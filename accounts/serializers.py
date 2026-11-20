"""DRF serializers for the Pinjemin Flutter app."""
from rest_framework import serializers

from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    angkatan = serializers.IntegerField(read_only=True, allow_null=True)
    photo_url = serializers.SerializerMethodField()
    mode_label = serializers.CharField(source="get_mode_display", read_only=True)
    is_seller = serializers.BooleanField(source="is_seller_mode", read_only=True)
    completeness = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "id",
            "username",
            "npm",
            "full_name",
            "kode_org",
            "angkatan",
            "phone",
            "bio",
            "location",
            "photo_url",
            "mode",
            "mode_label",
            "is_seller",
            "is_onboarded",
            "completeness",
            "created_at",
        ]
        read_only_fields = fields

    def get_photo_url(self, profile):
        if not profile.photo:
            return None
        request = self.context.get("request")
        url = profile.photo.url
        return request.build_absolute_uri(url) if request else url

    def get_completeness(self, profile):
        completeness = profile.completeness
        return {
            "percent": completeness["percent"],
            "checks": [{"label": label, "done": done} for label, done in completeness["checks"]],
        }
