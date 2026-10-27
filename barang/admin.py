from django.contrib import admin
from .models import Kategori, Lokasi, Barang


@admin.register(Kategori)
class KategoriAdmin(admin.ModelAdmin):
    list_display = ('nama', 'slug')
    prepopulated_fields = {'slug': ('nama',)}
    search_fields = ('nama', 'deskripsi')


@admin.register(Lokasi)
class LokasiAdmin(admin.ModelAdmin):
    list_display = ('nama_area', 'short_label', 'patokan', 'kode_pos')
    search_fields = ('nama_area', 'short_label', 'patokan')


@admin.register(Barang)
class BarangAdmin(admin.ModelAdmin):
    list_display = (
        'nama_barang',
        'pemilik',
        'kategori',
        'jenis_penawaran',
        'tarif_per_hari',
        'lokasi',
        'status_penawaran',
        'dilihat_count',
        'created_at',
    )
    list_filter = ('jenis_penawaran', 'status_penawaran', 'kategori', 'lokasi')
    search_fields = ('nama_barang', 'deskripsi', 'pemilik__username')
    readonly_fields = ('dilihat_count', 'created_at', 'updated_at')
