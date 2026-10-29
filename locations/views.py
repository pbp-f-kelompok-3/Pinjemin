import json
import math

from django.db import DatabaseError
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods

from .services import GeocodingError, pickup_context, reverse_geocode
from .forms import PickupLocationForm
from .models import PickupLocation


@never_cache
@require_POST
def current_location(request):
    try:
        payload = json.loads(request.body)
        latitude, longitude = payload['latitude'], payload['longitude']
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               for value in (latitude, longitude)):
            raise ValueError
        if not (math.isfinite(latitude) and math.isfinite(longitude)
                and -90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError
    except (ValueError, KeyError, TypeError, OverflowError):
        return JsonResponse({'error': 'Koordinat lokasi tidak valid.'}, status=400)

    try:
        label = reverse_geocode(latitude, longitude)
    except GeocodingError as exc:
        response = JsonResponse({'error': str(exc)}, status=exc.status)
        if exc.retry_after is not None:
            response['Retry-After'] = str(exc.retry_after)
        return response
    except DatabaseError:
        return JsonResponse(
            {'error': 'Layanan lokasi belum tersedia. Coba lagi nanti.'}, status=503
        )

    return JsonResponse({'label': label})


@never_cache
@login_required
def saved_locations(request):
    return render(request, 'locations/saved.html', pickup_context(request.user))


def _json_payload(request):
    try:
        payload = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


@never_cache
@require_http_methods(['GET', 'POST'])
def pickup_locations(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Silakan masuk kembali untuk mengelola lokasi.'}, status=401)
    if request.method == 'GET':
        return JsonResponse({'locations': pickup_context(request.user)['pickup_locations_data']})
    payload = _json_payload(request)
    if payload is None:
        return JsonResponse({'error': 'Data lokasi tidak valid.'}, status=400)
    form = PickupLocationForm(payload)
    if not form.is_valid():
        return JsonResponse({'error': 'Periksa label, alamat, dan titik pada peta.',
                             'errors': form.errors.get_json_data()}, status=400)
    location = form.save(commit=False)
    location.owner = request.user
    location.save()
    return JsonResponse({'location': location.as_dict()}, status=201)


@never_cache
@require_http_methods(['PATCH', 'DELETE'])
def pickup_location_detail(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Silakan masuk kembali untuk mengelola lokasi.'}, status=401)
    location = PickupLocation.objects.filter(pk=pk, owner=request.user, is_active=True).first()
    if location is None:
        return JsonResponse({'error': 'Lokasi ini tidak lagi tersedia. Pilih lokasi lain atau muat ulang riwayat.'}, status=404)
    if request.method == 'DELETE':
        location.is_active = False
        location.save(update_fields=['is_active', 'updated_at'])
        return JsonResponse({'deleted': True})
    payload = _json_payload(request)
    if payload is None:
        return JsonResponse({'error': 'Data lokasi tidak valid.'}, status=400)
    form = PickupLocationForm(payload, instance=location)
    if not form.is_valid():
        return JsonResponse({'error': 'Periksa label, alamat, dan titik pada peta.',
                             'errors': form.errors.get_json_data()}, status=400)
    location = form.save()
    return JsonResponse({'location': location.as_dict()})
