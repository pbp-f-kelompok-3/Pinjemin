from django.urls import path
from . import views

app_name = "transaksi"
urlpatterns = [
    path("", views.daftar, name="daftar"),
    path("barang/", views.katalog, name="katalog"),
    path("masuk/", views.masuk, name="masuk"),
    path("checkout/<int:item_id>/", views.buat, name="buat"),
    path("midtrans/notification/", views.webhook, name="webhook"),
    path("<uuid:pk>/", views.detail, name="detail"),
    path("<uuid:pk>/edit/", views.edit, name="edit"),
    path("<uuid:pk>/hapus/", views.hapus, name="hapus"),
    path("<uuid:pk>/ajukan/", views.ajukan, name="ajukan"),
    path("<uuid:pk>/batalkan/", views.batalkan, name="batalkan"),
    path("<uuid:pk>/bayar/", views.bayar, name="bayar"),
    path("<uuid:pk>/periksa/", views.periksa, name="periksa"),
]
