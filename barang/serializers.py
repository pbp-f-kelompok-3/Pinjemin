"""
@module: pinjemin.barang.serializers
@author: Fauzan Taqiy Santosa (NPM: 2506607272)
@feature: DRF Serializer untuk Integrasi Flutter/Mobile
@framework: Django REST Framework
"""

from rest_framework import serializers
from .models import Barang


class BarangSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barang
        fields = [
            'id',
            'nama_barang',
            'deskripsi',
            'jenis_penawaran',
            'tarif_per_hari',
            'status_penawaran',
            'foto_utama',
            'kategori',
            'lokasi',
            'created_at',
        ]
