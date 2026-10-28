from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from transaksi import gateway, services
from transaksi.models import Pembayaran


class Command(BaseCommand):
    help = "Rekonsiliasi pembayaran, refund, kedaluwarsa, dan penyelesaian pesanan. Jadwalkan setiap menit."

    def handle(self, *args, **options):
        failures = 0
        payments = Pembayaran.objects.filter(gateway_started=True).exclude(
            status__in=["deny", "cancel", "expire", "failure", "refund"]
        ).exclude(refund_status__in=[Pembayaran.Refund.DONE, Pembayaran.Refund.SIMULATED])
        for pk in payments.values_list("pk", flat=True):
            try:
                services.reconcile(pk)
            except (gateway.GatewayError, ValidationError) as exc:
                failures += 1
                self.stderr.write(f"{pk}: {exc}")
        services.maintain_orders()
        self.stdout.write(f"Sinkronisasi selesai; {failures} pembayaran perlu diperiksa ulang.")
