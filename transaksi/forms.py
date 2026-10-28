from django import forms
from django.utils import timezone

from .models import Pesanan


class JadwalForm(forms.ModelForm):
    mulai = forms.DateTimeField(
        label="Tanggal dan jam mulai (WIB)",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
    )
    durasi = forms.IntegerField(label="Durasi (hari / 24 jam)", min_value=1, max_value=365)

    class Meta:
        model = Pesanan
        fields = ["mulai", "durasi"]

    def clean_mulai(self):
        mulai = self.cleaned_data["mulai"]
        if mulai <= timezone.now():
            raise forms.ValidationError("Pilih jadwal di masa depan.")
        return mulai
