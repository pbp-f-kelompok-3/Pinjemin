import math

from django.utils.html import strip_tags
from rest_framework import serializers

from .models import PickupLocation


class PickupLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocation
        fields = ('id', 'label', 'address', 'latitude', 'longitude')
        extra_kwargs = {
            'latitude': {'coerce_to_string': False},
            'longitude': {'coerce_to_string': False},
        }

    def validate(self, attrs):
        for field in ('label', 'address'):
            if field in attrs:
                attrs[field] = strip_tags(attrs[field]).strip()
                if not attrs[field]:
                    raise serializers.ValidationError({field: 'Kolom ini wajib diisi.'})
        return attrs

    def update(self, instance, validated_data):
        if validated_data:
            for field, value in validated_data.items():
                setattr(instance, field, value)
            # A partial edit must not overwrite another edit or reactivate a deleted location.
            instance.save(update_fields=[*validated_data, 'updated_at'])
        return instance


class NearbyQuerySerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    radius = serializers.ChoiceField(choices=(1, 2), default=1)

    def validate(self, attrs):
        for field in ('latitude', 'longitude'):
            if not math.isfinite(attrs[field]):
                raise serializers.ValidationError({field: 'Koordinat tidak valid.'})
        return attrs


class NearbyItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    price = serializers.CharField()
    offer = serializers.CharField()
    area = serializers.CharField()
    distance_km = serializers.FloatField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    is_approximate = serializers.BooleanField()
