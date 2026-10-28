
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Category
from .forms import CategoryForm

def show_categories(request):
    categories = Category.objects.all()

    return render(request, "categories/categories.html", {
        "categories":categories,
    })

@login_required
def create_category(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    
    if request.method == "POST":
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Kategori berhasil dibuat.")
            return redirect("categories:show_categories")
    else:
        form = CategoryForm()

    return render(request, "categories/category_form.html", {
        "form": form,
        "title": "Buat Kategori",
    })


@login_required
def update_category(request, category_id):
    if not request.user.is_superuser:
        raise PermissionDenied
    
    category = get_object_or_404(Category, pk=category_id)

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)

        if form.is_valid():
            form.save()
            messages.success(request, "Kategori berhasil diperbarui..")
            return redirect("categories:show_categories")
    else:
        form = CategoryForm(instance=category)

    return render(request, "categories/category_form.html", {
        "form": form,
        "title": "Perbarui Kategori",
    })

@login_required
def delete_category(request, category_id):
    if not request.user.is_superuser:
        raise PermissionDenied
    category = get_object_or_404(Category, pk=category_id)

    if request.method == "POST":
        category.delete()
        messages.success(request, "Kategori berhasil dihapus.")
        return redirect("categories:show_categories")

    return render(request, "categories/category_delete.html", {
        "category": category,
    })
