from django.db import models


class GeocodingCache(models.Model):
    """Shared lookup cache and upstream quota for every Django worker."""

    key = models.CharField(max_length=120, primary_key=True)
    data = models.JSONField(default=dict)
    expires_at = models.DateTimeField()
