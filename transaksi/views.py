import json
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from barang.models import Barang
from . import gateway, services
from .forms import JadwalForm
from .models import Pesanan, Pembayaran


def _error(request, exc):
    messages.error(request, " ".join(exc.messages) if isinstance(exc, ValidationError) else str(exc))


def _borrower_order(user, pk):
    return get_object_or_404(Pesanan, pk=pk, peminjam=user)


@login_required
def daftar(request):
    services.maintain_orders()
    orders = Pesanan.objects.filter(peminjam=request.user).select_related("barang")
    status = request.GET.get("status", "")
    if status in Pesanan.Status.values:
        orders = orders.filter(status=status)
    return render(request, "transaksi/daftar.html", {"orders": orders, "statuses": Pesanan.Status.choices,
                  "selected_status": status, "incoming": False})


@login_required
def masuk(request):
    services.maintain_orders()
    orders = Pesanan.objects.filter(pemilik=request.user).exclude(status=Pesanan.Status.DRAFT).select_related("peminjam")
    return render(request, "transaksi/daftar.html", {"orders": orders, "incoming": True})


@login_required
def katalog(request):
    items = Barang.objects.filter(status_penawaran="aktif", pemilik__is_active=True).exclude(pemilik=request.user)
    return render(request, "transaksi/katalog.html", {"items": items})


@login_required
def buat(request, item_id):
    item = get_object_or_404(Barang, pk=item_id, status_penawaran="aktif")
    if item.pemilik_id == request.user.pk:
        messages.warning(request, "Kamu tidak dapat meminjam barang inventaris milikmu sendiri.")
        return redirect("barang:detail", pk=item.pk)
    form = JadwalForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            order = services.create_draft(request.user, item.pk, **form.cleaned_data)
            messages.success(request, "Draft disimpan. Ajukan pesanan setelah memeriksa jadwal dan biaya.")
            return redirect("transaksi:detail", pk=order.pk)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "transaksi/form.html", {"form": form, "item": item})


@login_required
def detail(request, pk):
    services.maintain_orders()
    order = get_object_or_404(Pesanan.objects.select_related("barang", "pemilik", "peminjam").filter(
        Q(peminjam=request.user) | Q(pemilik=request.user)), pk=pk)
    if order.status == Pesanan.Status.DRAFT and order.peminjam_id != request.user.pk:
        return HttpResponse(status=404)
    phone = ""
    if order.status != Pesanan.Status.DRAFT:
        profile = getattr(order.pemilik, "profile", None)
        phone = "".join(c for c in (profile.phone if profile else "") if c.isdigit())
        if phone.startswith("0"):
            phone = "62" + phone[1:]
    return render(request, "transaksi/detail.html", {"order": order, "payments": order.pembayaran.all(),
                  "borrower": order.peminjam_id == request.user.pk, "phone": phone,
                  "mock_refund": settings.REFUND_MODE == "mock"})


@login_required
def edit(request, pk):
    services.maintain_orders()
    order = _borrower_order(request.user, pk)
    if not order.bisa_diubah:
        messages.error(request, "Pesanan ini tidak dapat diubah.")
        return redirect("transaksi:detail", pk=pk)
    form = JadwalForm(request.POST if request.method == "POST" else None, instance=order)
    if request.method == "POST" and form.is_valid():
        try:
            services.edit_schedule(pk, request.user, **form.cleaned_data)
            # Attempt lama direkonsiliasi tanpa menggagalkan perubahan yang telah disimpan.
            for payment in order.pembayaran.filter(aktif=False, gateway_started=True):
                try:
                    services.reconcile(payment.pk)
                except (gateway.GatewayError, ValidationError):
                    messages.warning(request, "Tagihan lama sedang diperiksa. Gunakan hanya tombol Bayar pada rincian terbaru.")
            messages.success(request, "Jadwal dan total diperbarui. Batas pembayaran tidak direset.")
            return redirect("transaksi:detail", pk=pk)
        except (ValidationError, gateway.GatewayError) as exc:
            form.add_error(None, str(exc) if isinstance(exc, gateway.GatewayError) else exc)
    return render(request, "transaksi/form.html", {"form": form, "item": order.barang, "order": order})


@login_required
def hapus(request, pk):
    order = _borrower_order(request.user, pk)
    if request.method == "POST":
        try:
            services.delete_draft(pk, request.user)
            messages.success(request, "Draft dihapus permanen dari database.")
            return redirect("transaksi:daftar")
        except ValidationError as exc:
            _error(request, exc)
            return redirect("transaksi:detail", pk=pk)
    return render(request, "transaksi/konfirmasi.html", {"order": order, "delete": True})


@login_required
@require_POST
def ajukan(request, pk):
    _borrower_order(request.user, pk)
    services.maintain_orders()
    try:
        services.submit_order(pk, request.user)
        messages.success(request, "Pesanan diajukan. Untuk barang sewa, selesaikan pembayaran dalam 30 menit.")
    except ValidationError as exc:
        _error(request, exc)
    return redirect("transaksi:detail", pk=pk)


@login_required
def batalkan(request, pk):
    order = _borrower_order(request.user, pk)
    if request.method == "POST":
        try:
            services.cancel_order(pk, request.user)
            messages.success(request, "Pesanan dibatalkan. Pembayaran yang sudah berhasil akan diperiksa untuk pengembalian dana.")
            for payment in order.pembayaran.all():
                services.reconcile(payment.pk)
        except (ValidationError, gateway.GatewayError) as exc:
            _error(request, exc)
        return redirect("transaksi:detail", pk=pk)
    return render(request, "transaksi/konfirmasi.html", {"order": order,
                  "mock_refund": settings.REFUND_MODE == "mock"})


@login_required
@require_POST
def bayar(request, pk):
    _borrower_order(request.user, pk)
    try:
        url = services.payment_url(pk, request.user, request.build_absolute_uri(reverse("transaksi:detail", args=[pk])))
        return redirect(url)
    except (ValidationError, gateway.GatewayError) as exc:
        _error(request, exc)
        return redirect("transaksi:detail", pk=pk)


@login_required
@require_POST
def periksa(request, pk):
    order = _borrower_order(request.user, pk)
    try:
        for payment in order.pembayaran.all():
            services.reconcile(payment.pk)
        services.maintain_orders()
        messages.success(request, "Status pembayaran sudah diperiksa.")
    except (gateway.GatewayError, ValidationError) as exc:
        _error(request, exc)
    return redirect("transaksi:detail", pk=pk)


@csrf_exempt
@require_POST
def webhook(request):
    # Endpoint mesin saja; form pengguna tetap memerlukan CSRF.
    if len(request.body) > 64000:
        return HttpResponse(status=413)
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict) or not gateway.valid_signature(data):
            return HttpResponse(status=403)
        reference = data.get("order_id", "")
        if not reference.startswith("pj-"):
            return HttpResponse(status=400)
        payment = get_object_or_404(Pembayaran, pk=uuid.UUID(reference[3:]))
        if not gateway.valid_amount(data, payment):
            return HttpResponse(status=400)
        services.reconcile(payment.pk)
    except (ValueError, TypeError, ValidationError):
        return HttpResponse(status=400)
    except gateway.GatewayError:
        return HttpResponse(status=503)  # Midtrans boleh mencoba ulang.
    return JsonResponse({"received": True})
