"""
@module: pinjemin.barang.forms
@author: Fauzan Taqiy Santosa (NPM: 2506607272)
@feature: Formulir Tambah & Edit Barang
@framework: Django 5.0+ MVT
"""

from django import forms
from django.utils.html import strip_tags
from locations.models import PickupLocation
from .models import Barang, Kategori, Lokasi
from .services import visible_item_locations


class BarangForm(forms.ModelForm):
    """
    Formulir Pendaftaran Barang Baru (Fauzan Taqiy Santosa)
    Field sesuai spesifikasi README:
    - nama_barang, foto_utama, deskripsi, kategori, jenis_penawaran, tarif_per_hari, lokasi
    """
    pickup_location = forms.ModelChoiceField(queryset=PickupLocation.objects.none(), required=False,
                                            widget=forms.HiddenInput)
    pickup_latitude = forms.DecimalField(max_digits=9, decimal_places=6, min_value=-90,
                                        max_value=90, required=False, widget=forms.HiddenInput)
    pickup_longitude = forms.DecimalField(max_digits=10, decimal_places=6, min_value=-180,
                                         max_value=180, required=False, widget=forms.HiddenInput)
    pickup_mode = forms.CharField(required=False, initial='saved', widget=forms.HiddenInput)

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
            'pickup_location', 'pickup_latitude', 'pickup_longitude', 'pickup_mode',
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
                'step': '1',
                'id': 'id_tarif_per_hari',
            }),
            'lokasi': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_lokasi',
                'required': 'required',
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.current_pickup = self.instance.lokasi if self.instance.pk else None
        # Tarif per hari tidak required di level field HTML agar barang gratis bisa disubmit tanpa error
        self.fields['tarif_per_hari'].required = False
        if not self.is_bound and not self.instance.pk:
            self.initial['tarif_per_hari'] = ''
        self.fields['lokasi'].required = False
        self.fields['lokasi'].label = 'Lokasi penjemputan'
        self.fields['lokasi'].queryset = visible_item_locations(user)
        if user is not None and user.is_authenticated:
            self.fields['pickup_location'].queryset = PickupLocation.objects.filter(
                owner=user, is_active=True)

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

    def clean_foto_utama(self):
        photo = self.cleaned_data.get('foto_utama')
        if photo and hasattr(photo, 'content_type'):
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Ukuran foto maksimal 5 MB.')
            if photo.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
                raise forms.ValidationError('Gunakan foto dalam format JPG, PNG, atau WebP.')
        return photo

    def clean(self):
        cleaned_data = super().clean()
        location = cleaned_data.get('pickup_location')
        if location is not None:
            latitude = cleaned_data.get('pickup_latitude')
            longitude = cleaned_data.get('pickup_longitude')
            if latitude is None and longitude is None:
                cleaned_data['pickup_latitude'] = location.latitude
                cleaned_data['pickup_longitude'] = location.longitude
            elif latitude is None or longitude is None:
                self.add_error('pickup_location', 'Pilih titik penjemputan yang valid pada peta.')
        elif cleaned_data.get('pickup_mode') == 'current' and self.current_pickup is not None:
            # Use the item's original location, never a different ID supplied by the browser.
            cleaned_data['lokasi'] = self.current_pickup
            latitude = cleaned_data.get('pickup_latitude')
            longitude = cleaned_data.get('pickup_longitude')
            if latitude is None and longitude is None:
                cleaned_data['pickup_latitude'] = self.current_pickup.latitude
                cleaned_data['pickup_longitude'] = self.current_pickup.longitude
            elif latitude is None or longitude is None:
                self.add_error('pickup_location', 'Isi kedua koordinat atau pilih titik pada peta.')
        elif self.current_pickup is not None:
            # Fallback aman saat edit: pertahankan lokasi saat ini jika user tidak mengubah lokasi
            cleaned_data['lokasi'] = self.current_pickup
            cleaned_data['pickup_mode'] = 'current'
            if not cleaned_data.get('pickup_latitude'):
                cleaned_data['pickup_latitude'] = self.current_pickup.latitude
            if not cleaned_data.get('pickup_longitude'):
                cleaned_data['pickup_longitude'] = self.current_pickup.longitude
        elif cleaned_data.get('pickup_mode') or not cleaned_data.get('lokasi'):
            self.add_error('pickup_location', 'Pilih lokasi dari riwayat atau simpan lokasi baru terlebih dahulu.')
        jenis = cleaned_data.get('jenis_penawaran')
        tarif = cleaned_data.get('tarif_per_hari')

        if jenis == 'gratis':
            cleaned_data['tarif_per_hari'] = 0
            if hasattr(self, 'instance') and self.instance:
                self.instance.tarif_per_hari = 0
        elif jenis == 'sewa':
            if tarif is None:
                self.add_error('tarif_per_hari', 'Tarif sewa harian wajib diisi untuk barang sewa (tidak boleh kosong).')
            elif tarif <= 0:
                self.add_error('tarif_per_hari', 'Tarif sewa harian tidak boleh Rp 0 atau bernilai minus. Tentukan tarif minimal Rp 1.')

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
        if self.current_pickup is not None:
            self.initial.update({
                'pickup_mode': 'current',
                'pickup_latitude': self.current_pickup.latitude,
                'pickup_longitude': self.current_pickup.longitude,
            })
        # Foto utama tidak pernah wajib diisi ulang saat edit barang
        self.fields['foto_utama'].required = False
        self.fields['foto_utama'].widget.attrs.pop('required', None)
        self.fields['tarif_per_hari'].widget.attrs['step'] = '1'
