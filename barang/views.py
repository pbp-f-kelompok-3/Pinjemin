"""
@module: pinjemin.barang.views
@author: Fauzan Taqiy Santosa (NPM: 2506607272)
@feature: Manajemen Barang (Dashboard Barang Saya, Tambah, Edit, Hapus, dan API JSON/XML)
@framework: Django 5.0+ MVT
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.paginator import Paginator
from django.core import serializers
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from .models import Barang, Kategori, Lokasi
from .forms import BarangForm, BarangEditForm


@login_required
def dashboard_barang_saya(request):
    """
    DASHBOARD BARANG SAYA (Fauzan Taqiy Santosa)
    Menampilkan seluruh inventaris barang milik pengguna yang login:
    - Metrik: Total Barang, Barang Tersedia, Sedang Dipinjam, Tidak Aktif.
    - Filter tab status: Semua, Tersedia, Sedang Dipinjam, Tidak Aktif.
    - Pencarian teks & filter kategori.
    - Pengurutan (terbaru, nama, tarif, populer).
    - Paginasi daftar barang.
    """
    user = request.user
    queryset = Barang.objects.filter(pemilik=user).select_related('kategori', 'lokasi')

    # Metrik Ringkasan
    total_barang = queryset.count()
    barang_tersedia = sum(1 for b in queryset if b.status_penawaran == 'aktif' and not b.is_sedang_dipinjam)
    sedang_dipinjam = sum(1 for b in queryset if b.is_sedang_dipinjam)
    tidak_aktif = queryset.filter(status_penawaran='nonaktif').count()

    # Filter Tab
    tab = request.GET.get('tab', 'semua')
    if tab == 'tersedia':
        queryset = [b for b in queryset if b.status_penawaran == 'aktif' and not b.is_sedang_dipinjam]
    elif tab == 'sedang_dipinjam':
        queryset = [b for b in queryset if b.is_sedang_dipinjam]
    elif tab == 'tidak_aktif':
        queryset = queryset.filter(status_penawaran='nonaktif')

    # Filter Kategori
    kategori_id = request.GET.get('kategori')
    if kategori_id and kategori_id != 'all':
        if isinstance(queryset, list):
            queryset = [b for b in queryset if str(b.kategori_id) == str(kategori_id)]
        else:
            queryset = queryset.filter(kategori_id=kategori_id)

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        if isinstance(queryset, list):
            queryset = [
                b for b in queryset
                if q.lower() in b.nama_barang.lower() or q.lower() in b.deskripsi.lower()
            ]
        else:
            queryset = queryset.filter(Q(nama_barang__icontains=q) | Q(deskripsi__icontains=q))

    # Sorting
    sort = request.GET.get('sort', 'terbaru')
    if isinstance(queryset, list):
        if sort == 'nama_asc':
            queryset.sort(key=lambda x: x.nama_barang.lower())
        elif sort == 'harga_asc':
            queryset.sort(key=lambda x: x.tarif_per_hari)
        elif sort == 'sering_dipinjam':
            queryset.sort(key=lambda x: x.dilihat_count, reverse=True)
        else:
            queryset.sort(key=lambda x: x.created_at, reverse=True)
    else:
        if sort == 'nama_asc':
            queryset = queryset.order_by('nama_barang')
        elif sort == 'harga_asc':
            queryset = queryset.order_by('tarif_per_hari')
        elif sort == 'sering_dipinjam':
            queryset = queryset.order_by('-dilihat_count')
        else:
            queryset = queryset.order_by('-created_at')

    # Paginasi (6 item per halaman)
    paginator = Paginator(queryset, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    kategori_list = Kategori.objects.all()
    lokasi_list = Lokasi.objects.all()

    context = {
        'page_obj': page_obj,
        'total_barang': total_barang,
        'barang_tersedia': barang_tersedia,
        'sedang_dipinjam': sedang_dipinjam,
        'tidak_aktif': tidak_aktif,
        'kategori_list': kategori_list,
        'lokasi_list': lokasi_list,
        'active_tab': tab,
        'current_kategori': kategori_id or 'all',
        'current_q': q,
        'current_sort': sort,
    }
    return render(request, 'barang/dashboard.html', context)


@login_required
def tambah_barang(request):
    """
    FORM TAMBAH BARANG (Fauzan Taqiy Santosa)
    Daftarkan barang baru dengan foto produk asli, kategori, jenis penawaran, tarif, dan lokasi.
    Pemilik otomatis terisi dari request.user.
    """
    if request.method == 'POST':
        form = BarangForm(request.POST, request.FILES)
        if form.is_valid():
            barang = form.save(commit=False)
            barang.pemilik = request.user
            barang.save()
            messages.success(
                request,
                f"Barang '{barang.nama_barang}' berhasil didaftarkan ke inventaris Barang Saya."
            )
            return redirect('barang:dashboard')
        else:
            messages.error(request, "Silakan periksa kembali kolom formulir yang belum sesuai.")
    else:
        form = BarangForm()

    kategori_list = Kategori.objects.all()
    lokasi_list = Lokasi.objects.all()

    context = {
        'form': form,
        'kategori_list': kategori_list,
        'lokasi_list': lokasi_list,
    }
    return render(request, 'barang/tambah.html', context)


@login_required
def edit_barang(request, pk):
    """
    FORM EDIT BARANG (Fauzan Taqiy Santosa)
    Edit barang yang sudah ada. Hanya pemilik sah yang dapat mengakses.
    Menyediakan pengaturan Status Penawaran (Aktif vs Nonaktifkan Sementara).
    """
    barang = get_object_or_404(Barang, pk=pk, pemilik=request.user)

    if request.method == 'POST':
        form = BarangEditForm(request.POST, request.FILES, instance=barang)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Perubahan informasi barang '{barang.nama_barang}' berhasil disimpan."
            )
            return redirect('barang:dashboard')
        else:
            messages.error(request, "Terjadi kesalahan validasi saat menyimpan perubahan.")
    else:
        form = BarangEditForm(instance=barang)

    kategori_list = Kategori.objects.all()
    lokasi_list = Lokasi.objects.all()

    context = {
        'form': form,
        'barang': barang,
        'kategori_list': kategori_list,
        'lokasi_list': lokasi_list,
    }
    return render(request, 'barang/edit.html', context)


@login_required
@require_POST
def hapus_barang(request, pk):
    """
    PEMROSESAN HAPUS BARANG (Fauzan Taqiy Santosa)
    Backend view pemrosesan POST penghapusan barang:
    - Wajib POST dengan CSRF protection
    - Hanya pemilik sah
    - Memvalidasi Aturan Bisnis Rule #6: Barang yang sedang dipinjam TIDAK DAPAT dihapus.
    """
    barang = get_object_or_404(Barang, pk=pk, pemilik=request.user)

    if not barang.can_be_deleted():
        messages.error(
            request,
            f"Barang '{barang.nama_barang}' tidak dapat dihapus karena saat ini sedang dalam masa peminjaman aktif!"
        )
        return redirect('barang:dashboard')

    nama = barang.nama_barang
    barang.delete()
    messages.success(
        request,
        f"Barang '{nama}' telah berhasil dihapus dari inventaris Barang Saya."
    )
    return redirect('barang:dashboard')


# ==============================================================================
# SERIALISASI DATA: JSON & XML (STANDAR PROYEK PBP FASILKOM UI & INTEGRASI FLUTTER)
# ==============================================================================

def show_json(request):
    """Mengembalikan seluruh barang aktif dalam format JSON untuk integrasi API / Flutter."""
    data = Barang.objects.filter(status_penawaran='aktif').select_related('kategori', 'lokasi', 'pemilik')
    return HttpResponse(serializers.serialize("json", data), content_type="application/json")


def show_json_by_id(request, pk):
    """Mengembalikan data 1 barang spesifik berdasarkan ID dalam format JSON."""
    data = Barang.objects.filter(pk=pk)
    return HttpResponse(serializers.serialize("json", data), content_type="application/json")


@login_required
def show_json_barang_saya(request):
    """Mengembalikan daftar barang milik pengguna yang sedang login dalam format JSON."""
    data = Barang.objects.filter(pemilik=request.user)
    return HttpResponse(serializers.serialize("json", data), content_type="application/json")


def show_xml(request):
    """Mengembalikan seluruh barang aktif dalam format XML (Standar PBP Fasilkom UI)."""
    data = Barang.objects.filter(status_penawaran='aktif')
    return HttpResponse(serializers.serialize("xml", data), content_type="application/xml")


def show_xml_by_id(request, pk):
    """Mengembalikan data 1 barang spesifik berdasarkan ID dalam format XML."""
    data = Barang.objects.filter(pk=pk)
    return HttpResponse(serializers.serialize("xml", data), content_type="application/xml")


@csrf_exempt
@login_required
@require_POST
def tambah_barang_ajax(request):
    """
    Endpoint AJAX POST untuk penambahan barang asinkronus atau integrasi Flutter.
    """
    form = BarangForm(request.POST, request.FILES)
    if form.is_valid():
        barang = form.save(commit=False)
        barang.pemilik = request.user
        barang.save()

        return JsonResponse({
            'status': 'success',
            'message': f"Barang '{barang.nama_barang}' berhasil didaftarkan.",
            'barang_id': barang.pk,
            'nama_barang': barang.nama_barang,
            'tarif_per_hari': barang.tarif_per_hari,
            'jenis_penawaran': barang.jenis_penawaran,
        }, status=201)
    else:
        return JsonResponse({
            'status': 'error',
            'errors': form.errors,
        }, status=400)
