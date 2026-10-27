"""
@module: pinjemin.barang.forms
@author: Fauzan Taqiy Santosa (NPM: 2506607272)
@feature: Formulir Tambah & Edit Barang
@framework: Django 5.0+ MVT
"""

from django import forms
from django.utils.html import strip_tags
from .models import Barang, Kategori, Lokasi


class BarangForm(forms.ModelForm):
    """
    Formulir Pendaftaran Barang Baru (Fauzan Taqiy Santosa)
    Field sesuai spesifikasi README:
    - nama_barang, foto_utama, deskripsi, kategori, jenis_penawaran, tarif_per_hari, lokasi
    """
    class Meta:
        model = Barang
        fields = [
            'nama_barang',
            'foto_utama',
            'deskripsi',
            'kategori',
            'jenis_penawaran',
            'tarif_per_hari',
            'lokasi',
        ]
        widgets = {
            'nama_barang': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contoh: Jas Sidang Hitam Pria (Size L) - Bahan Wool Blend',
                'id': 'id_nama_barang',
                'required': 'required',
            }),
            'foto_utama': forms.FileInput(attrs={
                'class': 'form-file-input',
                'id': 'id_foto_utama',
                'accept': 'image/jpeg,image/png,image/webp',
                'required': 'required',
            }),
            'kategori': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_kategori',
                'required': 'required',
            }),
            'jenis_penawaran': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_jenis_penawaran',
            }),
            'deskripsi': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Jelaskan kondisi fisik barang (mulus/lecet pemakaian), kelengkapan aksesoris, aturan khusus pemakaian, dan ketentuan pengembalian...',
                'rows': 4,
                'maxlength': 1000,
                'id': 'id_deskripsi',
                'required': 'required',
            }),
            'tarif_per_hari': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '25000',
                'min': '0',
                'step': '1000',
                'id': 'id_tarif_per_hari',
            }),
            'lokasi': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_lokasi',
                'required': 'required',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tarif per hari tidak required di level field HTML agar barang gratis bisa disubmit tanpa error
        self.fields['tarif_per_hari'].required = False

    def clean_nama_barang(self):
        nama = strip_tags(self.cleaned_data.get("nama_barang", "")).strip()
        if not nama:
            raise forms.ValidationError("Nama barang tidak boleh kosong atau hanya berisi tag HTML.")
        return nama

    def clean_deskripsi(self):
        deskripsi = strip_tags(self.cleaned_data.get("deskripsi", "")).strip()
        if not deskripsi:
            raise forms.ValidationError("Deskripsi tidak boleh kosong atau hanya berisi tag HTML.")
        return deskripsi

    def clean(self):
        cleaned_data = super().clean()
        jenis = cleaned_data.get('jenis_penawaran')
        tarif = cleaned_data.get('tarif_per_hari')

        if jenis == 'gratis':
            cleaned_data['tarif_per_hari'] = 0
            if hasattr(self, 'instance') and self.instance:
                self.instance.tarif_per_hari = 0
        elif jenis == 'sewa':
            if tarif is None or tarif <= 0:
                self.add_error('tarif_per_hari', 'Tarif sewa harian harus lebih besar dari Rp 0 untuk barang sewa.')

        return cleaned_data


class BarangEditForm(BarangForm):
    """
    Formulir Edit Barang
    Menambahkan opsi Status Penawaran (Aktif vs Nonaktifkan Sementara)
    dan foto utama bersifat opsional saat edit jika sudah ada foto sebelumnya.
    """
    class Meta(BarangForm.Meta):
        fields = BarangForm.Meta.fields + ['status_penawaran']
        widgets = {
            **BarangForm.Meta.widgets,
            'status_penawaran': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_status_penawaran',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Foto utama tidak wajib diisi ulang jika sudah ada
        if self.instance and self.instance.pk and self.instance.foto_utama:
            self.fields['foto_utama'].required = False
            self.fields['foto_utama'].widget.attrs.pop('required', None)
