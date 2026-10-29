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
from django.conf import settings
from django.db.models import Q, F
from django.db import transaction
import urllib.parse
from .models import Barang, Kategori, Lokasi
from categories.models import Category
from .forms import BarangForm, BarangEditForm
from .services import save_item_with_pickup, visible_item_locations
from locations.services import pickup_context


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

    kategori_list = Category.objects.all()
    lokasi_list = visible_item_locations(request.user)

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
        form = BarangForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            barang = save_item_with_pickup(form, request.user)
            messages.success(
                request,
                f"Barang '{barang.nama_barang}' berhasil didaftarkan ke inventaris Barang Saya."
            )
            return redirect('barang:dashboard')
        else:
            messages.error(request, "Gagal mendaftarkan barang. Silakan periksa kesalahan berikut:")
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields and form.fields[field].label else field
                unique_errs = list(dict.fromkeys(errors))
                for err in unique_errs:
                    messages.error(request, f"• {field_label}: {err}" if field != '__all__' else f"• {err}")
    else:
        form = BarangForm(user=request.user)

    kategori_list = Category.objects.all()
    lokasi_list = visible_item_locations(request.user)

    context = {
        'form': form,
        'kategori_list': kategori_list,
        'lokasi_list': lokasi_list,
        **pickup_context(request.user),
    }
    return render(request, 'barang/tambah.html', context)


@login_required
@transaction.atomic
def edit_barang(request, pk):
    """
    FORM EDIT BARANG (Fauzan Taqiy Santosa)
    Edit barang yang sudah ada. Hanya pemilik sah yang dapat mengakses.
    Menyediakan pengaturan Status Penawaran (Aktif vs Nonaktifkan Sementara).
    """
    barang = get_object_or_404(Barang.objects.select_for_update(), pk=pk, pemilik=request.user)

    if barang.transaksi_terkunci:
        messages.error(request, "Barang terkunci karena memiliki pesanan yang sudah dikonfirmasi.")
        return redirect('barang:dashboard')

    if request.method == 'POST':
        form = BarangEditForm(request.POST, request.FILES, instance=barang, user=request.user)
        if form.is_valid():
            save_item_with_pickup(form, request.user)
            messages.success(
                request,
                f"Perubahan informasi barang '{barang.nama_barang}' berhasil disimpan."
            )
            return redirect('barang:dashboard')
        else:
            messages.error(request, "Gagal menyimpan perubahan barang. Silakan periksa kesalahan berikut:")
            for field, errors in form.errors.items():
                field_label = form.fields[field].label if field in form.fields and form.fields[field].label else field
                unique_errs = list(dict.fromkeys(errors))
                for err in unique_errs:
                    messages.error(request, f"• {field_label}: {err}" if field != '__all__' else f"• {err}")
    else:
        form = BarangEditForm(instance=barang, user=request.user)

    kategori_list = Category.objects.all()
    lokasi_list = visible_item_locations(request.user)

    context = {
        'form': form,
        'barang': barang,
        'kategori_list': kategori_list,
        'lokasi_list': lokasi_list,
        **pickup_context(request.user),
        'pickup_current_data': {
            'id': 'current',
            'label': form.current_pickup.nama_area,
            'address': form.current_pickup.full_address or form.current_pickup.patokan,
            'latitude': float(form.current_pickup.latitude) if form.current_pickup.latitude is not None else None,
            'longitude': float(form.current_pickup.longitude) if form.current_pickup.longitude is not None else None,
        },
    }
    return render(request, 'barang/edit.html', context)


@login_required
@require_POST
@transaction.atomic
def hapus_barang(request, pk):
    """
    PEMROSESAN HAPUS BARANG (Fauzan Taqiy Santosa)
    Backend view pemrosesan POST penghapusan barang:
    - Wajib POST dengan CSRF protection
    - Hanya pemilik sah
    - Memvalidasi Aturan Bisnis Rule #6: Barang yang sedang dipinjam TIDAK DAPAT dihapus.
    """
    barang = get_object_or_404(Barang.objects.select_for_update(), pk=pk, pemilik=request.user)

    if not barang.can_be_deleted():
        messages.error(
            request,
            f"Barang '{barang.nama_barang}' tidak dapat dihapus karena sudah memiliki draft atau riwayat pesanan."
        )
        return redirect('barang:dashboard')

    nama = barang.nama_barang
    barang.delete()
    messages.success(
        request,
        f"Barang '{nama}' telah berhasil dihapus dari inventaris Barang Saya."
    )
    return redirect('barang:dashboard')


