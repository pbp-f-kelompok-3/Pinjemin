from django.shortcuts import render

from categories.models import Category

def home(request):
    categories = Category.objects.all().order_by("name")

    return render(request, "home.html", {
        "categories": categories,
    })
