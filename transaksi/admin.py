from django.contrib import admin
from .models import Pesanan, Pembayaran


@admin.register(Pesanan)
class PesananAdmin(admin.ModelAdmin):
    list_display = ["id", "nama_barang", "peminjam", "status", "mulai", "total"]
    list_filter = ["status"]
    readonly_fields = [field.name for field in Pesanan._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Pembayaran)
class PembayaranAdmin(admin.ModelAdmin):
    list_display = ["id", "pesanan", "jumlah", "status", "refund_status"]
    list_filter = ["refund_status", "status"]
    readonly_fields = [field.name for field in Pembayaran._meta.fields]
    actions = ["retry_refund", "manual_refund_done"]

    @admin.action(description="Coba ulang refund otomatis yang perlu penanganan manual")
    def retry_refund(self, request, queryset):
        from . import services
        for payment in queryset.filter(refund_status__in=[Pembayaran.Refund.MANUAL, Pembayaran.Refund.REQUIRED]):
            payment.refund_status = Pembayaran.Refund.REQUIRED
            payment.save(update_fields=["refund_status"])
            services.refund_payment(payment.pk)
        self.message_user(request, "Permintaan diproses. Periksa status refund pada daftar.")

    @admin.action(description="Tandai refund manual selesai (hanya setelah dana dikembalikan di luar aplikasi)")
    def manual_refund_done(self, request, queryset):
        count = queryset.filter(refund_status=Pembayaran.Refund.MANUAL).update(
            refund_status=Pembayaran.Refund.DONE,
            catatan=f"Pengembalian manual dikonfirmasi pengelola {request.user.pk}.",
        )
        self.message_user(request, f"{count} pengembalian manual ditandai selesai.")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
