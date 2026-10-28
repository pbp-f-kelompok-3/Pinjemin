"""Aturan pesanan. Semua perubahan reservasi mengunci Barang yang sama.

Gunakan PostgreSQL di deployment untuk serialisasi checkout secara concurrent.
SQLite lokal hanya untuk pengembangan; select_for_update tidak mengunci baris.
"""
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from barang.models import Barang
from . import gateway
from .models import Pesanan, Pembayaran


def _lock_order(pk):
    item_id = Pesanan.objects.values_list("barang_id", flat=True).get(pk=pk)
    Barang.objects.select_for_update().get(pk=item_id)
    return Pesanan.objects.select_for_update().select_related("barang__lokasi").get(pk=pk)


def _snapshot(order):
    item = order.barang
    order.pemilik_id = item.pemilik_id
    order.nama_barang = item.nama_barang
    loc = item.lokasi
    order.lokasi_snapshot = {"label": loc.short_label, "alamat": loc.nama_area,
                             "patokan": loc.patokan, "kota": loc.kecamatan_kota}


def _schedule(order, mulai, durasi, submitting=False):
    if order.peminjam_id == order.barang.pemilik_id:
        raise ValidationError("Kamu tidak dapat meminjam barang sendiri.")
    if order.barang.status_penawaran != "aktif" or not order.barang.pemilik.is_active:
        raise ValidationError("Barang ini sedang tidak tersedia.")
    if not 1 <= durasi <= 365:
        raise ValidationError("Durasi harus 1–365 hari.")
    now = timezone.now()
    paid = order.barang.jenis_penawaran == "sewa"
    minimum = now + timedelta(hours=24, minutes=30 if paid else 0)
    if order.status == Pesanan.Status.WAITING:
        minimum = order.batas_bayar + timedelta(hours=24)
    if mulai < minimum:
        raise ValidationError("Jadwal mulai minimal 24 jam 30 menit dari sekarang untuk sewa, atau 24 jam untuk barang gratis. Saat menunggu pembayaran, minimal 24 jam setelah batas bayar.")
    end = mulai + timedelta(days=durasi)
    if submitting or order.status == Pesanan.Status.WAITING:
        conflict = order.barang.daftar_pesanan.exclude(pk=order.pk).filter(
            mulai__lt=end, selesai__gt=mulai,
        ).filter(Q(status=Pesanan.Status.CONFIRMED) | Q(status=Pesanan.Status.WAITING, batas_bayar__gt=now))
        if conflict.exists():
            raise ValidationError("Barang sudah dipesan pada jadwal tersebut. Pilih waktu lain.")
    order.mulai, order.selesai, order.durasi = mulai, end, durasi
    # Tarif dibekukan saat pengajuan; perubahan jadwal tidak mengambil tarif baru.
    if order.status == Pesanan.Status.DRAFT:
        order.tarif_per_hari = order.barang.tarif_per_hari if paid else 0
    order.total = order.tarif_per_hari * durasi


@transaction.atomic
def create_draft(user, item_id, mulai, durasi):
    item = Barang.objects.select_for_update().select_related("lokasi", "pemilik").get(pk=item_id)
    order = Pesanan(peminjam=user, barang=item, pemilik_id=item.pemilik_id)
    _schedule(order, mulai, durasi)
    _snapshot(order)
    order.save()
    return order


@transaction.atomic
def delete_draft(pk, user):
    order = _lock_order(pk)
    if order.peminjam_id != user.pk or order.status != Pesanan.Status.DRAFT:
        raise ValidationError("Hanya draft milikmu yang dapat dihapus permanen.")
    order.delete()


@transaction.atomic
def submit_order(pk, user):
    order = _lock_order(pk)
    if order.peminjam_id != user.pk or order.status != Pesanan.Status.DRAFT:
        raise ValidationError("Pesanan ini bukan draft yang dapat diajukan.")
    _schedule(order, order.mulai, order.durasi, submitting=True)
    _snapshot(order)
    order.diajukan_at = timezone.now()
    if order.total:
        order.status = Pesanan.Status.WAITING
        order.batas_bayar = order.diajukan_at + timedelta(minutes=30)
        Pembayaran.objects.create(pesanan=order, jumlah=order.total)
    else:
        order.status = Pesanan.Status.CONFIRMED
    order.save()
    return order


