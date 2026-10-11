import re

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from .models import Profile

MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_PHOTO_EXT = (".jpg", ".jpeg", ".png")


class PhotoValidationMixin:
    """Validasi foto di sisi server (ukuran dan format)."""

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if isinstance(photo, UploadedFile):  # hanya validasi file yang baru diunggah
            if photo.size > MAX_PHOTO_BYTES:
                raise ValidationError("Ukuran foto maksimal 10 MB.")
            if not photo.name.lower().endswith(ALLOWED_PHOTO_EXT):
                raise ValidationError("Format foto harus JPG, JPEG, atau PNG.")
        return photo


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-control"
            field.widget.attrs["class"] = css


class ProfileForm(PhotoValidationMixin, BootstrapFormMixin, forms.ModelForm):
    """Form edit profil (halaman /akun/profil/edit/)."""

    class Meta:
        model = Profile
        fields = ["photo", "phone", "location", "bio"]
        labels = {"location": "Titik temu favorit"}
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}


class OnboardingForm(PhotoValidationMixin, forms.ModelForm):
    """Form onboarding 3 langkah. Tampilan dirender manual di onboarding.html."""

    phone = forms.CharField(
        max_length=20,
        error_messages={"required": "Nomor WhatsApp wajib diisi."},
        widget=forms.TextInput(attrs={
            "placeholder": "08XXXXXXXXXX",
            "inputmode": "tel",
            "autocomplete": "tel",
        }),
    )
    accept_privacy = forms.BooleanField(
        error_messages={"required": "Kamu harus menyetujui Kebijakan Privasi & Ketentuan Pinjemin."},
    )

    class Meta:
        model = Profile
        fields = ["photo", "phone", "location", "bio", "mode"]
        widgets = {
            "photo": forms.FileInput(attrs={
                "accept": ".jpg,.jpeg,.png,image/jpeg,image/png",
                "class": "sr-only",
            }),
            "location": forms.TextInput(attrs={"placeholder": "mis. Kutek, Perpusat, Kantin Fasilkom"}),
            "bio": forms.Textarea(attrs={
                "rows": 4,
                "maxlength": 300,
                "placeholder": "Aku suka kucing dan aku juga bermain game",
            }),
        }

    def clean_phone(self):
        raw = re.sub(r"[\s\-]", "", self.cleaned_data["phone"])
        if not re.fullmatch(r"\+?\d{9,15}", raw):
            raise ValidationError("Nomor WhatsApp tidak valid. Contoh: 08123456789.")
        return raw