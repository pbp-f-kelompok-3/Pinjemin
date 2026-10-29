from django import forms
from django.utils import timezone

from .models import Pesanan, Ulasan


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


class UlasanForm(forms.ModelForm):
    RATING_CHOICES = [
        (5, '⭐⭐⭐⭐⭐ (5 - Sangat Memuaskan)'),
        (4, '⭐⭐⭐⭐ (4 - Memuaskan)'),
        (3, '⭐⭐⭐ (3 - Cukup Baik)'),
        (2, '⭐⭐ (2 - Kurang Memuaskan)'),
        (1, '⭐ (1 - Tidak Memuaskan)'),
    ]
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.Select(),
        label="Beri Nilai Bintang"
    )
    komentar = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Ceritakan pengalamanmu meminjam barang ini: kondisi barang, ketepatan waktu serah terima di titik temu kampus, keramahan pemilik...'
        }),
        label="Ulasan & Komentar"
    )

    class Meta:
        model = Ulasan
        fields = ['rating', 'komentar']
