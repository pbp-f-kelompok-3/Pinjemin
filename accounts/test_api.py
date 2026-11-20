import xml.etree.ElementTree as ET
from unittest import mock

import requests
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile

User = get_user_model()

SSO_RESULT = {
    "username": "rois",
    "attributes": {"nama": "Roisul Umam", "npm": "2506620210", "kd_org": "01.00.12.01"},
}


def make_user(username="rois", npm="2506620210", onboarded=True, **profile_kwargs):
    user = User.objects.create_user(username=username, password="x")
    profile = Profile.objects.create(
        user=user, npm=npm, full_name="Roisul Umam", is_onboarded=onboarded, **profile_kwargs
    )
    return user, profile


class SsoStartApiTests(TestCase):
    def test_returns_login_url_with_mobile_callback_and_sets_csrf_cookie(self):
        resp = self.client.get(reverse("accounts:api_sso_start"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["status"])
        self.assertTrue(data["login_url"].startswith("https://sso.ui.ac.id/cas2/login?service="))
        self.assertIn("%2Fakun%2Fapi%2Fsso%2Fcallback%2F", data["login_url"])
        self.assertIn("csrftoken", resp.cookies)

    def test_post_not_allowed(self):
        self.assertEqual(self.client.post(reverse("accounts:api_sso_start")).status_code, 405)


class SsoCallbackLandingTests(TestCase):
    def test_landing_never_validates_ticket(self):
        with mock.patch("accounts.api_views.validate_ticket") as validate:
            resp = self.client.get(reverse("accounts:api_sso_callback"), {"ticket": "ST-1"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Kembali ke aplikasi Pinjemin")
        validate.assert_not_called()
        self.assertNotIn("_auth_user_id", self.client.session)


class SsoExchangeApiTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:api_sso_exchange")

    def exchange(self, ticket="ST-1"):
        return self.client.post(self.url, {"ticket": ticket})

    def assert_error(self, resp, status, fragment):
        self.assertEqual(resp.status_code, status)
        self.assertFalse(resp.json()["status"])
        self.assertIn(fragment, resp.json()["message"])
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_missing_ticket(self):
        self.assert_error(self.exchange(ticket=""), 400, "Ticket SSO tidak ada")

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_http_400_from_sso(self):
        error = requests.HTTPError(response=mock.Mock(status_code=400))
        with mock.patch("accounts.api_views.validate_ticket", side_effect=error):
            self.assert_error(self.exchange(), 502, "menolak")

    def test_http_500_from_sso(self):
        error = requests.HTTPError(response=mock.Mock(status_code=500))
        with mock.patch("accounts.api_views.validate_ticket", side_effect=error):
            self.assert_error(self.exchange(), 502, "sedang bermasalah")

    def test_http_error_without_response(self):
        with mock.patch("accounts.api_views.validate_ticket", side_effect=requests.HTTPError()):
            self.assert_error(self.exchange(), 502, "sedang bermasalah")

    def test_connection_error(self):
        with mock.patch("accounts.api_views.validate_ticket", side_effect=requests.ConnectionError()):
            self.assert_error(self.exchange(), 502, "sedang bermasalah")

    def test_broken_xml(self):
        with mock.patch("accounts.api_views.validate_ticket", side_effect=ET.ParseError("bad")):
            self.assert_error(self.exchange(), 502, "sedang bermasalah")

    def test_invalid_ticket(self):
        with mock.patch("accounts.api_views.validate_ticket", return_value=None):
            self.assert_error(self.exchange(), 401, "Validasi SSO gagal")

    def test_non_student_rejected(self):
        result = {"username": "dosen", "attributes": {"nama": "Dosen", "peran_user": "staff"}}
        with mock.patch("accounts.api_views.validate_ticket", return_value=result):
            self.assert_error(self.exchange(), 403, "mahasiswa")
        self.assertFalse(User.objects.filter(username="dosen").exists())

    def test_first_login_creates_account(self):
        with mock.patch("accounts.api_views.validate_ticket", return_value=SSO_RESULT) as validate:
            resp = self.exchange()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["status"])
        self.assertFalse(data["reactivated"])
        self.assertEqual(data["profile"]["npm"], "2506620210")
        self.assertEqual(data["profile"]["mode"], "renter")
        self.assertFalse(data["profile"]["is_onboarded"])
        # The ticket must be validated against the same callback URL used in sso_start
        self.assertTrue(validate.call_args.args[1].endswith("/akun/api/sso/callback/"))
        user = User.objects.get(username="rois")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertIn("csrftoken", resp.cookies)

    def test_existing_user_keeps_own_data(self):
        make_user(phone="08123456789", bio="Halo")
        with mock.patch("accounts.api_views.validate_ticket", return_value=SSO_RESULT):
            profile = self.exchange().json()["profile"]
        self.assertTrue(profile["is_onboarded"])
        self.assertEqual(profile["phone"], "08123456789")
        self.assertEqual(profile["bio"], "Halo")

    def test_self_deactivated_account_is_reactivated(self):
        user, _ = make_user(deactivated_at=timezone.now())
        user.is_active = False
        user.save()
        with mock.patch("accounts.api_views.validate_ticket", return_value=SSO_RESULT):
            resp = self.exchange()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["reactivated"])
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertIsNone(user.profile.deactivated_at)

    def test_admin_blocked_account_stays_blocked(self):
        user, _ = make_user()
        user.is_active = False
        user.save()
        with mock.patch("accounts.api_views.validate_ticket", return_value=SSO_RESULT):
            self.assert_error(self.exchange(), 403, "tidak dapat digunakan")

    def test_csrf_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        with mock.patch("accounts.api_views.validate_ticket", return_value=SSO_RESULT):
            no_token = client.post(self.url, {"ticket": "ST-1"})
            self.assertEqual(no_token.status_code, 403)

            client.get(reverse("accounts:api_sso_start"))
            token = client.cookies["csrftoken"].value
            with_token = client.post(self.url, {"ticket": "ST-1"}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(with_token.status_code, 200)


class MeApiTests(TestCase):
    def test_anonymous_gets_401_json(self):
        resp = self.client.get(reverse("accounts:api_me"))
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(resp.json()["status"])

    def test_returns_profile_and_sets_csrf_cookie(self):
        user, _ = make_user(phone="08123456789", mode=Profile.Mode.SELLER)
        self.client.force_login(user)
        resp = self.client.get(reverse("accounts:api_me"))
        self.assertEqual(resp.status_code, 200)
        profile = resp.json()["profile"]
        self.assertEqual(profile["username"], "rois")
        self.assertEqual(profile["mode_label"], "Minjemin")
        self.assertTrue(profile["is_seller"])
        self.assertEqual(profile["angkatan"], 2025)
        self.assertIsNone(profile["photo_url"])
        self.assertEqual(profile["completeness"]["percent"], 25)
        self.assertEqual(profile["completeness"]["checks"][1], {"label": "Nomor WhatsApp", "done": True})
        self.assertIn("csrftoken", resp.cookies)

    def test_creates_missing_profile(self):
        user = User.objects.create_user(username="tanpaprofil", password="x")
        self.client.force_login(user)
        resp = self.client.get(reverse("accounts:api_me"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_deactivated_session_is_rejected(self):
        user, _ = make_user()
        self.client.force_login(user)
        user.is_active = False
        user.save()
        self.assertEqual(self.client.get(reverse("accounts:api_me")).status_code, 401)
