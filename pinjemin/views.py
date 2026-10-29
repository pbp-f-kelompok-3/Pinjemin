from django.db.models import Q
from django.shortcuts import render

from barang.models import Barang
from categories.models import Category


def home(request):
    categories = Category.objects.all().order_by("name")

    q = request.GET.get('q', '').strip()
    kategori_id = request.GET.get('kategori', '').strip()

    items = Barang.objects.filter(status_penawaran='aktif').select_related(
        'kategori', 'lokasi', 'pemilik', 'pemilik__profile'
    )
    if q:
        items = items.filter(
            Q(nama_barang__icontains=q) |
            Q(deskripsi__icontains=q) |
            Q(kategori__name__icontains=q)
        )
    if kategori_id and kategori_id != 'all':
        items = items.filter(kategori_id=kategori_id)

    items = items.order_by('-created_at')

    selected_category = None
    if kategori_id and kategori_id.isdigit():
        selected_category = Category.objects.filter(pk=kategori_id).first()

    return render(request, "home.html", {
        "categories": categories,
        "barang_list": items,
        "current_q": q,
        "current_kategori": kategori_id,
        "selected_category": selected_category,
    })
