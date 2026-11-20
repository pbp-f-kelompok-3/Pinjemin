from django.urls import include, path
from categories import api_views

app_name = "api"
urlpatterns = [
    path("categories/", api_views.category_list, name="category-list"),
]