@login_required
@require_POST
def hapus_barang_ajax(request, pk):
    """
    PEMROSESAN HAPUS BARANG VIA AJAX (Standar Tutorial 06 PBP - Fauzan Taqiy Santosa)
    Menghapus barang secara asinkronus tanpa me-refresh halaman:
    - Wajib login (@login_required) & hanya pemilik sah
    - Memvalidasi aturan bisnis: Barang yang sedang dipinjam aktif TIDAK DAPAT dihapus
    - Mengembalikan JsonResponse untuk manipulasi DOM sisi klien secara realtime
    """
    try:
        barang = Barang.objects.get(pk=pk, pemilik=request.user)
    except Barang.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Barang tidak ditemukan atau Anda tidak memiliki hak akses.'
        }, status=404)

    if not barang.can_be_deleted():
        return JsonResponse({
            'status': 'error',
            'message': f"Barang '{barang.nama_barang}' tidak dapat dihapus karena saat ini sedang dalam masa peminjaman aktif!"
        }, status=400)

    nama = barang.nama_barang
    barang.delete()

    total_barang = Barang.objects.filter(pemilik=request.user).count()
    barang_tersedia = Barang.objects.filter(pemilik=request.user, status_penawaran='aktif').count()

    return JsonResponse({
        'status': 'success',
        'message': f"Barang '{nama}' telah berhasil dihapus.",
        'deleted_id': pk,
        'total_barang': total_barang,
        'barang_tersedia': barang_tersedia,
    }, status=200)


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
    form = BarangForm(request.POST, request.FILES, user=request.user)
    if form.is_valid():
        barang = save_item_with_pickup(form, request.user)

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


def detail_barang(request, pk):
    """
    HALAMAN RINCIAN / DETAIL BARANG (Publik & Calon Peminjam)
    Menampilkan detail lengkap barang:
    - Foto produk asli ukuran penuh
    - Nama barang, kategori, jenis penawaran (sewa/gratis), tarif
    - Status ketersediaan (Tersedia / Sedang Dipinjam)
    - Deskripsi lengkap kondisi & aturan barang
    - Profil nama asli pemilik (nama lengkap dari Profile SSO UI)
    - Titik lokasi penjemputan interaktif pada peta Leaflet
    - Tombol aksi Pinjam Barang / Hubungi Pemilik via WhatsApp
    """
    barang = get_object_or_404(
        Barang.objects.select_related('kategori', 'lokasi', 'pemilik', 'pemilik__profile'),
        pk=pk
    )

    # Tambah counter dilihat jika bukan pemilik sendiri yang membuka halaman
    if not request.user.is_authenticated or request.user != barang.pemilik:
        Barang.objects.filter(pk=pk).update(dilihat_count=F('dilihat_count') + 1)
        barang.dilihat_count += 1

    is_owner = request.user.is_authenticated and request.user == barang.pemilik

    # Aturan Privasi & Keamanan:
    # Nomor WhatsApp pemilik HANYA boleh terbuka setelah peminjam membayar / pesanan terkonfirmasi.
    has_paid = False
    if request.user.is_authenticated and not is_owner:
        for rel_name in ['daftar_pesanan', 'pesanan_set', 'transaksi_set', 'transaksi']:
            manager = getattr(barang, rel_name, None)
            if manager is not None and hasattr(manager, 'filter'):
                if manager.filter(
                    peminjam=request.user,
                    status__in=['dikonfirmasi', 'selesai', 'dipinjam', 'aktif']
                ).exists():
                    has_paid = True
                    break

    # Format kontak WhatsApp pemilik jika berhak melihat (sudah membayar atau pemilik sendiri)
    profile = getattr(barang.pemilik, 'profile', None)
    phone = ''
    wa_link = ''
    if (has_paid or is_owner) and profile and profile.phone:
        raw_digits = ''.join(c for c in profile.phone if c.isdigit())
        if raw_digits.startswith('0'):
            phone = '62' + raw_digits[1:]
        elif raw_digits.startswith('62'):
            phone = raw_digits
        elif raw_digits:
            phone = '62' + raw_digits

        if phone:
            loc_label = barang.lokasi.short_label or barang.lokasi.nama_area
            wa_message = (
                f"Halo {barang.nama_pemilik_lengkap}, saya peminjam '{barang.nama_barang}' di Pinjemin UI. "
                f"Pembayaran peminjaman saya telah terkonfirmasi. Mari atur waktu dan penyerahan barang di {loc_label}."
            )
            wa_link = f"https://wa.me/{phone}?text={urllib.parse.quote(wa_message)}"

    can_view_pickup = is_owner or has_paid
    location = barang.lokasi
    pickup_detail_data = None
    if can_view_pickup and location.latitude is not None and location.longitude is not None:
        pickup_detail_data = {
            'label': location.nama_area,
            'latitude': float(location.latitude),
            'longitude': float(location.longitude),
            'tileUrl': settings.OSM_TILE_URL,
        }

    context = {
        'barang': barang,
        'profile': profile,
        'can_view_pickup': can_view_pickup,
        'pickup_detail_data': pickup_detail_data,
        'phone': phone,
        'wa_link': wa_link,
        'is_owner': is_owner,
        'has_paid': has_paid,
    }
    return render(request, 'barang/detail.html', context)
