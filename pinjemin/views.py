from django.db.models import Q
from django.shortcuts import render

from barang.models import Barang
from categories.models import Category


def home(request):
    categories = Category.objects.all().order_by("name")

    q = request.GET.get('q', '').strip()
    kategori_id = request.GET.get('kategori', '').strip()
    price_type = request.GET.get("price_type", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    sort = request.GET.get("sort", "terbaru").strip()

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

    selected_category = None
    if kategori_id and kategori_id.isdigit():
        selected_category = Category.objects.filter(pk=kategori_id).first()

    if price_type == "gratis":
        items = items.filter(jenis_penawaran="gratis")
    elif price_type == "sewa":
        items = items.filter(jenis_penawaran="sewa")

    min_price_value = None
    if min_price:
        try:
            val = int(min_price)
            if val >= 0:
                min_price_value = val
                items = items.filter(tarif_per_hari__gte=val)
        except ValueError:
            min_price_value = None

    max_price_value = None
    if max_price:
        try:
            val = int(max_price)
            if val >= 0:
                max_price_value = val
                items = items.filter(tarif_per_hari__lte=val)
        except ValueError:
            max_price_value = None

    # Sorting options
    if sort == 'nama_asc':
        items = items.order_by('nama_barang')
    elif sort == 'nama_desc':
        items = items.order_by('-nama_barang')
    elif sort == 'harga_asc':
        items = items.order_by('tarif_per_hari', '-created_at')
    elif sort == 'harga_desc':
        items = items.order_by('-tarif_per_hari', '-created_at')
    elif sort == 'sering_dipinjam':
        items = items.order_by('-dilihat_count', '-created_at')
    else:
        sort = 'terbaru'
        items = items.order_by('-created_at')

    context = {
        "categories": categories,
        "barang_list": items,
        "current_q": q,
        "current_kategori": kategori_id,
        "selected_category": selected_category,
        "current_price_type": price_type,
        "current_min_price": min_price_value if min_price_value is not None else "",
        "current_max_price": max_price_value if max_price_value is not None else "",
        "min_price": min_price_value,
        "max_price": max_price_value,
        "current_sort": sort,
        "total_barang": items.count(),
    }

    return render(request, "home.html", context)
