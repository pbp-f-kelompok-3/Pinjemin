"""
@module: pinjemin.barang.models
@author: Fauzan Taqiy Santosa (NPM: 2506607272)
@feature: Manajemen Barang (Manajemen Inventaris, Formulir Barang, Moderasi Admin)
@framework: Django 5.0+ MVT
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from categories.models import Category


class Kategori(models.Model):
    """
    Model Kategori Barang.
    CATATAN INTEGRASI (Modul Manajemen Kategori - Chelsea Stania Passikha):
    Model ini bertindak sebagai baseline entitas kategori agar relasi ForeignKey
    pada Barang dapat berfungsi. Saat modul Chelsea di-merge, relasi dapat
    langsung disambungkan ke model Kategori/Category milik Chelsea.
    """
    nama = models.CharField(max_length=100, unique=True, verbose_name=_("Nama Kategori"))
    slug = models.SlugField(max_length=100, unique=True)
    deskripsi = models.TextField(blank=True, verbose_name=_("Deskripsi Kategori"))

    class Meta:
        verbose_name = _("Kategori")
        verbose_name_plural = _("Kategori")
        ordering = ['nama']

    def __str__(self):
        return self.nama


class Lokasi(models.Model):
    """
    Lokasi penjemputan pada barang, termasuk salinan titik dari riwayat akun.
    CATATAN INTEGRASI (Modul Manajemen Lokasi - I Nyoman Yadnya Suta Karmana):
    Model ini bertindak sebagai baseline klaster area kampus agar relasi ForeignKey
    pada Barang dapat berfungsi. Saat modul Nyoman di-merge, titik lokasi / OpenStreetMap
    dapat langsung disambungkan ke model Lokasi/TitikLokasi milik Nyoman.
    """
    nama_area = models.CharField(max_length=150, verbose_name=_("Nama Area Kampus"))
    kecamatan_kota = models.CharField(max_length=200, blank=True, default="Kecamatan Beji, Kota Depok, Jawa Barat")
    kode_pos = models.CharField(max_length=10, blank=True, default="16425")
    patokan = models.CharField(max_length=255, verbose_name=_("Patokan Lokasi"))
    short_label = models.CharField(max_length=50, verbose_name=_("Label Ringkas"))
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                              null=True, blank=True, related_name='item_pickup_snapshots')
    full_address = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    is_pickup_snapshot = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Lokasi Kampus")
        verbose_name_plural = _("Lokasi Kampus")
        ordering = ['nama_area']

    def __str__(self):
        return f"{self.nama_area} ({self.short_label})"


class Barang(models.Model):
    """
    Model Inti Manajemen Barang Pinjemin (Fauzan Taqiy Santosa):
    - 1 Foto Utama produk asli (ImageField)
    - Pemilik terhubung ke User (ForeignKey)
    - Jenis Penawaran: Gratis atau Sewa
    - Status Penawaran: Aktif Ditawarkan atau Nonaktifkan Sementara
    - Validasi Aturan Bisnis Rule #1, #2, #4, #6, #9, #10
    """
    JENIS_PENAWARAN_CHOICES = [
        ('gratis', _('Pinjam Tanpa Biaya (Gratis)')),
        ('sewa', _('Sewa dengan Tarif Harian (Berbayar)')),
    ]

    STATUS_PENAWARAN_CHOICES = [
        ('aktif', _('Aktif Ditawarkan')),
        ('nonaktif', _('Nonaktifkan Sementara')),
    ]

    pemilik = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='barang_milik',
        verbose_name=_("Pemilik Barang")
    )
    nama_barang = models.CharField(
        max_length=200,
        verbose_name=_("Nama Barang"),
        help_text=_("Gunakan nama yang spesifik dan jelas mencakup ukuran, tipe, atau seri barang.")
    )
    foto_utama = models.ImageField(
        upload_to='barang/fotos/%Y/%m/',
        verbose_name=_("Foto Barang Utama"),
        help_text=_("Unggah 1 foto produk asli dengan pencahayaan jelas. Format JPG, PNG, atau WebP (Maks. 5MB).")
    )
    deskripsi = models.TextField(
        max_length=1000,
        verbose_name=_("Deskripsi Lengkap"),
        help_text=_("Jelaskan kondisi fisik, kelengkapan, cara pemakaian, dan aturan bagi peminjam.")
    )
    kategori = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='daftar_barang',
        verbose_name=_("Kategori Barang")
    )
    jenis_penawaran = models.CharField(
        max_length=10,
        choices=JENIS_PENAWARAN_CHOICES,
        default='sewa',
        verbose_name=_("Jenis Peminjaman")
    )
    tarif_per_hari = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Tarif Sewa Harian (Rp)"),
        help_text=_("Tarif dihitung per hari (24 jam). Bernilai 0 jika jenis pinjam adalah Gratis.")
    )
    lokasi = models.ForeignKey(
        Lokasi,
        on_delete=models.PROTECT,
        related_name='barang_di_lokasi',
        verbose_name=_("Lokasi Penjemputan")
    )
    status_penawaran = models.CharField(
        max_length=10,
        choices=STATUS_PENAWARAN_CHOICES,
        default='aktif',
        verbose_name=_("Status Penawaran")
    )
    dilihat_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Jumlah Dilihat")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Waktu Ditambahkan"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Waktu Diperbarui"))

    class Meta:
        verbose_name = _("Barang")
        verbose_name_plural = _("Daftar Barang")
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        # Aturan Bisnis #10: Barang gratis tidak boleh memiliki tarif sewa
        if self.jenis_penawaran == 'gratis':
            self.tarif_per_hari = 0
        elif self.jenis_penawaran == 'sewa' and (self.tarif_per_hari is None or self.tarif_per_hari <= 0):
            raise ValidationError({
                'tarif_per_hari': _("Tarif sewa harian harus lebih besar dari Rp 0 untuk barang sewa.")
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_sedang_dipinjam(self):
        """
        CATATAN INTEGRASI (Modul Manajemen Transaksi - Alphard Qodaruddin):
        Mengecek apakah barang sedang dalam masa peminjaman aktif melalui
        relasi pesanan / transaksi dari modul Alphard.
        """
        for rel_name in ['daftar_pesanan', 'pesanan_set', 'transaksi_set', 'transaksi']:
            manager = getattr(self, rel_name, None)
            if manager is not None and hasattr(manager, 'filter'):
                active_statuses = ['aktif', 'dikonfirmasi', 'dipinjam', 'menunggu_pengembalian', 'menunggu pembayaran']
                for st in active_statuses:
                    if manager.filter(models.Q(status__iexact=st) | models.Q(status_transaksi__iexact=st)).exists():
                        return True
        return False

    def can_be_deleted(self):
        """
        Aturan Bisnis #6:
        Barang yang sedang dipinjam TIDAK BOLEH dihapus oleh pemilik.
        """
        return not self.is_sedang_dipinjam

    @property
    def tarif_formatted(self):
        """Format tarif ke format ribuan rupiah Indonesia (misal 50000 -> 50.000)"""
        if self.tarif_per_hari:
            return f"{self.tarif_per_hari:,}".replace(',', '.')
        return "0"

    def __str__(self):
        return f"{self.nama_barang} ({self.get_jenis_penawaran_display()})"
