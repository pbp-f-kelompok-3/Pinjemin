from django import forms
from django.utils.html import strip_tags

from .models import PickupLocation


class PickupLocationForm(forms.ModelForm):
    class Meta:
        model = PickupLocation
        fields = ['label', 'address', 'latitude', 'longitude']

    def clean_label(self):
        value = strip_tags(self.cleaned_data['label']).strip()
        if not value:
            raise forms.ValidationError('Isi label lokasi, misalnya Kos Kukusan.')
        return value

    def clean_address(self):
        value = strip_tags(self.cleaned_data['address']).strip()
        if not value:
            raise forms.ValidationError('Isi alamat penjemputan yang jelas.')
        return value
