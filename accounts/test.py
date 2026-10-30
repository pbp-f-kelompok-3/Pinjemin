import io
import shutil
import tempfile
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from unittest import mock

import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages import get_messages
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts import sso
from accounts.context_processors import user_mode
from accounts.forms import OnboardingForm, ProfileEditForm
from accounts.models import Profile
from accounts.services import get_blocking_transactions
from barang.models import Barang
from transaksi.models import Pesanan

User = get_user_model()

TEMP_MEDIA = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)


# ------------------------------------------------------------------ helpers
def make_user(username="rois", npm="2506620210", full_name="Roisul Umam", onboarded=True, **profile_kwargs):
    user = User.objects.create_user(username=username, password="x")
    profile = Profile.objects.create(
        user=user, npm=npm, full_name=full_name, is_onboarded=onboarded, **profile_kwargs
    )
    return user, profile


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), "yellow").save(buf, "PNG")
    return buf.getvalue()


def msgs(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


SSO_RESULT = {
    "username": "rois",
    "attributes": {"nama": "Roisul Umam", "npm": "2506620210", "kd_org": "01.00.12.01"},
}

CAS_SUCCESS_XML = b"""<cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
  <cas:authenticationSuccess>
    <cas:user>rois</cas:user>
    <cas:attributes>
      <cas:nama>Roisul Umam</cas:nama>
      <cas:npm>2506620210</cas:npm>
      <cas:kd_org>01.00.12.01</cas:kd_org>
    </cas:attributes>
  </cas:authenticationSuccess>
</cas:serviceResponse>"""

CAS_FAILURE_XML = b"""<cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
  <cas:authenticationFailure code="INVALID_TICKET">Ticket tidak valid</cas:authenticationFailure>
</cas:serviceResponse>"""

CAS_NO_ATTR_XML = b"""<cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
  <cas:authenticationSuccess><cas:user>rois</cas:user></cas:authenticationSuccess>
</cas:serviceResponse>"""


# ------------------------------------------------------------------ model
class ProfileModelTests(TestCase):
    def test_angkatan_dari_npm(self):
        self.assertEqual(Profile(npm="2506620210").angkatan, 2025)

    def test_angkatan_kosong_atau_bukan_angka(self):
        self.assertIsNone(Profile(npm="").angkatan)
        self.assertIsNone(Profile(npm="ab123").angkatan)

    def test_completeness_kosong(self):
        result = Profile().completeness
        self.assertEqual(result["percent"], 0)
        self.assertEqual(len(result["checks"]), 4)

    def test_completeness_lengkap(self):
        profile = Profile(photo="profile_photos/a.png", phone="08123456789", location="Kutek", bio="Halo")
        self.assertEqual(profile.completeness["percent"], 100)

    def test_completeness_sebagian(self):
        self.assertEqual(Profile(phone="08123456789", bio="Halo").completeness["percent"], 50)

    def test_properti_mode_dan_nonaktif(self):
        profile = Profile(mode=Profile.Mode.SELLER)
        self.assertTrue(profile.is_seller_mode)
        self.assertFalse(Profile(mode=Profile.Mode.RENTER).is_seller_mode)
        self.assertFalse(profile.is_deactivated)

    def test_is_deactivated(self):
        from django.utils import timezone
        self.assertTrue(Profile(deactivated_at=timezone.now()).is_deactivated)

    def test_str(self):
        user, profile = make_user()
        self.assertEqual(str(profile), "Roisul Umam (2506620210)")
        profile.full_name = ""
        self.assertIn("rois", str(profile))


# ------------------------------------------------------------------ form
@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class FormTests(TestCase):
    def valid_data(self, **extra):
        data = {"phone": "0812-3456 7890", "location": "Kutek", "bio": "Halo", "mode": "renter", "accept_privacy": "on"}
        data.update(extra)
        return data

    def test_onboarding_valid_dan_nomor_dinormalisasi(self):
        _, profile = make_user(onboarded=False)
        form = OnboardingForm(self.valid_data(), instance=profile)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["phone"], "081234567890")

    def test_nomor_tidak_valid(self):
        _, profile = make_user(onboarded=False)
        form = OnboardingForm(self.valid_data(phone="abc"), instance=profile)
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    def test_nomor_wajib(self):
        _, profile = make_user(onboarded=False)
        form = OnboardingForm(self.valid_data(phone=""), instance=profile)
        self.assertFalse(form.is_valid())
        self.assertIn("wajib", form.errors["phone"][0])

    def test_persetujuan_privasi_wajib(self):
        _, profile = make_user(onboarded=False)
        data = self.valid_data()
        del data["accept_privacy"]
        form = OnboardingForm(data, instance=profile)
        self.assertFalse(form.is_valid())
        self.assertIn("accept_privacy", form.errors)

    def test_foto_terlalu_besar(self):
        _, profile = make_user(onboarded=False)
        upload = SimpleUploadedFile("a.png", png_bytes(), content_type="image/png")
        with mock.patch("accounts.forms.MAX_PHOTO_BYTES", 10):
            form = OnboardingForm(self.valid_data(), {"photo": upload}, instance=profile)
            self.assertFalse(form.is_valid())
        self.assertIn("10 MB", form.errors["photo"][0])

    def test_foto_format_tidak_diizinkan(self):
        _, profile = make_user(onboarded=False)
        upload = SimpleUploadedFile("a.gif", png_bytes(), content_type="image/gif")
        form = OnboardingForm(self.valid_data(), {"photo": upload}, instance=profile)
        self.assertFalse(form.is_valid())
        self.assertIn("JPG, JPEG, atau PNG", form.errors["photo"][0])

    def test_foto_valid_diterima(self):
        _, profile = make_user(onboarded=False)
        upload = SimpleUploadedFile("a.png", png_bytes(), content_type="image/png")
        form = OnboardingForm(self.valid_data(), {"photo": upload}, instance=profile)
        self.assertTrue(form.is_valid(), form.errors)

    def test_edit_hapus_foto(self):
        _, profile = make_user()
        profile.photo.save("lama.png", ContentFile(png_bytes()), save=True)
        self.assertTrue(profile.photo)
        form = ProfileEditForm({"phone": "08123456789", "remove_photo": "on"}, instance=profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        profile.refresh_from_db()
        self.assertFalse(profile.photo)

    def test_edit_tanpa_hapus_foto_mempertahankan_foto(self):
        _, profile = make_user()
        profile.photo.save("lama.png", ContentFile(png_bytes()), save=True)
        form = ProfileEditForm({"phone": "08123456789"}, instance=profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        profile.refresh_from_db()
        self.assertTrue(profile.photo)

    def test_edit_ganti_foto_menang_atas_hapus(self):
        _, profile = make_user()
        upload = SimpleUploadedFile("baru.png", png_bytes(), content_type="image/png")
        form = ProfileEditForm({"phone": "08123456789", "remove_photo": "on"}, {"photo": upload}, instance=profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        profile.refresh_from_db()
        self.assertTrue(profile.photo)


# ------------------------------------------------------------------ sso client
class SSOClientTests(TestCase):
    def fake_response(self, content):
        return mock.Mock(content=content, raise_for_status=mock.Mock())

    def test_get_login_url(self):
        url = sso.get_login_url("http://localhost:8000/akun/sso/callback/")
        self.assertTrue(url.startswith("https://sso.ui.ac.id/cas2/login?service="))
        self.assertIn("localhost%3A8000", url)

    def test_validate_ticket_sukses(self):
        with mock.patch("accounts.sso.requests.get", return_value=self.fake_response(CAS_SUCCESS_XML)) as get:
            result = sso.validate_ticket("ST-1", "http://x/cb/")
        self.assertEqual(result["username"], "rois")
        self.assertEqual(result["attributes"]["npm"], "2506620210")
        self.assertEqual(result["attributes"]["nama"], "Roisul Umam")
        self.assertEqual(get.call_args.kwargs["params"]["ticket"], "ST-1")

    def test_validate_ticket_gagal(self):
        with mock.patch("accounts.sso.requests.get", return_value=self.fake_response(CAS_FAILURE_XML)):
            self.assertIsNone(sso.validate_ticket("ST-1", "http://x/cb/"))

    def test_validate_ticket_tanpa_atribut(self):
        with mock.patch("accounts.sso.requests.get", return_value=self.fake_response(CAS_NO_ATTR_XML)):
            result = sso.validate_ticket("ST-1", "http://x/cb/")
        self.assertEqual(result, {"username": "rois", "attributes": {}})

    def test_validate_ticket_http_error_diteruskan(self):
        resp = mock.Mock(content=b"", raise_for_status=mock.Mock(side_effect=requests.HTTPError("400")))
        with mock.patch("accounts.sso.requests.get", return_value=resp):
            with self.assertRaises(requests.HTTPError):
                sso.validate_ticket("ST-1", "http://x/cb/")

    def test_validate_ticket_xml_rusak(self):
        with mock.patch("accounts.sso.requests.get", return_value=self.fake_response(b"<html>bukan xml")):
            with self.assertRaises(ET.ParseError):
                sso.validate_ticket("ST-1", "http://x/cb/")


# ------------------------------------------------------------------ services
class BlockingTransactionsTests(TestCase):
    def fake_order(self, status, borrower, owner, nama="Kamera Sony"):
        return SimpleNamespace(
            status=status,
            nama_barang=nama,
            peminjam=borrower,
            peminjam_id=borrower.id,
            pemilik=owner,
            get_status_display=lambda: "status",
        )

    def run_service(self, user, orders):
        with mock.patch("transaksi.services.maintain_orders"), \
                mock.patch.object(Pesanan.objects, "filter") as m_filter:
            m_filter.return_value.select_related.return_value = orders
            return get_blocking_transactions(user)

    def test_kosong_di_database_nyata(self):
        user, _ = make_user()
        with mock.patch("transaksi.services.maintain_orders") as maintain:
            self.assertEqual(get_blocking_transactions(user), [])
        maintain.assert_called_once()

    def test_peminjam_menunggu_pembayaran(self):
        me, _ = make_user()
        owner, _ = make_user("bagas", full_name="Bagas")
        items = self.run_service(me, [self.fake_order(Pesanan.Status.WAITING, me, owner)])
        self.assertIn("menunggu pembayaran", items[0]["label"])
        self.assertIn("Bagas", items[0]["label"])

    def test_peminjam_terkonfirmasi(self):
        me, _ = make_user()
        owner, _ = make_user("bagas", full_name="Bagas")
        items = self.run_service(me, [self.fake_order(Pesanan.Status.CONFIRMED, me, owner)])
        self.assertIn("terkonfirmasi", items[0]["label"])

    def test_pemilik_menunggu_pembayaran(self):
        me, _ = make_user()
        borrower, _ = make_user("rina", full_name="Rina")
        items = self.run_service(me, [self.fake_order(Pesanan.Status.WAITING, borrower, me)])
        self.assertIn("milikmu sedang dipesan Rina", items[0]["label"])

    def test_pemilik_terkonfirmasi_dan_nama_barang_kosong(self):
        me, _ = make_user()
        borrower, _ = make_user("rina", full_name="Rina")
        items = self.run_service(me, [self.fake_order(Pesanan.Status.CONFIRMED, borrower, me, nama="")])
        self.assertTrue(items[0]["label"].startswith("barang milikmu"))
        self.assertEqual(items[0]["status"], "status")

    def test_nama_tampil_memakai_username_kalau_tanpa_profil(self):
        me, _ = make_user()
        owner = User.objects.create_user(username="tanpa.profil", password="x")
        items = self.run_service(me, [self.fake_order(Pesanan.Status.WAITING, me, owner)])
        self.assertIn("tanpa.profil", items[0]["label"])


# ------------------------------------------------------------------ context processor
class ContextProcessorTests(TestCase):
    def ctx(self, user):
        request = RequestFactory().get("/")
        request.user = user
        return user_mode(request)

    def test_anonim(self):
        self.assertEqual(self.ctx(AnonymousUser()), {"is_seller_mode": False})

    def test_mode_minjemin(self):
        user, _ = make_user(mode=Profile.Mode.SELLER)
        self.assertTrue(self.ctx(user)["is_seller_mode"])

    def test_mode_minjem(self):
        user, _ = make_user(mode=Profile.Mode.RENTER)
        self.assertFalse(self.ctx(user)["is_seller_mode"])

    def test_tanpa_profil(self):
        user = User.objects.create_user(username="tanpa.profil", password="x")
        self.assertFalse(self.ctx(user)["is_seller_mode"])


# ------------------------------------------------------------------ login & SSO views
class LoginViewTests(TestCase):
    def test_halaman_login_untuk_anonim(self):
        resp = self.client.get(reverse("accounts:login"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "accounts/login.html")

    def test_user_login_dialihkan_ke_beranda(self):
        user, _ = make_user()
        self.client.force_login(user)
        resp = self.client.get(reverse("accounts:login"))
        self.assertRedirects(resp, "/", fetch_redirect_response=False)

    def test_sso_login_redirect_ke_sso_ui(self):
        resp = self.client.get(reverse("accounts:sso_login"))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("https://sso.ui.ac.id/cas2/login?service="))

    def test_sso_login_menyimpan_next_yang_aman(self):
        self.client.get(reverse("accounts:sso_login"), {"next": "/barang/"})
        self.assertEqual(self.client.session["post_login_next"], "/barang/")

    def test_sso_login_mengabaikan_next_berbahaya(self):
        self.client.get(reverse("accounts:sso_login"), {"next": "http://evil.example/"})
        self.assertNotIn("post_login_next", self.client.session)


class SSOCallbackTests(TestCase):
    url = None

    def setUp(self):
        self.url = reverse("accounts:sso_callback")

    def callback(self, **kwargs):
        return self.client.get(self.url, {"ticket": "ST-1"}, **kwargs)

    def assert_gagal(self, resp, potongan_pesan):
        self.assertRedirects(resp, reverse("accounts:login"), fetch_redirect_response=False)
        self.assertTrue(any(potongan_pesan in m for m in msgs(resp)), msgs(resp))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_tanpa_ticket(self):
        resp = self.client.get(self.url)
        self.assert_gagal(resp, "dibatalkan")

    def test_http_400(self):
        error = requests.HTTPError(response=mock.Mock(status_code=400, text="bad"))
        with mock.patch("accounts.views.validate_ticket", side_effect=error):
            self.assert_gagal(self.callback(), "menolak")

    def test_http_500(self):
        error = requests.HTTPError(response=mock.Mock(status_code=500, text="oops"))
        with mock.patch("accounts.views.validate_ticket", side_effect=error):
            self.assert_gagal(self.callback(), "sedang bermasalah")

    def test_http_error_tanpa_response(self):
        with mock.patch("accounts.views.validate_ticket", side_effect=requests.HTTPError()):
            self.assert_gagal(self.callback(), "sedang bermasalah")

    def test_koneksi_gagal(self):
        with mock.patch("accounts.views.validate_ticket", side_effect=requests.ConnectionError()):
            self.assert_gagal(self.callback(), "sedang bermasalah")

    def test_xml_rusak(self):
        with mock.patch("accounts.views.validate_ticket", side_effect=ET.ParseError("bad")):
            self.assert_gagal(self.callback(), "sedang bermasalah")

    def test_ticket_tidak_valid(self):
        with mock.patch("accounts.views.validate_ticket", return_value=None):
            self.assert_gagal(self.callback(), "Validasi SSO gagal")

    def test_bukan_mahasiswa_tanpa_npm(self):
        result = {"username": "dosen", "attributes": {"nama": "Dosen", "peran_user": "staff"}}
        with mock.patch("accounts.views.validate_ticket", return_value=result):
            self.assert_gagal(self.callback(), "mahasiswa")
        self.assertFalse(User.objects.filter(username="dosen").exists())

    def test_login_pertama_membuat_akun_dan_ke_onboarding(self):
        with mock.patch("accounts.views.validate_ticket", return_value=SSO_RESULT):
            resp = self.callback()
        self.assertRedirects(resp, reverse("accounts:onboarding"), fetch_redirect_response=False)
        user = User.objects.get(username="rois")
        self.assertFalse(user.has_usable_password())
        self.assertEqual(user.profile.npm, "2506620210")
        self.assertEqual(user.profile.full_name, "Roisul Umam")
        self.assertEqual(user.profile.kode_org, "01.00.12.01")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_user_lama_ke_beranda(self):
        make_user()
        with mock.patch("accounts.views.validate_ticket", return_value=SSO_RESULT):
            resp = self.callback()
        self.assertRedirects(resp, "/", fetch_redirect_response=False)

    def test_user_lama_kembali_ke_halaman_tujuan(self):
        make_user()
        session = self.client.session
        session["post_login_next"] = "/barang/"
        session.save()
        with mock.patch("accounts.views.validate_ticket", return_value=SSO_RESULT):
            resp = self.callback()
        self.assertRedirects(resp, "/barang/", fetch_redirect_response=False)

    def test_data_sso_disinkronkan_tapi_data_user_tidak_tertimpa(self):
        _, profile = make_user(full_name="Nama Lama", phone="08123456789", bio="Bio saya")
        with mock.patch("accounts.views.validate_ticket", return_value=SSO_RESULT):
            self.callback()
        profile.refresh_from_db()
        self.assertEqual(profile.full_name, "Roisul Umam")
        self.assertEqual(profile.phone, "08123456789")
        self.assertEqual(profile.bio, "Bio saya")

    def test_akun_nonaktif_diaktifkan_kembali(self):
        from django.utils import timezone
        user, profile = make_user()
        profile.deactivated_at = timezone.now()
        profile.save()
        user.is_active = False
        user.save()
        with mock.patch("accounts.views.validate_ticket", return_value=SSO_RESULT):
            resp = self.callback()
        user.refresh_from_db()
        profile.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertIsNone(profile.deactivated_at)
        self.assertTrue(any("Selamat datang kembali" in m for m in msgs(resp)))
        self.assertIn("_auth_user_id", self.client.session)

    def test_akun_diblokir_pengelola_tetap_ditolak(self):
        user, _ = make_user()
        user.is_active = False
        user.save()
        with mock.patch("accounts.views.validate_ticket", return_value=SSO_RESULT):
            resp = self.callback()
        self.assert_gagal(resp, "tidak dapat digunakan")


class LogoutTests(TestCase):
    def test_logout(self):
        user, _ = make_user()
        self.client.force_login(user)
        resp = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(resp, reverse("accounts:login"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_harus_post(self):
        user, _ = make_user()
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)


# ------------------------------------------------------------------ onboarding
class OnboardingViewTests(TestCase):
    def setUp(self):
        self.user, self.profile = make_user(onboarded=False)
        self.client.force_login(self.user)
        self.url = reverse("accounts:onboarding")

    def valid_post(self, **extra):
        data = {"phone": "081234567890", "location": "Kutek", "bio": "Halo", "mode": "seller", "accept_privacy": "on"}
        data.update(extra)
        return data

    def test_wajib_login(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:login"), resp["Location"])

    def test_tampil(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Selamat Datang di Pinjemin")
        self.assertContains(resp, 'data-start-step="1"')
        self.assertEqual(resp.context["first_name"], "Roisul")

    def test_sudah_onboarded_dialihkan(self):
        self.profile.is_onboarded = True
        self.profile.save()
        self.assertRedirects(self.client.get(self.url), "/", fetch_redirect_response=False)

    def test_kirim_valid(self):
        resp = self.client.post(self.url, self.valid_post())
        self.assertRedirects(resp, "/", fetch_redirect_response=False)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.is_onboarded)
        self.assertIsNotNone(self.profile.accepted_privacy_at)
        self.assertEqual(self.profile.phone, "081234567890")
        self.assertEqual(self.profile.mode, "seller")

    def test_kirim_valid_kembali_ke_halaman_tujuan(self):
        session = self.client.session
        session["post_login_next"] = "/barang/"
        session.save()
        resp = self.client.post(self.url, self.valid_post())
        self.assertRedirects(resp, "/barang/", fetch_redirect_response=False)

    def test_error_nomor_membuka_langkah_2(self):
        resp = self.client.post(self.url, self.valid_post(phone="abc"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'data-start-step="2"')
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.is_onboarded)

    def test_error_persetujuan_membuka_langkah_3(self):
        data = self.valid_post()
        del data["accept_privacy"]
        resp = self.client.post(self.url, data)
        self.assertContains(resp, 'data-start-step="3"')

    def test_first_name_memakai_username_kalau_nama_kosong(self):
        self.profile.full_name = ""
        self.profile.save()
        self.assertEqual(self.client.get(self.url).context["first_name"], "rois")


# ------------------------------------------------------------------ profil
@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ProfileViewTests(TestCase):
    def setUp(self):
        self.user, self.profile = make_user()
        self.client.force_login(self.user)

    def test_profil_wajib_login(self):
        self.client.logout()
        for name in ("accounts:profile", "accounts:profile_edit"):
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 302)
            self.assertIn(reverse("accounts:login"), resp["Location"])

    def test_profil_saya(self):
        resp = self.client.get(reverse("accounts:profile"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Roisul Umam")
        self.assertContains(resp, reverse("accounts:profile_activity"))

    def test_edit_tampil(self):
        resp = self.client.get(reverse("accounts:profile_edit"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Edit Profil")

    def test_edit_valid(self):
        resp = self.client.post(reverse("accounts:profile_edit"), {
            "phone": "0812 3456 7890", "location": "Perpusat", "bio": "Halo semua",
        })
        self.assertRedirects(resp, reverse("accounts:profile"), fetch_redirect_response=False)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.phone, "081234567890")
        self.assertEqual(self.profile.location, "Perpusat")
        self.assertTrue(any("berhasil diperbarui" in m for m in msgs(resp)))

    def test_edit_dengan_foto(self):
        upload = SimpleUploadedFile("foto.png", png_bytes(), content_type="image/png")
        resp = self.client.post(reverse("accounts:profile_edit"), {"phone": "08123456789", "photo": upload})
        self.assertEqual(resp.status_code, 302)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.photo)

    def test_edit_tidak_valid(self):
        resp = self.client.post(reverse("accounts:profile_edit"), {"phone": "abc"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("phone", resp.context["form"].errors)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.phone, "")


class PublicProfileTests(TestCase):
    def setUp(self):
        self.viewer, _ = make_user("viewer", npm="2406000001", full_name="Pengunjung")
        self.owner, self.owner_profile = make_user("pemilik", npm="2506111111", full_name="Pemilik Barang")
        self.client.force_login(self.viewer)

    def url(self, profile):
        return reverse("accounts:profile_public", args=[profile.pk])

    def test_wajib_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url(self.owner_profile)).status_code, 302)

    def test_profil_aktif(self):
        resp = self.client.get(self.url(self.owner_profile))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Pemilik Barang")
        self.assertFalse(resp.context["is_owner"])
        self.assertEqual(resp.context["rating"], "-")
        self.assertEqual(resp.context["done_count"], 0)
        self.assertEqual(resp.context["review_count"], 0)

    def test_melihat_profil_sendiri(self):
        viewer_profile = Profile.objects.get(user=self.viewer)
        resp = self.client.get(self.url(viewer_profile))
        self.assertTrue(resp.context["is_owner"])

    def test_profil_tidak_ada(self):
        resp = self.client.get(reverse("accounts:profile_public", args=[99999]))
        self.assertEqual(resp.status_code, 404)

    def test_belum_onboarding_tidak_tampil(self):
        self.owner_profile.is_onboarded = False
        self.owner_profile.save()
        self.assertEqual(self.client.get(self.url(self.owner_profile)).status_code, 404)

    def test_akun_nonaktif_tidak_tersedia(self):
        from django.utils import timezone
        self.owner_profile.deactivated_at = timezone.now()
        self.owner_profile.save()
        resp = self.client.get(self.url(self.owner_profile))
        self.assertContains(resp, "Profil tidak tersedia", status_code=404)
        self.assertTemplateUsed(resp, "accounts/profile_unavailable.html")


# ------------------------------------------------------------------ toggle mode (AJAX)
class ToggleModeTests(TestCase):
    def setUp(self):
        self.user, self.profile = make_user()
        self.client.force_login(self.user)
        self.url = reverse("accounts:toggle_mode")

    def test_wajib_login(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url, {"mode": "seller"}).status_code, 302)

    def test_harus_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_ajax_membalas_json(self):
        resp = self.client.post(self.url, {"mode": "seller"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"mode": "seller", "label": "Minjemin", "is_seller": True})
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.mode, "seller")

    def test_ajax_kembali_ke_minjem(self):
        self.profile.mode = "seller"
        self.profile.save()
        resp = self.client.post(self.url, {"mode": "renter"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.json()["label"], "Minjem")

    def test_mode_tidak_valid_membalik_mode(self):
        resp = self.client.post(self.url, {"mode": "ngawur"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.json()["mode"], "seller")
        resp = self.client.post(self.url, {}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.json()["mode"], "renter")

    def test_tanpa_ajax_redirect_ke_next_yang_aman(self):
        resp = self.client.post(self.url, {"mode": "seller", "next": reverse("accounts:profile")})
        self.assertRedirects(resp, reverse("accounts:profile"), fetch_redirect_response=False)

    def test_tanpa_ajax_next_berbahaya_ke_beranda(self):
        resp = self.client.post(self.url, {"mode": "seller", "next": "http://evil.example/"})
        self.assertRedirects(resp, "/", fetch_redirect_response=False)


# ------------------------------------------------------------------ nonaktifkan akun
class DeactivateAccountTests(TestCase):
    def setUp(self):
        self.user, self.profile = make_user()
        self.client.force_login(self.user)
        self.url = reverse("accounts:deactivate")

    def test_wajib_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_halaman_konfirmasi(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Yang akan terjadi")
        self.assertEqual(resp.context["blocking"], [])

    def test_halaman_menampilkan_transaksi_penghalang(self):
        blocking = [{"label": "Kamu sedang meminjam Kamera dari Bagas", "status": "Terkonfirmasi"}]
        with mock.patch("accounts.views.get_blocking_transactions", return_value=blocking):
            resp = self.client.get(self.url)
        self.assertContains(resp, "Kamu belum bisa menonaktifkan akun")
        self.assertContains(resp, "Kamera dari Bagas")

    def test_tanpa_konfirmasi_tidak_dinonaktifkan(self):
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(any("Centang konfirmasi" in m for m in msgs(resp)))

    def test_terblokir_transaksi_berjalan(self):
        blocking = [{"label": "Pesanan berjalan", "status": "x"}]
        with mock.patch("accounts.views.get_blocking_transactions", return_value=blocking):
            resp = self.client.post(self.url, {"confirm": "yes"})
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertIsNone(self.profile.deactivated_at)
        self.assertTrue(any("transaksi berjalan" in m for m in msgs(resp)))

    def test_berhasil_dinonaktifkan(self):
        resp = self.client.post(self.url, {"confirm": "yes"})
        self.assertRedirects(resp, reverse("accounts:login"), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIsNotNone(self.profile.deactivated_at)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(any("dinonaktifkan" in m for m in msgs(resp)))


# ------------------------------------------------------------------ aktivitas (HTMX)
class ProfileActivityTests(TestCase):
    def setUp(self):
        self.user, self.profile = make_user()
        self.client.force_login(self.user)
        self.url = reverse("accounts:profile_activity")

    def test_anonim_mendapat_401_dan_hx_redirect(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)
        self.assertIn(reverse("accounts:login"), resp["HX-Redirect"])

    def test_mode_minjem_menampilkan_riwayat_pinjam(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "accounts/_activity.html")
        self.assertEqual(resp.context["kind"], "pesanan")
        self.assertContains(resp, "Riwayat Pinjam")
        self.assertContains(resp, "Belum ada riwayat pinjam")

    def test_mode_minjemin_menampilkan_barang(self):
        self.profile.mode = "seller"
        self.profile.save()
        resp = self.client.get(self.url)
        self.assertEqual(resp.context["kind"], "barang")
        self.assertContains(resp, "Barang Saya")
        self.assertContains(resp, "Belum ada barang")

    def test_tab_ulasan(self):
        resp = self.client.get(self.url, {"tab": "reviews"})
        self.assertEqual(resp.context["kind"], "ulasan")
        self.assertContains(resp, "Belum ada ulasan")

    def test_tab_tidak_dikenal_kembali_ke_main(self):
        resp = self.client.get(self.url, {"tab": "ngawur"})
        self.assertEqual(resp.context["tab"], "main")

    def test_halaman_kedua_hanya_mengirim_baris(self):
        self.profile.mode = "seller"
        self.profile.save()
        item = SimpleNamespace(
            pk=1, nama_barang="Kamera", foto_utama=None,
            kategori=SimpleNamespace(nama="Elektronik"),
            lokasi=SimpleNamespace(short_label="Kutek", nama_area="Kutek"),
            jenis_penawaran="gratis", status_penawaran="aktif", tarif_formatted="0",
        )
        with mock.patch.object(Barang.objects, "filter") as m_filter, \
                mock.patch("accounts.views.ACTIVITY_PAGE_SIZE", 1):
            m_filter.return_value.select_related.return_value.order_by.return_value = [item, item, item]
            resp = self.client.get(self.url, {"tab": "main", "page": 2})
        self.assertTemplateUsed(resp, "accounts/_activity_rows.html")
        self.assertTemplateNotUsed(resp, "accounts/_activity.html")
        self.assertContains(resp, "Kamera")
        self.assertContains(resp, "Muat lebih banyak")