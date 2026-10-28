import hashlib
import math
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

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
