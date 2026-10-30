import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

DEFAULT_WA_MESSAGE = "Halo Customer Care Pinjemin, saya butuh bantuan."


def normalize_wa_number(raw: str) -> str:
    """Ubah input bebas (0812-3456-7890, +62 812..., 812...) jadi format wa.me: 62812...."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    elif digits.startswith("8"):
        digits = "62" + digits
    return digits


class HelpCenterSetting(models.Model):
    """Pengaturan Pusat Bantuan. Singleton: hanya satu baris (pk=1), diatur lewat admin."""

    whatsapp_number = models.CharField(
        "Nomor WhatsApp Customer Care",
        max_length=20,
        blank=True,
        validators=[RegexValidator(r"^[0-9+\-\s]*$", "Hanya boleh angka, spasi, '+', atau '-'.")],
        help_text="Contoh: 0812-3456-7890 atau +62 812 3456 7890. Otomatis diubah ke format 62xxxxxxxxxx.",
    )
    whatsapp_message = models.CharField(
        "Pesan awal WhatsApp",
        max_length=200,
        blank=True,
        default=DEFAULT_WA_MESSAGE,
        help_text="Teks yang sudah terisi saat pengguna membuka chat. Boleh dikosongkan.",
    )
    is_active = models.BooleanField(
        "Tampilkan tombol WhatsApp",
        default=True,
        help_text="Matikan untuk menyembunyikan tombol tanpa menghapus nomor.",
    )

    class Meta:
        verbose_name = "Pengaturan Pusat Bantuan"
        verbose_name_plural = "Pengaturan Pusat Bantuan"

    def __str__(self):
        return "Pengaturan Pusat Bantuan"

    def clean(self):
        super().clean()
        if self.whatsapp_number:
            number = normalize_wa_number(self.whatsapp_number)
            if not 9 <= len(number) <= 15:
                raise ValidationError({"whatsapp_number": "Nomor WhatsApp tidak valid."})
            self.whatsapp_number = number

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        self.whatsapp_number = normalize_wa_number(self.whatsapp_number)
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def whatsapp_url(self) -> str:
        """URL wa.me, atau string kosong kalau belum diatur / dimatikan."""
        from urllib.parse import quote

        if not self.is_active or not self.whatsapp_number:
            return ""
        url = f"https://wa.me/{self.whatsapp_number}"
        if self.whatsapp_message:
            url += f"?text={quote(self.whatsapp_message)}"
        return url