"""
JSON endpoints for the Pinjemin Flutter app.

Every endpoint lives under /akun/api/ so the existing web pages in views.py keep
their behaviour. None of them is csrf_exempt: the app fetches the csrftoken cookie
from sso_start/me and sends it back as the X-CSRFToken header on every POST.
"""
import logging
import xml.etree.ElementTree as ET
from functools import wraps

import requests
from django.contrib.auth import get_user_model, login
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import Profile
from .sso import get_login_url, validate_ticket

logger = logging.getLogger(__name__)
User = get_user_model()

SSO_DOWN_MESSAGE = "SSO UI sedang bermasalah. Coba lagi beberapa saat."


def _error(message, status, **extra):
    return JsonResponse({"status": False, "message": message, **extra}, status=status)


def api_login_required(view):
    """Like login_required, but answers 401 JSON instead of redirecting to an HTML page."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _error("Sesi kamu sudah habis. Silakan login lagi.", 401)
        return view(request, *args, **kwargs)

    return wrapper


def serialize_profile(profile, request):
    completeness = profile.completeness
    return {
        "id": profile.pk,
        "username": profile.user.username,
        "npm": profile.npm,
        "full_name": profile.full_name,
        "kode_org": profile.kode_org,
        "angkatan": profile.angkatan,
        "phone": profile.phone,
        "bio": profile.bio,
        "location": profile.location,
        "photo_url": request.build_absolute_uri(profile.photo.url) if profile.photo else None,
        "mode": profile.mode,
        "mode_label": profile.get_mode_display(),
        "is_seller": profile.is_seller_mode,
        "is_onboarded": profile.is_onboarded,
        "completeness": {
            "percent": completeness["percent"],
            "checks": [{"label": label, "done": done} for label, done in completeness["checks"]],
        },
        "created_at": profile.created_at.isoformat(),
    }


def _mobile_callback_url(request):
    # Must be identical when building the SSO login URL and when validating the ticket
    return request.build_absolute_uri(reverse("accounts:api_sso_callback"))


def _sync_sso_user(result):
    """Create or update the user from the SSO result. Same rules as views.sso_callback."""
    attrs = result["attributes"]

    user, created = User.objects.get_or_create(username=result["username"])
    if created:
        user.set_unusable_password()
        user.save()

    profile, _ = Profile.objects.get_or_create(user=user)
    profile.npm = attrs.get("npm", profile.npm)
    profile.full_name = attrs.get("nama", profile.full_name)
    profile.kode_org = attrs.get("kd_org", profile.kode_org)

    reactivated = profile.deactivated_at is not None
    if reactivated:
        profile.deactivated_at = None
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
    profile.save()
    return user, profile, reactivated


@require_GET
@never_cache
@ensure_csrf_cookie
def sso_start(request):
    """Gives the app the SSO UI login URL and sets the csrftoken cookie for the exchange."""
    return JsonResponse({"status": True, "login_url": get_login_url(_mobile_callback_url(request))})


@require_GET
def sso_callback_landing(request):
    """
    SSO UI redirects here with ?ticket=. The app's WebView catches this URL and sends
    the ticket to sso_exchange. This view deliberately does NOT validate the ticket,
    so loading it in a browser by accident never consumes it.
    """
    return HttpResponse(
        "<!doctype html><html lang='id'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Pinjemin</title></head>"
        "<body style='font-family:sans-serif;padding:24px'>"
        "<p>Login SSO selesai. Kembali ke aplikasi Pinjemin.</p></body></html>"
    )


@require_POST
@never_cache
def sso_exchange(request):
    """Validates the SSO ticket and logs the user in. Response sets sessionid and a new csrftoken."""
    ticket = request.POST.get("ticket", "").strip()
    if not ticket:
        return _error("Ticket SSO tidak ada. Silakan login ulang.", 400)

    try:
        result = validate_ticket(ticket, _mobile_callback_url(request))
    except requests.HTTPError as exc:
        resp = exc.response
        status = resp.status_code if resp is not None else None
        logger.warning("SSO HTTP error (mobile): status=%s", status)
        if status == 400:
            return _error("SSO UI menolak permintaan login. Silakan coba lagi.", 502)
        return _error(SSO_DOWN_MESSAGE, 502)
    except (requests.RequestException, ET.ParseError) as exc:
        logger.warning("SSO error (mobile): %r", exc)
        return _error(SSO_DOWN_MESSAGE, 502)

    if result is None:
        return _error("Validasi SSO gagal. Silakan login ulang.", 401)

    if not result["attributes"].get("npm"):
        return _error("Pinjemin hanya untuk mahasiswa Universitas Indonesia.", 403)

    user, profile, reactivated = _sync_sso_user(result)

    # Accounts deactivated by an admin (not by the owner) stay blocked
    if not user.is_active:
        return _error("Akun ini tidak dapat digunakan. Hubungi pengelola.", 403)

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return JsonResponse({
        "status": True,
        "message": "Selamat datang kembali. Akunmu sudah aktif lagi." if reactivated else "Login berhasil.",
        "reactivated": reactivated,
        "profile": serialize_profile(profile, request),
    })


@require_GET
@never_cache
@ensure_csrf_cookie
@api_login_required
def me(request):
    """Current user's profile. The app calls this on startup to check the stored session."""
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return JsonResponse({"status": True, "profile": serialize_profile(profile, request)})
