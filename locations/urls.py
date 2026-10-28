from django.urls import path

from . import views

app_name = 'locations'

urlpatterns = [
    path('terkini/', views.current_location, name='current'),
]
