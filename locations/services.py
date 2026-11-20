import hashlib
import math
from datetime import timedelta

import requests
from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from barang.models import Barang

from .models import GeocodingCache, PickupLocation


def pickup_context(user):
    return {
        'pickup_locations_data': [location.as_dict() for location in
                                  PickupLocation.objects.filter(owner=user, is_active=True)],
        'pickup_map_config': {
            'tileUrl': settings.OSM_TILE_URL,
            'center': [-6.3621, 106.8279],
            'zoom': 15,
        },
    }


def nearby_items(latitude, longitude, radius_km):
    """Return public item pins for a validated point and radius."""
    # Keep the precise device point transient: it is used only in this query.
    # A bounding-box filter lets the database discard distant inventory before
    # the exact Haversine calculation below, which matters as the catalogue
    # grows.  The final calculation still handles the curved earth accurately.
    latitude_delta = radius_km / 110.574
    longitude_delta = radius_km / max(111.320 * abs(math.cos(math.radians(latitude))), 0.01)
    candidates = Barang.objects.filter(
        status_penawaran='aktif', pemilik__is_active=True,
        lokasi__latitude__isnull=False, lokasi__longitude__isnull=False,
        lokasi__latitude__gte=latitude - latitude_delta,
        lokasi__latitude__lte=latitude + latitude_delta,
    ).select_related('lokasi')
    minimum_longitude = longitude - longitude_delta
    maximum_longitude = longitude + longitude_delta
    if longitude_delta < 180:
        if minimum_longitude < -180:
            candidates = candidates.filter(
                Q(lokasi__longitude__gte=minimum_longitude + 360)
                | Q(lokasi__longitude__lte=maximum_longitude)
            )
        elif maximum_longitude > 180:
            candidates = candidates.filter(
                Q(lokasi__longitude__gte=minimum_longitude)
                | Q(lokasi__longitude__lte=maximum_longitude - 360)
            )
        else:
            candidates = candidates.filter(
                lokasi__longitude__gte=minimum_longitude,
                lokasi__longitude__lte=maximum_longitude,
            )

    nearby = []
    for item in candidates:
        item_lat = float(item.lokasi.latitude)
        item_lon = float(item.lokasi.longitude)
        lat_delta = math.radians(item_lat - latitude)
        lon_delta = math.radians(item_lon - longitude)
        haversine = (math.sin(lat_delta / 2) ** 2
                     + math.cos(math.radians(latitude)) * math.cos(math.radians(item_lat))
                     * math.sin(lon_delta / 2) ** 2)
        distance_km = 6371 * 2 * math.asin(math.sqrt(min(1, haversine)))
        if distance_km > radius_km:
            continue
        nearby.append({
            'id': item.pk,
            'name': item.nama_barang,
            'price': item.tarif_formatted,
            'offer': 'Sewa' if item.jenis_penawaran == 'sewa' else 'Gratis',
            'area': item.lokasi.short_label or item.lokasi.nama_area,
            'distance_km': round(distance_km, 2),
            # Pins shown before an order is made deliberately identify an area,
            # not a house/room-level pickup point.  Exact coordinates are only
            # returned to the two parties of the order in transaksi.detail.
            'latitude': round(item_lat, 3),
            'longitude': round(item_lon, 3),
            'is_approximate': True,
            'image': item.foto_utama.url if item.foto_utama else '',
            'url': reverse('barang:detail', args=[item.pk]),
        })

    nearby.sort(key=lambda item: (item['distance_km'], item['name'].casefold()))
    return nearby[:50]

class GeocodingError(Exception):
    def __init__(self, message, status=503, retry_after=None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


def _area_label(payload):
    address = payload.get('address') if isinstance(payload, dict) else None
    if not isinstance(address, dict):
        return ''

    def first(*keys):
        for key in keys:
            value = address.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ''

    area = first('suburb', 'city_district', 'district', 'borough', 'quarter', 'village')
    city = first('city', 'town', 'municipality', 'county')
    parts = []
    for value in (area, city or first('state', 'country')):
        if value and value.casefold() not in [part.casefold() for part in parts]:
            parts.append(value)
    return ', '.join(parts)[:120]


def reverse_geocode(latitude, longitude):
    # Only approximate coordinates and an area label are cached, never a street address.
    latitude, longitude = round(latitude, 3), round(longitude, 3)
    provider = hashlib.sha256(settings.NOMINATIM_REVERSE_URL.encode()).hexdigest()[:16]
    key = f'result:{provider}:{latitude:.3f}:{longitude:.3f}'
    now = timezone.now()
    cached = GeocodingCache.objects.filter(key=key, expires_at__gt=now).first()
    if cached:
        return cached.data['label']

    quota_key = f'quota:{provider}'
    GeocodingCache.objects.get_or_create(
        key=quota_key, defaults={'expires_at': now, 'data': {}}
    )
    # One conditional UPDATE reserves a slot across processes and servers sharing the DB.
    # Keep a small margin above the public service's maximum of one request per second.
    reserved = GeocodingCache.objects.filter(
        key=quota_key, expires_at__lte=now
    ).update(expires_at=now + timedelta(seconds=1.1))
    if not reserved:
        quota = GeocodingCache.objects.get(key=quota_key)
        retry_after = max(1, math.ceil((quota.expires_at - now).total_seconds()))
        raise GeocodingError(
            'Layanan lokasi sedang sibuk. Coba lagi sebentar.',
            status=429, retry_after=retry_after,
        )

    try:
        response = requests.get(
            settings.NOMINATIM_REVERSE_URL,
            params={
                'lat': f'{latitude:.3f}', 'lon': f'{longitude:.3f}',
                'format': 'jsonv2', 'addressdetails': 1,
                'zoom': 13, 'layer': 'address', 'accept-language': 'id',
            },
            headers={'User-Agent': settings.NOMINATIM_USER_AGENT},
            timeout=(3, 6),
            allow_redirects=False,
        )
        if response.status_code == 429:
            try:
                retry_after = min(3600, max(1, int(response.headers.get('Retry-After', '60'))))
            except (TypeError, ValueError):
                retry_after = 60
            until = timezone.now() + timedelta(seconds=retry_after)
            GeocodingCache.objects.filter(
                key=quota_key, expires_at__lt=until
            ).update(expires_at=until)
            raise GeocodingError(
                'Layanan peta membatasi permintaan. Coba lagi nanti.',
                status=429, retry_after=retry_after,
            )
        if response.status_code == 404:
            raise GeocodingError('Nama wilayah untuk lokasi ini belum tersedia.', status=404)
        if response.status_code != 200:
            raise GeocodingError('Layanan peta sedang tidak tersedia. Coba lagi nanti.')
        label = _area_label(response.json())
    except (requests.RequestException, ValueError) as exc:
        raise GeocodingError(
            'Tidak dapat menghubungi layanan peta. Periksa koneksi dan coba lagi.'
        ) from exc

    if not label:
        raise GeocodingError('Nama wilayah untuk lokasi ini belum tersedia.', status=404)
    now = timezone.now()
    GeocodingCache.objects.update_or_create(
        key=key,
        defaults={'data': {'label': label}, 'expires_at': now + timedelta(hours=24)},
    )
    GeocodingCache.objects.filter(key__startswith='result:', expires_at__lte=now).delete()
    return label
