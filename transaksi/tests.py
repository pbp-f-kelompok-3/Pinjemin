from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from barang.models import Barang, Lokasi
from categories.models import Category
from . import gateway, services
from .models import Pesanan, Pembayaran


@override_settings(REFUND_MODE="midtrans")
class TransaksiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="owner", password="test-password")
        self.user = User.objects.create_user(username="borrower", password="test-password")
        self.other = User.objects.create_user(username="stranger", password="test-password")
        self.category, _ = Category.objects.get_or_create(name="Elektronik")
        self.location = Lokasi.objects.create(nama_area="Kampus UI", patokan="Gerbang", short_label="UI",
                                             latitude="-6.362100", longitude="106.827900")
        self.item = Barang.objects.create(pemilik=self.owner, nama_barang="Proyektor", foto_utama="test.jpg",
                                         deskripsi="Tes", kategori=self.category, lokasi=self.location,
                                         jenis_penawaran="sewa", tarif_per_hari=25000)
        self.start = timezone.now() + timedelta(days=3)

    def draft(self, user=None):
        return services.create_draft(user or self.user, self.item.pk, self.start, 2)

    def order(self):
        return services.submit_order(self.draft().pk, self.user)

    def test_order_snapshots_pickup_coordinates_and_shows_route_map(self):
        order = self.order()
        self.assertEqual(order.lokasi_snapshot["latitude"], -6.3621)
        self.assertEqual(order.lokasi_snapshot["longitude"], 106.8279)

        self.client.force_login(self.user)
        response = self.client.get(reverse("transaksi:detail", args=[order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-order-map")
        self.assertContains(response, "Rute dari lokasiku")
        self.assertContains(response, "Buka rute di Google Maps")
        self.assertEqual(response.context["pickup_route_data"]["latitude"], -6.3621)
        self.assertEqual(response.context["pickup_route_data"]["longitude"], 106.8279)

    def test_pickup_snapshot_is_immutable_and_route_is_limited_to_order_parties(self):
        order = self.order()
        original_snapshot = order.lokasi_snapshot.copy()
        self.location.latitude = "-6.300000"
        self.location.longitude = "106.900000"
        self.location.save()
        order.refresh_from_db()
        self.assertEqual(order.lokasi_snapshot, original_snapshot)

        self.client.force_login(self.owner)
        owner_response = self.client.get(reverse("transaksi:detail", args=[order.pk]))
        self.assertEqual(owner_response.status_code, 200)
        self.assertContains(owner_response, "data-order-map")

        self.client.force_login(self.other)
        stranger_response = self.client.get(reverse("transaksi:detail", args=[order.pk]))
        self.assertEqual(stranger_response.status_code, 404)

    def status_data(self, payment, status="settlement", **kwargs):
        return {"order_id": payment.gateway_order_id, "gross_amount": str(payment.jumlah),
                "transaction_status": status, "transaction_id": "sandbox-transaction", "payment_type": "gopay",
                "settlement_time": timezone.localtime().strftime("%Y-%m-%d %H:%M:%S"), **kwargs}

    def test_draft_crud_really_deletes(self):
        draft = self.draft()
        self.assertEqual(draft.total, 50000)
        services.edit_schedule(draft.pk, self.user, self.start, 3)
        draft.refresh_from_db()
        self.assertEqual(draft.total, 75000)
        self.assertEqual(draft.pembayaran.count(), 0)
        services.delete_draft(draft.pk, self.user)
        self.assertFalse(Pesanan.objects.filter(pk=draft.pk).exists())

    def test_submit_holds_slot_and_timer_not_reset_by_edit(self):
        order = self.order()
        self.assertEqual(order.batas_bayar - order.diajukan_at, timedelta(minutes=30))
        with self.assertRaises(ValidationError):
            services.submit_order(self.draft(self.other).pk, self.other)
        old_payment = order.pembayaran.get()
        services.edit_schedule(order.pk, self.user, self.start, 3)
        order.refresh_from_db()
        self.assertEqual(order.batas_bayar - order.diajukan_at, timedelta(minutes=30))
        self.assertEqual(order.pembayaran.get(aktif=True).jumlah, 75000)
        old_payment.refresh_from_db()
        self.assertFalse(old_payment.aktif)

    def test_free_order_has_no_payment(self):
        self.item.jenis_penawaran = "gratis"
        self.item.save()
        order = self.order()
        self.assertEqual(order.total, 0)
        self.assertEqual(order.status, Pesanan.Status.CONFIRMED)
        self.assertFalse(order.pembayaran.exists())

    def test_cannot_book_own_item_or_less_than_lead_time(self):
        with self.assertRaises(ValidationError):
            services.create_draft(self.owner, self.item.pk, self.start, 2)
        with self.assertRaises(ValidationError):
            services.create_draft(self.user, self.item.pk, timezone.now() + timedelta(hours=24, minutes=10), 2)

    def test_verified_payment_confirms_and_duplicate_is_safe(self):
        order = self.order()
        payment = order.pembayaran.get()
        data = self.status_data(payment)
        services.apply_status(payment.pk, data)
        services.apply_status(payment.pk, data)
        order.refresh_from_db()
        self.assertEqual(order.status, Pesanan.Status.CONFIRMED)
        payment.refresh_from_db()
        self.assertEqual(payment.refund_status, Pembayaran.Refund.NONE)
        self.assertTrue(order.barang.transaksi_terkunci)
        self.assertFalse(order.barang.can_be_deleted())

    def test_wrong_amount_does_not_confirm(self):
        order = self.order()
        payment = order.pembayaran.get()
        with self.assertRaises(ValidationError):
            services.apply_status(payment.pk, self.status_data(payment, gross_amount="1"))
        order.refresh_from_db()
        self.assertEqual(order.status, Pesanan.Status.WAITING)

    def test_old_payment_and_cancelled_order_require_refund(self):
        order = self.order()
        payment = order.pembayaran.get()
        services.edit_schedule(order.pk, self.user, self.start, 3)
        services.apply_status(payment.pk, self.status_data(payment))
        payment.refresh_from_db()
        self.assertEqual(payment.refund_status, Pembayaran.Refund.REQUIRED)
        order.refresh_from_db()
        self.assertEqual(order.status, Pesanan.Status.WAITING)
        services.cancel_order(order.pk, self.user)
        current = order.pembayaran.get(aktif=True)
        services.apply_status(current.pk, self.status_data(current))
        current.refresh_from_db()
        self.assertEqual(current.refund_status, Pembayaran.Refund.REQUIRED)

    def test_expiry_releases_slot_and_late_success_does_not_confirm(self):
        order = self.order()
        Pesanan.objects.filter(pk=order.pk).update(batas_bayar=timezone.now() - timedelta(seconds=1))
        services.maintain_orders()
        order.refresh_from_db()
        self.assertEqual(order.status, Pesanan.Status.CANCELLED)
        payment = order.pembayaran.get()
        services.apply_status(payment.pk, self.status_data(payment))
        payment.refresh_from_db()
        self.assertEqual(payment.refund_status, Pembayaran.Refund.REQUIRED)
        self.assertEqual(services.submit_order(self.draft(self.other).pk, self.other).status, Pesanan.Status.WAITING)

    def test_non_draft_cannot_be_deleted(self):
        order = self.order()
        with self.assertRaises(ValidationError):
            services.delete_draft(order.pk, self.user)
        self.assertTrue(Pesanan.objects.filter(pk=order.pk).exists())

    def test_delayed_notification_honors_on_time_settlement_if_slot_free(self):
        order = self.order()
        payment = order.pembayaran.get()
        paid_time = order.batas_bayar - timedelta(minutes=1)
        with patch("transaksi.services.timezone.now", return_value=order.batas_bayar + timedelta(minutes=1)):
            services.maintain_orders()
            services.apply_status(payment.pk, self.status_data(payment,
                settlement_time=timezone.localtime(paid_time).strftime("%Y-%m-%d %H:%M:%S")))
        order.refresh_from_db()
        self.assertEqual(order.status, Pesanan.Status.CONFIRMED)

    def test_cancel_after_start_rejected_and_completion_needs_return_confirmation(self):
        order = self.order()
        payment = order.pembayaran.get()
        services.apply_status(payment.pk, self.status_data(payment))
        with patch("transaksi.services.timezone.now", return_value=order.mulai + timedelta(minutes=1)):
            with self.assertRaises(ValidationError):
                services.cancel_order(order.pk, self.user)
        with patch("transaksi.services.timezone.now", return_value=order.selesai + timedelta(minutes=1)):
            services.maintain_orders()
        order.refresh_from_db()
        self.assertEqual(order.status, Pesanan.Status.CONFIRMED)
        services.receive_order(order.pk, self.user)
        services.complete_order(order.pk, self.owner)
        order.refresh_from_db()
        self.assertEqual(order.status, Pesanan.Status.COMPLETED)

    def test_receipt_credits_owner_once_and_blocks_cancellation(self):
        order = self.order()
        payment = order.pembayaran.get()
        services.apply_status(payment.pk, self.status_data(payment))
        self.assertFalse(services.earned_orders(self.owner).exists())
        services.receive_order(order.pk, self.user)
        order.refresh_from_db()
        received = order.diterima_at
        services.receive_order(order.pk, self.user)
        order.refresh_from_db()
        self.assertEqual(order.diterima_at, received)
        self.assertEqual(services.earned_orders(self.owner).count(), 1)
        self.assertEqual(services.earned_orders(self.owner).get().total, 50000)
        self.assertFalse(services.earned_orders(self.other).exists())
        with self.assertRaises(ValidationError):
            services.cancel_order(order.pk, self.user)
        services.complete_order(order.pk, self.owner)
        self.assertEqual(services.earned_orders(self.owner).count(), 1)

    def test_receipt_requires_borrower_and_verified_payment(self):
        order = self.order()
        for user in [self.user, self.owner, self.other]:
            with self.assertRaises(ValidationError):
                services.receive_order(order.pk, user)
        services.apply_status(order.pembayaran.get().pk, self.status_data(order.pembayaran.get()))
        with self.assertRaises(ValidationError):
            services.receive_order(order.pk, self.owner)
        with self.assertRaises(ValidationError):
            services.complete_order(order.pk, self.owner)

    def test_owner_dashboard_payment_stages_and_income_privacy(self):
        order = self.order()
        self.client.force_login(self.owner)
        response = self.client.get(reverse("transaksi:masuk"))
        self.assertContains(response, "Menunggu peminjam membayar")
        services.apply_status(order.pembayaran.get().pk, self.status_data(order.pembayaran.get()))
        response = self.client.get(reverse("transaksi:masuk"))
        self.assertContains(response, "Siap diserahkan")
        income = self.client.get(reverse("transaksi:pendapatan"))
        self.assertEqual(income.context["held_income"], 50000)
        self.assertEqual(income.context["total_income"], 0)
        self.assertEqual(self.client.post(reverse("transaksi:terima", args=[order.pk])).status_code, 404)
        services.receive_order(order.pk, self.user)
        income = self.client.get(reverse("transaksi:pendapatan"))
        self.assertEqual(income.context["total_income"], 50000)
        self.assertEqual(income.context["held_income"], 0)
        self.assertContains(income, "Tidak ada transfer")
        self.client.force_login(self.other)
        income = self.client.get(reverse("transaksi:pendapatan"))
        self.assertEqual(income.context["total_income"], 0)
        self.assertNotContains(income, order.nama_barang)

    def test_free_receipt_and_refund_do_not_create_income(self):
        self.item.jenis_penawaran = "gratis"
        self.item.save()
        order = self.order()
        services.receive_order(order.pk, self.user)
        self.assertFalse(services.earned_orders(self.owner).exists())

    def test_provider_refund_removes_income(self):
        order = self.order()
        payment = order.pembayaran.get()
        services.apply_status(payment.pk, self.status_data(payment))
        services.receive_order(order.pk, self.user)
        self.assertTrue(services.earned_orders(self.owner).exists())
        services.apply_status(payment.pk, self.status_data(payment, "refund", refund_amount="50000"))
        self.assertFalse(services.earned_orders(self.owner).exists())

    def test_receipt_endpoint_requires_post_and_csrf(self):
        from django.test import Client
        order = self.order()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("transaksi:terima", args=[order.pk])).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(reverse("transaksi:terima", args=[order.pk])).status_code, 403)

    @override_settings(REFUND_MODE="mock")
    @patch("transaksi.gateway.requests.request")
    def test_demo_fixtures_are_local_repeatable_and_cover_owner_stages(self, api):
        import io
        import tempfile
        from django.core.management import call_command
        output = io.StringIO()
        # Use the platform temp directory: CI checkouts do not contain .test-tmp.
        with tempfile.TemporaryDirectory(prefix="pinjemin-test-media-") as media:
            with override_settings(MEDIA_ROOT=media, PRODUCTION=False):
                call_command("seed_demo_transaksi", password="demo-test-password", stdout=output)
                call_command("seed_demo_transaksi", password="do-not-reset-password", stdout=output)
        owner = get_user_model().objects.get(username="demo_transaksi_pemilik")
        borrower = get_user_model().objects.get(username="demo_transaksi_peminjam")
        self.assertTrue(owner.check_password("demo-test-password"))
        self.assertFalse(owner.is_superuser)
        self.assertFalse(owner.is_staff)
        self.assertFalse(borrower.is_staff)
        self.assertEqual(Pesanan.objects.filter(pemilik=owner).count(), 5)
        self.assertEqual(services.earned_orders(owner).count(), 2)
        self.assertFalse(api.called)
        self.client.force_login(owner)
        response = self.client.get(reverse("transaksi:masuk"))
        self.assertContains(response, "[Demo] Proyektor", count=5)
        self.assertEqual(response.context["summary"], {"waiting": 1, "ready": 1, "borrowed": 1})
        self.assertEqual(self.client.get(reverse("transaksi:pendapatan")).context["total_income"], 100000)

    @patch("transaksi.gateway.request")
    def test_refund_uses_same_key_and_manual_fallback(self, api):
        order = self.order()
        payment = order.pembayaran.get()
        services.apply_status(payment.pk, self.status_data(payment))
        services.cancel_order(order.pk, self.user)
        api.return_value = {"transaction_status": "refund"}
        services.refund_payment(payment.pk)
        services.refund_payment(payment.pk)
        self.assertEqual(api.call_count, 1)
        self.assertEqual(api.call_args.args[2]["refund_key"], str(payment.refund_key))
        payment.refresh_from_db()
        self.assertEqual(payment.refund_status, Pembayaran.Refund.DONE)

    @patch("transaksi.gateway.request", side_effect=gateway.GatewayError("Perlu aktivasi refund"))
    def test_refund_failure_visible_to_operator(self, api):
        order = self.order()
        payment = order.pembayaran.get()
        services.apply_status(payment.pk, self.status_data(payment))
        services.cancel_order(order.pk, self.user)
        services.refund_payment(payment.pk)
        payment.refresh_from_db()
        self.assertEqual(payment.refund_status, Pembayaran.Refund.MANUAL)

    @patch("transaksi.gateway.request")
    def test_insufficient_balance_waits_and_retries_with_same_key(self, api):
        order = self.order()
        payment = order.pembayaran.get()
        services.apply_status(payment.pk, self.status_data(payment))
        services.cancel_order(order.pk, self.user)
        api.side_effect = gateway.GatewayError("Saldo belum cukup", retryable=True)
        services.refund_payment(payment.pk)
        payment.refresh_from_db()
        self.assertEqual(payment.refund_status, Pembayaran.Refund.REQUIRED)
        api.side_effect = None
        api.return_value = {"transaction_status": "refund"}
        services.refund_payment(payment.pk)
        self.assertEqual(api.call_count, 2)
        keys = [call.args[2]["refund_key"] for call in api.call_args_list]
        self.assertEqual(keys, [str(payment.refund_key)] * 2)
        payment.refresh_from_db()
        self.assertEqual(payment.refund_status, Pembayaran.Refund.DONE)

    @override_settings(REFUND_MODE="mock")
    @patch("transaksi.gateway.request")
    def test_mock_refund_is_local_idempotent_and_not_provider_refund(self, api):
        order = self.order()
        payment = order.pembayaran.get()
        services.apply_status(payment.pk, self.status_data(payment))
        services.cancel_order(order.pk, self.user)
        services.refund_payment(payment.pk)
        payment.refresh_from_db()
        original_note = payment.catatan
        services.refund_payment(payment.pk)
        services.apply_status(payment.pk, self.status_data(payment))
        payment.refresh_from_db()
        order.refresh_from_db()
        self.assertFalse(api.called)
        self.assertEqual(payment.refund_status, Pembayaran.Refund.SIMULATED)
        self.assertEqual(payment.status, "settlement")
        self.assertEqual(payment.catatan, original_note)
        self.assertEqual(order.status, Pesanan.Status.CANCELLED)
        self.client.force_login(self.user)
        response = self.client.get(reverse("transaksi:detail", args=[order.pk]))
        self.assertContains(response, "Refund simulasi selesai")
        self.assertContains(response, "Tidak ada pengembalian dana melalui Midtrans")

    @override_settings(REFUND_MODE="mock")
    @patch("transaksi.gateway.request")
    def test_mock_refund_recovers_old_manual_but_requires_verified_payment(self, api):
        order = self.order()
        payment = order.pembayaran.get()
        services.cancel_order(order.pk, self.user)
        Pembayaran.objects.filter(pk=payment.pk).update(refund_status=Pembayaran.Refund.MANUAL)
        services.refund_payment(payment.pk)
        payment.refresh_from_db()
        self.assertEqual(payment.refund_status, Pembayaran.Refund.MANUAL)
        services.apply_status(payment.pk, self.status_data(payment))
        services.refund_payment(payment.pk)
        payment.refresh_from_db()
        self.assertEqual(payment.refund_status, Pembayaran.Refund.SIMULATED)
        self.assertFalse(api.called)

    @override_settings(REFUND_MODE="mock")
    @patch("transaksi.gateway.status")
    @patch("transaksi.gateway.request")
    def test_cancellation_view_automatically_simulates_full_refund(self, api, status):
        order = self.order()
        payment = order.pembayaran.get()
        payment.gateway_started = True
        payment.save()
        status.return_value = self.status_data(payment)
        services.apply_status(payment.pk, status.return_value)
        self.client.force_login(self.user)
        response = self.client.post(reverse("transaksi:batalkan", args=[order.pk]))
        self.assertEqual(response.status_code, 302)
        payment.refresh_from_db()
        self.assertEqual(payment.refund_status, Pembayaran.Refund.SIMULATED)
        self.assertFalse(api.called)

    def test_permissions_csrf_and_pages(self):
        draft = self.draft()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("transaksi:detail", args=[draft.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("transaksi:hapus", args=[draft.pk])).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("transaksi:detail", args=[draft.pk])).status_code, 404)
        self.client.force_login(self.user)
        for name in ["detail", "edit", "hapus", "batalkan"]:
            self.assertEqual(self.client.get(reverse(f"transaksi:{name}", args=[draft.pk])).status_code, 200)
        for name in ["daftar", "masuk", "katalog"]:
            self.assertEqual(self.client.get(reverse(f"transaksi:{name}")).status_code, 200)
        from django.test import Client
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(reverse("transaksi:hapus", args=[draft.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("transaksi:ajukan", args=[draft.pk])).status_code, 405)

    @override_settings(MIDTRANS_SERVER_KEY="test-server-key")
    @patch("transaksi.gateway.status")
    def test_webhook_verifies_signature_and_fetches_status(self, status):
        import hashlib
        order = self.order()
        payment = order.pembayaran.get()
        payment.gateway_started = True
        payment.save()
        data = self.status_data(payment, status_code="200")
        endpoint = reverse("transaksi:webhook")
        data["signature_key"] = "forged"
        self.assertEqual(self.client.post(endpoint, data, content_type="application/json").status_code, 403)
        self.assertFalse(status.called)
        data["signature_key"] = hashlib.sha512((data["order_id"] + "200" + data["gross_amount"] + "test-server-key").encode()).hexdigest()
        status.return_value = self.status_data(payment)
        self.assertEqual(self.client.post(endpoint, data, content_type="application/json").status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Pesanan.Status.CONFIRMED)

    @patch("transaksi.gateway.create_session", side_effect=gateway.GatewayError("Timeout"))
    def test_timeout_retains_payment_reference(self, create):
        order = self.order()
        with self.assertRaises(gateway.GatewayError):
            services.payment_url(order.pk, self.user, "https://example.com/finish")
        self.assertTrue(order.pembayaran.get().gateway_started)


@override_settings(MIDTRANS_SERVER_KEY="test-server-key")
class GatewayDiagnosticsTests(TestCase):
    @patch("transaksi.gateway.requests.request")
    def test_only_insufficient_funds_414_is_retryable(self, api):
        api.return_value.status_code = 200
        api.return_value.ok = True
        for message, retryable in [("Sorry, your refund request was declined due to merchant insufficient funds.", True),
                                   ("Refund request is rejected due to invalid amount", False)]:
            api.return_value.json.return_value = {"status_code": "414", "status_message": message}
            with self.assertRaises(gateway.GatewayError) as caught:
                gateway.request("POST", "/demo/refund")
            self.assertEqual(caught.exception.retryable, retryable)

    @patch("transaksi.gateway.requests.request")
    def test_provider_error_kept_for_operator_and_key_redacted(self, api):
        import base64
        api.return_value.status_code = 412
        api.return_value.ok = False
        encoded = base64.b64encode(b"test-server-key:").decode()
        api.return_value.json.return_value = {
            "status_code": "412", "status_message": "Refund not enabled",
            "error_messages": ["test-server-key", encoded],
        }
        with self.assertRaises(gateway.GatewayError) as caught:
            gateway.request("POST", "/demo/refund")
        error = caught.exception
        self.assertIn("kode 412", error.diagnostic)
        self.assertIn("Refund not enabled", error.diagnostic)
        self.assertNotIn("test-server-key", error.diagnostic)
        self.assertNotIn(encoded, error.diagnostic)
        self.assertNotIn("Refund not enabled", str(error))

    @patch("transaksi.gateway.requests.request")
    def test_non_object_response_is_controlled_error(self, api):
        api.return_value.json.return_value = []
        with self.assertRaises(gateway.GatewayError):
            gateway.request("GET", "/demo/status")
