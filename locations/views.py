import json
import math

from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .services import GeocodingError, reverse_geocode


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