@transaction.atomic
def edit_schedule(pk, user, mulai, durasi):
    order = _lock_order(pk)
    if order.peminjam_id != user.pk or not order.bisa_diubah:
        raise ValidationError("Jadwal hanya dapat diubah pada draft atau sebelum pembayaran selesai dan batas bayar berakhir.")
    # Verifikasi dulu bila pengguna sudah membuka Midtrans; jangan mengubah order yang telah dibayar.
    payment = order.pembayaran.filter(aktif=True).first()
    if payment and payment.gateway_started:
        data = gateway.status(payment)
        if data and data.get("transaction_status") in ["capture", "settlement", "refund", "partial_refund"]:
            raise ValidationError("Pembayaran sudah diproses. Periksa status pembayaran sebelum mengubah jadwal.")
    _schedule(order, mulai, durasi)
    if order.status == Pesanan.Status.DRAFT:
        _snapshot(order)
    elif payment:
        # Referensi baru membuat callback tagihan lama tidak mengonfirmasi jadwal baru.
        # Hasil pembayaran attempt lama akan direfund melalui rekonsiliasi.
        payment.aktif = False
        payment.save(update_fields=["aktif"])
        Pembayaran.objects.create(pesanan=order, jumlah=order.total)
    order.save()
    return order


@transaction.atomic
def cancel_order(pk, user):
    order = _lock_order(pk)
    if order.peminjam_id != user.pk or not order.bisa_dibatalkan:
        raise ValidationError("Pesanan hanya dapat dibatalkan sebelum peminjaman dimulai.")
    order.status = Pesanan.Status.CANCELLED
    order.alasan_pembatalan = "Dibatalkan peminjam"
    order.save()
    order.pembayaran.filter(dibayar_at__isnull=False, refund_status=Pembayaran.Refund.NONE).update(refund_status=Pembayaran.Refund.REQUIRED)
    return order


def payment_url(pk, user, finish_url):
    error = None
    with transaction.atomic():
        order = _lock_order(pk)
        if order.peminjam_id != user.pk or order.status != Pesanan.Status.WAITING or order.batas_bayar <= timezone.now():
            raise ValidationError("Pesanan tidak dapat dibayar atau batas waktunya telah berakhir.")
        payment = order.pembayaran.get(aktif=True)
        if payment.redirect_url:
            return payment.redirect_url
        # Bahkan pada timeout, simpan jejak request untuk rekonsiliasi berikutnya.
        payment.gateway_started = True
        payment.save(update_fields=["gateway_started"])
        try:
            data = gateway.create_session(payment, finish_url)
            payment.snap_token, payment.redirect_url = data["token"], data["redirect_url"]
            payment.save()
        except gateway.GatewayError as exc:
            error = exc
    if error:
        raise error
    return payment.redirect_url


def _paid_time(data):
    value = data.get("settlement_time")
    if value:
        try:
            return timezone.make_aware(datetime.strptime(value, "%Y-%m-%d %H:%M:%S"), timezone.get_default_timezone())
        except (ValueError, TypeError):
            pass
    return timezone.now()


@transaction.atomic
def apply_status(payment_id, data):
    payment = Pembayaran.objects.get(pk=payment_id)
    order = _lock_order(payment.pesanan_id)
    payment = Pembayaran.objects.select_for_update().get(pk=payment_id)
    if not gateway.valid_amount(data, payment):
        raise ValidationError("Referensi atau jumlah pembayaran tidak cocok.")
    state = data.get("transaction_status", "")
    if state not in ["pending", "capture", "settlement", "deny", "cancel", "expire", "refund", "partial_refund", "authorize", "failure"]:
        raise ValidationError("Status pembayaran tidak dikenal.")
    payment.transaction_id = data.get("transaction_id", payment.transaction_id)
    payment.metode = data.get("payment_type", payment.metode)
    success = state == "settlement" or (state == "capture" and data.get("fraud_status") == "accept")
    if state == "refund" and Decimal(str(data.get("refund_amount", 0))) >= payment.jumlah:
        payment.status = state
        payment.refund_status = Pembayaran.Refund.DONE
        if payment.aktif and order.status in [Pesanan.Status.WAITING, Pesanan.Status.CONFIRMED]:
            order.status = Pesanan.Status.CANCELLED
            order.alasan_pembatalan = "Pembayaran dikembalikan"
            order.save()
    elif success and payment.refund_status != Pembayaran.Refund.DONE:
        payment.status = state
        payment.dibayar_at = payment.dibayar_at or _paid_time(data)
        conflict = order.barang.daftar_pesanan.exclude(pk=order.pk).filter(
            mulai__lt=order.selesai, selesai__gt=order.mulai,
        ).filter(Q(status=Pesanan.Status.CONFIRMED) | Q(status=Pesanan.Status.WAITING, batas_bayar__gt=timezone.now())).exists()
        expired_locally = order.status == Pesanan.Status.CANCELLED and order.alasan_pembatalan == "Batas pembayaran 30 menit berakhir"
        valid = (payment.aktif and (order.status in [Pesanan.Status.WAITING, Pesanan.Status.CONFIRMED, Pesanan.Status.COMPLETED] or expired_locally)
                 and payment.dibayar_at <= order.batas_bayar
                 and payment.dibayar_at + timedelta(hours=24) <= order.mulai and not conflict)
        if valid and (order.status == Pesanan.Status.WAITING or expired_locally):
            order.status = Pesanan.Status.CONFIRMED
            order.alasan_pembatalan = ""
            _snapshot(order)
            order.save()
        elif not valid and payment.refund_status == Pembayaran.Refund.NONE:
            payment.refund_status = Pembayaran.Refund.REQUIRED
            if payment.aktif and order.status == Pesanan.Status.WAITING:
                order.status = Pesanan.Status.CANCELLED
                order.alasan_pembatalan = "Pembayaran terlambat atau reservasi tidak berlaku"
                order.save()
    elif not payment.dibayar_at:
        payment.status = state
        if payment.aktif and state in ["deny", "cancel", "expire", "failure"] and order.status == Pesanan.Status.WAITING:
            order.status = Pesanan.Status.CANCELLED
            order.alasan_pembatalan = "Pembayaran gagal, dibatalkan, atau kedaluwarsa"
            order.save()
    payment.save()


