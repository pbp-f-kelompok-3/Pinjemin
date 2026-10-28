from django.urls import path
from . import views

app_name = "categories"

urlpatterns = [
    path("", views.show_categories, name="show_categories"),
    path("create/", views.create_category, name="create_category"),
    path("<int:category_id>/edit/", views.update_category, name="update_category"),
    path("<int:category_id>/delete/", views.delete_category, name="delete_category"),
]
