from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class Profile(models.Model):
    class Mode(models.TextChoices):
        RENTER = "renter", "Minjem"
        SELLER = "seller", "Minjemin"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )

    # Data dari SSO UI (read-only di sisi user)
    npm = models.CharField(max_length=20, blank=True)
    full_name = models.CharField(max_length=150, blank=True)
    kode_org = models.CharField(max_length=50, blank=True)

    # Data yang bisa diedit user
    phone = models.CharField(
        max_length=16,
        blank=True,
        validators=[RegexValidator(r"^\+?\d{9,15}$", "Nomor HP tidak valid.")],
    )
    bio = models.TextField(max_length=300, blank=True)
    location = models.CharField(max_length=100, blank=True)
    photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)

    # Mode & onboarding
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.RENTER)
    is_onboarded = models.BooleanField(default=False)
    accepted_privacy_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name or self.user.username} ({self.npm})"

    @property
    def is_seller_mode(self):
        return self.mode == self.Mode.SELLER

    @property
    def angkatan(self):
        if self.npm[:2].isdigit():
            return 2000 + int(self.npm[:2])
        return None

    @property
    def completeness(self):
        checks = [
            ("Foto profil", bool(self.photo)),
            ("Nomor WhatsApp", bool(self.phone)),
            ("Titik temu favorit", bool(self.location)),
            ("Bio singkat", bool(self.bio)),
        ]
        done = sum(1 for _, ok in checks if ok)
        return {"checks": checks, "percent": round(done / len(checks) * 100)}
