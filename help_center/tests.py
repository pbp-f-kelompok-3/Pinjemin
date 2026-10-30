from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile

from .models import HelpCenterSetting, normalize_wa_number

User = get_user_model()


class HelpCenterTests(TestCase):
    def test_halaman_bantuan_untuk_anonim(self):
        resp = self.client.get(reverse("help_center:help"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "help_center/help.html")
        self.assertContains(resp, "Pusat Bantuan")

    def test_halaman_bantuan_memuat_tiga_bagian(self):
        resp = self.client.get(reverse("help_center:help"))
        for judul in ("Tutorial", "Kebijakan Privasi", "FAQ"):
            self.assertContains(resp, judul)

    def test_halaman_bantuan_untuk_user_login(self):
        user = User.objects.create_user(username="rois", password="x")
        Profile.objects.create(user=user, npm="2506620210", full_name="Roisul Umam", is_onboarded=True)
        self.client.force_login(user)
        resp = self.client.get(reverse("help_center:help"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Akun saya")  # navbar user login menampilkan link akun


class HelpCenterWhatsAppTests(TestCase):
    def test_tombol_wa_tersembunyi_kalau_nomor_belum_diatur(self):
        resp = self.client.get(reverse("help_center:help"))
        self.assertNotContains(resp, "wa.me")

    def test_tombol_wa_muncul_dengan_nomor_dari_pengaturan(self):
        setting = HelpCenterSetting.load()
        setting.whatsapp_number = "0812-3456-7890"
        setting.save()
        resp = self.client.get(reverse("help_center:help"))
        self.assertContains(resp, "https://wa.me/6281234567890?text=")
        self.assertContains(resp, "Chat via WhatsApp")

    def test_tombol_wa_hilang_kalau_dimatikan(self):
        setting = HelpCenterSetting.load()
        setting.whatsapp_number = "6281234567890"
        setting.is_active = False
        setting.save()
        resp = self.client.get(reverse("help_center:help"))
        self.assertNotContains(resp, "wa.me")

    def test_normalisasi_nomor(self):
        for raw in ("081234567890", "+62 812-3456-7890", "6281234567890", "81234567890"):
            self.assertEqual(normalize_wa_number(raw), "6281234567890")

    def test_pengaturan_singleton(self):
        HelpCenterSetting.load()
        HelpCenterSetting().save()
        self.assertEqual(HelpCenterSetting.objects.count(), 1)