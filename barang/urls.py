"""
@module: pinjemin.barang.urls
@author: Fauzan Taqiy Santosa (NPM: 2506607272)
@feature: Manajemen Barang Routing
@framework: Django 5.0+ MVT
"""

from django.urls import path
from . import views

app_name = 'barang'

urlpatterns = [
    # Dashboard Inventaris Barang Saya (Fauzan Taqiy Santosa)
    path('saya/', views.dashboard_barang_saya, name='dashboard'),

    # Formulir Pengelolaan Barang
    path('tambah/', views.tambah_barang, name='tambah'),
    path('tambah-ajax/', views.tambah_barang_ajax, name='tambah_ajax'),
    path('<int:pk>/', views.detail_barang, name='detail'),
    path('<int:pk>/edit/', views.edit_barang, name='edit'),
    path('<int:pk>/hapus/', views.hapus_barang, name='hapus'),
    path('<int:pk>/hapus-ajax/', views.hapus_barang_ajax, name='hapus_ajax'),

    # Endpoint Serialisasi Data (Standar PBP Fasilkom UI & Integrasi Mobile/Flutter)
    path('json/', views.show_json, name='show_json'),
    path('json/saya/', views.show_json_barang_saya, name='show_json_barang_saya'),
    path('json/<int:pk>/', views.show_json_by_id, name='show_json_by_id'),
    path('xml/', views.show_xml, name='show_xml'),
    path('xml/<int:pk>/', views.show_xml_by_id, name='show_xml_by_id'),
]
