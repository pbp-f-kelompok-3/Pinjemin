"""Midtrans Snap Sandbox. Kunci server hanya dibaca di backend."""
import hashlib
import hmac
import base64
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.utils import timezone


class GatewayError(Exception):
    def __init__(self, message, diagnostic=None, retryable=False):
        super().__init__(message)
        # Detail penyedia hanya untuk catatan pengelola, bukan pesan ke peminjam.
        self.diagnostic = diagnostic or message
        self.retryable = retryable


def _error_detail(response, data, key):
    code = str(data.get("status_code", response.status_code))
    messages = data.get("error_messages")
    if not isinstance(messages, list):
        messages = []
    parts = [data.get("status_message", ""), *messages]
    detail = " ".join(part for part in parts if isinstance(part, str))
    # Jangan menyimpan key atau header autentikasi meskipun dikembalikan penyedia.
    for secret in [key, base64.b64encode((key + ":").encode()).decode()]:
        if secret:
            detail = detail.replace(secret, "[disembunyikan]")
    code = re.sub(r"[^0-9]", "", code)[:3] or "unknown"
    detail = " ".join(detail.split())[:190]
    return f"Midtrans HTTP {response.status_code}, kode {code}: {detail or 'Tidak ada rincian dari penyedia.'}"


def request(method, path, payload=None, snap=False, missing_ok=False):
    key = settings.MIDTRANS_SERVER_KEY
    if not key:
        raise GatewayError("Midtrans Sandbox belum dikonfigurasi. Pesanan tetap tersimpan.")
    base = "https://app.sandbox.midtrans.com/snap/v1" if snap else "https://api.sandbox.midtrans.com/v2"
    try:
        response = requests.request(method, base + path, json=payload,
                                    auth=(key, ""), timeout=(5, 15),
                                    headers={"Accept": "application/json"})
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise GatewayError("Midtrans belum merespons. Coba periksa status kembali.") from exc
    if not isinstance(data, dict):
        raise GatewayError("Respons Midtrans tidak valid. Coba periksa status kembali.")
    if missing_ok and (response.status_code == 404 or str(data.get("status_code")) == "404"):
        return None
    if not response.ok or str(data.get("status_code", "200")) not in ["200", "201", "202"]:
        insufficient_funds = (str(data.get("status_code")) == "414"
                              and "insufficient funds" in str(data.get("status_message", "")).lower())
        raise GatewayError("Permintaan Midtrans belum berhasil. Periksa status atau hubungi pengelola.",
                           diagnostic=_error_detail(response, data, key), retryable=insufficient_funds)
    return data


def create_session(payment, finish_url):
    order = payment.pesanan
    data = request("POST", "/transactions", {
        "transaction_details": {"order_id": payment.gateway_order_id, "gross_amount": payment.jumlah},
        "item_details": [{"id": str(order.barang_id), "name": order.nama_barang[:50],
                          "price": order.tarif_per_hari, "quantity": order.durasi}],
        "callbacks": {"finish": finish_url},
        # Start tetap saat place order, bukan saat halaman pembayaran dibuka.
        "expiry": {"start_time": timezone.localtime(order.diajukan_at).strftime("%Y-%m-%d %H:%M:%S %z"),
                   "unit": "minutes", "duration": 30},
    }, snap=True)
    url = data.get("redirect_url", "")
    if urlparse(url).scheme != "https" or urlparse(url).hostname != "app.sandbox.midtrans.com" or not data.get("token"):
        raise GatewayError("Respons halaman pembayaran tidak valid.")
    return data


def status(payment):
    return request("GET", f"/{payment.gateway_order_id}/status", missing_ok=True)


def valid_signature(data):
    fields = [data.get(k) for k in ["order_id", "status_code", "gross_amount", "signature_key"]]
    if not settings.MIDTRANS_SERVER_KEY or not all(isinstance(v, str) for v in fields):
        return False
    digest = hashlib.sha512(("".join(fields[:3]) + settings.MIDTRANS_SERVER_KEY).encode()).hexdigest()
    return hmac.compare_digest(digest, fields[3])


def valid_amount(data, payment):
    try:
        return Decimal(str(data.get("gross_amount"))) == payment.jumlah and data.get("order_id") == payment.gateway_order_id
    except (InvalidOperation, TypeError):
        return False
