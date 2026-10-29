from django.db.models import Q


def _display_name(user):
    profile = getattr(user, "profile", None)
    return profile.full_name if profile and profile.full_name else user.username


def get_blocking_transactions(user):
    """
    Daftar transaksi berjalan yang MENGHALANGI penonaktifan akun `user`.
    List kosong = boleh dinonaktifkan. Tiap item: {"label": "...", "status": "..."}.

    Yang dianggap berjalan: pesanan berstatus WAITING (menunggu pembayaran) dan
    CONFIRMED (sudah terkonfirmasi, belum selesai), baik sebagai peminjam maupun pemilik.
    Keduanya selesai sendiri: WAITING dibatalkan otomatis setelah 30 menit, dan
    CONFIRMED menjadi COMPLETED saat masa pinjam berakhir (lihat maintain_orders).
    """
    # Import di dalam fungsi untuk menghindari import melingkar antar-app
    from transaksi.models import Pesanan
    from transaksi.services import maintain_orders

    maintain_orders()  # rapikan dulu pesanan yang sudah kedaluwarsa / selesai

    orders = (
        Pesanan.objects
        .filter(
            Q(peminjam=user) | Q(pemilik=user),
            status__in=(Pesanan.Status.WAITING, Pesanan.Status.CONFIRMED),
        )
        .select_related("peminjam", "pemilik")
    )

    items = []
    for order in orders:
        nama = order.nama_barang or "barang"
        menunggu = order.status == Pesanan.Status.WAITING
        if order.peminjam_id == user.id:
            owner = _display_name(order.pemilik)
            label = (
                f"Pesananmu untuk {nama} dari {owner} menunggu pembayaran"
                if menunggu else
                f"Kamu punya pesanan terkonfirmasi: {nama} dari {owner}"
            )
        else:
            borrower = _display_name(order.peminjam)
            label = (
                f"{nama} milikmu sedang dipesan {borrower} (menunggu pembayaran)"
                if menunggu else
                f"{nama} milikmu sudah dipesan {borrower} (terkonfirmasi)"
            )
        items.append({"label": label, "status": order.get_status_display()})
    return items