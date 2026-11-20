"""
Django REST Framework endpoints for the Pinjemin Flutter app.

Every endpoint lives under /akun/api/ so the existing web pages in views.py keep
their behaviour. None of them skips CSRF: the app gets the csrftoken cookie from
sso_start/me and sends it back as the X-CSRFToken header on every POST.
"""
import logging
import xml.etree.ElementTree as ET

import requests
from django.contrib.auth import get_user_model, login
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from rest_framework import exceptions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Profile
from .serializers import ProfileSerializer
from .sso import get_login_url, validate_ticket

logger = logging.getLogger(__name__)
User = get_user_model()

SSO_DOWN_MESSAGE = "SSO UI sedang bermasalah. Coba lagi beberapa saat."
SESSION_EXPIRED_MESSAGE = "Sesi kamu sudah habis. Silakan login lagi."
CSRF_FAILED_MESSAGE = "Permintaan ditolak server. Tutup aplikasi lalu login lagi."


class CsrfSessionAuthentication(SessionAuthentication):
    """
    SessionAuthentication that also checks CSRF for anonymous requests.

    DRF marks every APIView as csrf_exempt and only checks CSRF once a user is
    logged in. The SSO exchange happens before login, so without this an attacker
    could log a victim into the attacker's account (login CSRF).
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            self.enforce_csrf(request)
        return result

    def authenticate_header(self, request):
        # Any value makes DRF answer 401 (not 403) when the session is missing
        return "Session"


def _error(message, status_code, **extra):
    return Response({"status": False, "message": message, **extra}, status=status_code)


@method_decorator(never_cache, name="dispatch")
class PinjeminAPIView(APIView):
    """Base view: session + CSRF auth, JSON only, errors as {"status": false, "message": ...}."""

    authentication_classes = [CsrfSessionAuthentication]
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]
    parser_classes = [FormParser, MultiPartParser, JSONParser]

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if isinstance(exc, exceptions.NotAuthenticated):
            message = SESSION_EXPIRED_MESSAGE
        elif isinstance(exc, exceptions.PermissionDenied) and "CSRF" in str(exc.detail):
            message = CSRF_FAILED_MESSAGE
        else:
            message = str(exc.detail)
        response.data = {"status": False, "message": message}
        return response


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


class SsoStartView(PinjeminAPIView):
    """GET: the SSO UI login URL. Also sets the csrftoken cookie needed by the exchange."""

    def get(self, request):
        get_token(request._request)
        return Response({"status": True, "login_url": get_login_url(_mobile_callback_url(request))})


@require_GET
def sso_callback_landing(request):
    """
    SSO UI redirects here with ?ticket=. The app's WebView catches this URL and sends
    the ticket to the exchange endpoint. This is a plain HTML page, not an API, and it
    deliberately does NOT validate the ticket, so loading it by accident never consumes it.
    """
    return HttpResponse(
        "<!doctype html><html lang='id'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Pinjemin</title></head>"
        "<body style='font-family:sans-serif;padding:24px'>"
        "<p>Login SSO selesai. Kembali ke aplikasi Pinjemin.</p></body></html>"
    )


class SsoExchangeView(PinjeminAPIView):
    """POST ticket: validates it with SSO UI and logs in. Sets sessionid and a new csrftoken."""

    def post(self, request):
        ticket = str(request.data.get("ticket", "")).strip()
        if not ticket:
            return _error("Ticket SSO tidak ada. Silakan login ulang.", status.HTTP_400_BAD_REQUEST)

        try:
            result = validate_ticket(ticket, _mobile_callback_url(request))
        except requests.HTTPError as exc:
            resp = exc.response
            sso_status = resp.status_code if resp is not None else None
            logger.warning("SSO HTTP error (mobile): status=%s", sso_status)
            if sso_status == 400:
                return _error("SSO UI menolak permintaan login. Silakan coba lagi.", status.HTTP_502_BAD_GATEWAY)
            return _error(SSO_DOWN_MESSAGE, status.HTTP_502_BAD_GATEWAY)
        except (requests.RequestException, ET.ParseError) as exc:
            logger.warning("SSO error (mobile): %r", exc)
            return _error(SSO_DOWN_MESSAGE, status.HTTP_502_BAD_GATEWAY)

        if result is None:
            return _error("Validasi SSO gagal. Silakan login ulang.", status.HTTP_401_UNAUTHORIZED)

        if not result["attributes"].get("npm"):
            return _error("Pinjemin hanya untuk mahasiswa Universitas Indonesia.", status.HTTP_403_FORBIDDEN)

        user, profile, reactivated = _sync_sso_user(result)

        # Accounts deactivated by an admin (not by the owner) stay blocked
        if not user.is_active:
            return _error("Akun ini tidak dapat digunakan. Hubungi pengelola.", status.HTTP_403_FORBIDDEN)

        login(request._request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({
            "status": True,
            "message": "Selamat datang kembali. Akunmu sudah aktif lagi." if reactivated else "Login berhasil.",
            "reactivated": reactivated,
            "profile": ProfileSerializer(profile, context={"request": request}).data,
        })


class MeView(PinjeminAPIView):
    """GET: the current user's profile. The app calls this on startup to check the stored session."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        get_token(request._request)
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return Response({"status": True, "profile": ProfileSerializer(profile, context={"request": request}).data})
