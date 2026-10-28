from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class GeocodingCache(models.Model):
    """Shared lookup cache and upstream quota for every Django worker."""

    key = models.CharField(max_length=120, primary_key=True)
    data = models.JSONField(default=dict)
    expires_at = models.DateTimeField()


class PickupLocation(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name='pickup_locations')
    label = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6,
                                   validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.DecimalField(max_digits=10, decimal_places=6,
                                    validators=[MinValueValidator(-180), MaxValueValidator(180)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-pk']

    def __str__(self):
        return self.label

    def as_dict(self):
        return {'id': self.pk, 'label': self.label, 'address': self.address,
                'latitude': float(self.latitude), 'longitude': float(self.longitude)}
