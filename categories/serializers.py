from django.utils.html import strip_tags
from rest_framework import serializers

from .models import Category

class CategorySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.username", read_only=True)
    icon_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "name", "icon_url"
        ]
        read_only_fields = fields

    def validate_name(self, value):
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Isi nama kategori.")
        return value

    def get_icon_url(self, obj):
        if obj.icon_url:
            return obj.icon_url
        return None

