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

    current_kategori = request.GET.get("kategori", "").strip()
    selected_category = None
    if current_kategori.isdigit():
        selected_category = categories.filter(pk=current_kategori).first()

        if selected_category:
            items = items.filter(
                kategori=selected_category
            )

    price_type = request.GET.get("price_type", "")
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()

    if price_type == "gratis":
        items = items.filter(jenis_penawaran="gratis")
    elif price_type == "sewa":
        items = items.filter(jenis_penawaran="sewa")
    try:
        min_price_value = int(min_price) if min_price else None
        if min_price_value is not None and min_price_value >= 0:
            items = items.filter(
                tarif_per_hari__gte=min_price_value
            )
        else:
            min_price_value = None
    except ValueError:
        min_price_value = None

    try:
        max_price_value = int(max_price) if max_price else None
        if max_price_value is not None and max_price_value >= 0:
            items = items.filter(
                tarif_per_hari__lte=max_price_value
            )
        else:
            max_price_value = None
    except ValueError:
        max_price_value = None

    return render(request, "home.html", {
        "categories": categories,
        "barang_list": items,
        "current_q": q,
        "current_kategori": kategori_id,
        "selected_category": selected_category,
        "min_price": min_price_value,
        "max_price": max_price_value,
    })