def reconcile(payment_id):
    """Selalu baca status API terbaru; payload webhook hanya pemicu, bukan sumber status."""
    payment = Pembayaran.objects.select_related("pesanan").get(pk=payment_id)
    if payment.gateway_started:
        data = gateway.status(payment)
        if data:
            apply_status(payment.pk, data)
    payment.refresh_from_db()
    # Batalkan attempt lama/pesanan batal yang sudah punya kode pembayaran pending.
    if payment.gateway_started and (not payment.aktif or payment.pesanan.status == Pesanan.Status.CANCELLED) and payment.status == "pending":
        gateway.request("POST", f"/{payment.gateway_order_id}/cancel")
        data = gateway.status(payment)
        if data:
            apply_status(payment.pk, data)
    refund_payment(payment.pk)


@transaction.atomic
def refund_payment(payment_id):
    payment = Pembayaran.objects.select_for_update().get(pk=payment_id)
    if payment.refund_status not in [Pembayaran.Refund.REQUIRED, Pembayaran.Refund.PROCESSING]:
        return
    if not settings_auto_refund():
        payment.refund_status = Pembayaran.Refund.MANUAL
        payment.catatan = "Refund otomatis dinonaktifkan; pengelola perlu menangani pengembalian."
        payment.save()
        return
    try:
        if payment.status == "capture":
            gateway.request("POST", f"/{payment.gateway_order_id}/cancel")
            data = gateway.status(payment)
            if data and data.get("transaction_status") == "cancel":
                payment.refund_status = Pembayaran.Refund.DONE
                payment.status = "cancel"
            else:
                raise gateway.GatewayError("Pembatalan pembayaran belum terkonfirmasi.")
        elif payment.status == "settlement" and payment.metode in ["credit_card", "gopay", "shopeepay", "dana", "ovo", "qris", "kredivo", "akulaku"]:
            data = gateway.request("POST", f"/{payment.gateway_order_id}/refund", {
                "refund_key": str(payment.refund_key), "amount": payment.jumlah,
                "reason": "Pembatalan pesanan atau pembayaran untuk tagihan tidak aktif",
            })
            payment.refund_status = Pembayaran.Refund.DONE if data.get("transaction_status") == "refund" else Pembayaran.Refund.PROCESSING
        else:
            raise gateway.GatewayError("Metode pembayaran memerlukan pengembalian manual.")
        payment.catatan = ""
    except gateway.GatewayError as exc:
        payment.refund_status = Pembayaran.Refund.REQUIRED if exc.retryable else Pembayaran.Refund.MANUAL
        payment.catatan = exc.diagnostic[:255]
    payment.save()


def settings_auto_refund():
    from django.conf import settings
    return settings.MIDTRANS_AUTO_REFUND


def maintain_orders():
    """Jalankan setiap menit lewat scheduler; halaman terkait juga menjalankannya."""
    now = timezone.now()
    expired = Pesanan.objects.filter(status=Pesanan.Status.WAITING, batas_bayar__lte=now)
    for pk in expired.values_list("pk", flat=True):
        with transaction.atomic():
            order = _lock_order(pk)
            if order.status == Pesanan.Status.WAITING and order.batas_bayar <= timezone.now():
                order.status = Pesanan.Status.CANCELLED
                order.alasan_pembatalan = "Batas pembayaran 30 menit berakhir"
                order.save()
    Pesanan.objects.filter(status=Pesanan.Status.CONFIRMED, selesai__lte=now).update(status=Pesanan.Status.COMPLETED)
