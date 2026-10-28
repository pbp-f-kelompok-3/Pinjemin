from django.urls import path

from . import views

app_name = 'locations'

urlpatterns = [
    path('terkini/', views.current_location, name='current'),
    path('tersimpan/', views.saved_locations, name='saved'),
    path('api/penjemputan/', views.pickup_locations, name='pickup_list'),
    path('api/penjemputan/<int:pk>/', views.pickup_location_detail, name='pickup_detail'),
]
