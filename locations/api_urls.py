from django.urls import path

from .api_views import NearbyItemsView, PickupLocationViewSet

app_name = 'locations_api'

urlpatterns = [
    path(
        'lokasi-penjemputan/',
        PickupLocationViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='pickup_list',
    ),
    path(
        'lokasi-penjemputan/<int:pk>/',
        PickupLocationViewSet.as_view({'patch': 'partial_update', 'delete': 'destroy'}),
        name='pickup_detail',
    ),
    path('barang-terdekat/', NearbyItemsView.as_view(), name='nearby'),
]
