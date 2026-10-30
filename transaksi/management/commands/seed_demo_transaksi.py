"""Data uji lokal dengan dua akun dan beberapa tahap pesanan. Tanpa API Midtrans."""
import base64
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from barang.models import Barang, Lokasi
from categories.models import Category
from transaksi import services
from transaksi.models import Pesanan, Pembayaran


class Command(BaseCommand):
    help = "Buat data demo lokal pemilik/peminjam; pembayaran dan pendapatan sepenuhnya simulasi."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Password untuk akun demo yang baru dibuat.")
        parser.add_argument("--owner", help="Username akun pemilik yang sudah ada; tidak mengubah akses atau password akun tersebut.")

    @transaction.atomic
    def handle(self, *args, **options):
        if settings.PRODUCTION:
            raise CommandError("Data demo hanya boleh dibuat pada lingkungan lokal (PRODUCTION=False).")
        if settings.REFUND_MODE != "mock":
            raise CommandError("Gunakan REFUND_MODE=mock untuk data demo ini.")
        password = options["password"] or secrets.token_urlsafe(12)
        users = []
        for username, name in [("demo_transaksi_pemilik", "Pemilik Demo"),
                               ("demo_transaksi_peminjam", "Peminjam Demo")]:
            if username == "demo_transaksi_pemilik" and options["owner"]:
                try:
                    user = get_user_model().objects.get(username=options["owner"], is_active=True)
                except get_user_model().DoesNotExist:
                    raise CommandError("Username pemilik tidak ditemukan atau akunnya tidak aktif.")
                users.append(user)
                continue
            user, created = get_user_model().objects.get_or_create(
                username=username, defaults={"first_name": name})
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(f"Akun baru: {username} | password: {password}")
            else:
                self.stdout.write(f"Akun sudah ada: {username}; password tidak diubah.")
            users.append(user)
        owner, borrower = users
        category, _ = Category.objects.get_or_create(name="Demo Transaksi")
        location, _ = Lokasi.objects.get_or_create(
            nama_area="Titik Temu Demo Transaksi", defaults={"patokan": "Gerbang kampus", "short_label": "Demo UI"})
        stages = [("Menunggu pembayaran", "waiting"), ("Sudah dibayar", "paid"),
                  ("Sudah diterima", "received"), ("Dikembalikan", "completed"), ("Dibatalkan", "cancelled")]
        for title, stage in stages:
            item, created = Barang.objects.get_or_create(
                pemilik=owner, nama_barang=f"[Demo] Proyektor — {title}", defaults={
                    "deskripsi": "Data uji lokal. Pembayaran dan pendapatan contoh bukan transaksi Midtrans.",
                    "kategori": category, "lokasi": location, "jenis_penawaran": "sewa", "tarif_per_hari": 25000,
                    "foto_utama": "demo-transaksi.png",
                })
            if not item.foto_utama.storage.exists(item.foto_utama.name):
                pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aS1cAAAAASUVORK5CYII=")
                item.foto_utama.save("demo-transaksi.png", ContentFile(pixel), save=True)
            if item.daftar_pesanan.exists():
                self.stdout.write(f"Dipertahankan: {title}")
                continue
            order = services.create_draft(borrower, item.pk, timezone.now() + timedelta(days=3), 2)
            services.submit_order(order.pk, borrower)
            payment = order.pembayaran.get(aktif=True)
            if stage != "waiting":
                services.apply_status(payment.pk, {
                    "order_id": payment.gateway_order_id, "gross_amount": str(payment.jumlah),
                    "transaction_status": "settlement", "payment_type": "demo",
                    "transaction_id": f"demo-{payment.id.hex}",
                    "settlement_time": timezone.localtime().strftime("%Y-%m-%d %H:%M:%S"),
                })
                Pembayaran.objects.filter(pk=payment.pk).update(catatan="Pembayaran contoh lokal; tidak pernah dikirim ke Midtrans.")
            if stage in ["received", "completed"]:
                services.receive_order(order.pk, borrower)
            if stage == "completed":
                services.complete_order(order.pk, owner)
            if stage == "cancelled":
                services.cancel_order(order.pk, borrower)
                services.refund_payment(payment.pk)
            self.stdout.write(f"Dibuat: {title}")
        self.stdout.write(self.style.SUCCESS("Demo siap. Buka /transaksi/masuk/ atau /transaksi/pendapatan/ dengan akun pemilik yang terkait. Akun demo tidak memiliki akses staff/admin. Gunakan --owner USERNAME untuk menaruh data pada akun login yang sudah ada."))
