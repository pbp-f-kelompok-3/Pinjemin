import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class Pesanan(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        WAITING = "menunggu_pembayaran", "Menunggu Pembayaran"
        CONFIRMED = "dikonfirmasi", "Dikonfirmasi"
        COMPLETED = "selesai", "Selesai"
        CANCELLED = "dibatalkan", "Dibatalkan"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    peminjam = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                 related_name="pesanan_peminjam")
    barang = models.ForeignKey("barang.Barang", on_delete=models.PROTECT,
                               related_name="daftar_pesanan")
    pemilik = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                related_name="pesanan_pemilik")
    mulai = models.DateTimeField()
    durasi = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(365)])
    selesai = models.DateTimeField()
    tarif_per_hari = models.PositiveBigIntegerField(default=0)
    total = models.PositiveBigIntegerField(default=0)
    nama_barang = models.CharField(max_length=200)
    lokasi_snapshot = models.JSONField(default=dict)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    diajukan_at = models.DateTimeField(null=True, blank=True)
    batas_bayar = models.DateTimeField(null=True, blank=True)
    alasan_pembatalan = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["barang", "status", "mulai", "selesai"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(durasi__gte=1, durasi__lte=365), name="pesanan_durasi_valid"),
            models.CheckConstraint(condition=models.Q(selesai__gt=models.F("mulai")), name="pesanan_waktu_valid"),
        ]

    @property
    def bisa_diubah(self):
        return self.status == self.Status.DRAFT or (
            self.status == self.Status.WAITING and self.batas_bayar > timezone.now())

    @property
    def bisa_dibatalkan(self):
        return self.status in [self.Status.WAITING, self.Status.CONFIRMED] and self.mulai > timezone.now()

    def __str__(self):
        return f"{self.nama_barang} — {self.get_status_display()}"


class Pembayaran(models.Model):
    class Refund(models.TextChoices):
        NONE = "none", "Tidak ada pengembalian dana"
        REQUIRED = "required", "Menunggu pengembalian dana"
        PROCESSING = "processing", "Pengembalian dana diproses"
        MANUAL = "manual", "Perlu pengembalian manual"
        DONE = "done", "Pengembalian dana disetujui penyedia"
        SIMULATED = "simulated", "Refund simulasi selesai"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pesanan = models.ForeignKey(Pesanan, on_delete=models.PROTECT, related_name="pembayaran")
    jumlah = models.PositiveBigIntegerField()
    status = models.CharField(max_length=30, default="created")
    aktif = models.BooleanField(default=True)
    snap_token = models.CharField(max_length=255, blank=True)
    redirect_url = models.URLField(max_length=1000, blank=True)
    gateway_started = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=100, blank=True)
    metode = models.CharField(max_length=50, blank=True)
    dibayar_at = models.DateTimeField(null=True, blank=True)
    refund_status = models.CharField(max_length=20, choices=Refund.choices, default=Refund.NONE)
    refund_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    catatan = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["pesanan"], condition=models.Q(aktif=True), name="satu_pembayaran_aktif")]

    @property
    def gateway_order_id(self):
        return f"pj-{self.id.hex}"

    @property
    def status_label(self):
        return {
            "created": "Belum memulai pembayaran", "pending": "Menunggu pembayaran",
            "capture": "Pembayaran diterima", "settlement": "Pembayaran berhasil",
            "cancel": "Pembayaran dibatalkan", "expire": "Pembayaran kedaluwarsa",
            "deny": "Pembayaran ditolak", "failure": "Pembayaran gagal",
            "authorize": "Menunggu penyelesaian pembayaran", "refund": "Pengembalian dana",
            "partial_refund": "Pengembalian sebagian dana",
        }.get(self.status, "Sedang diperiksa")
