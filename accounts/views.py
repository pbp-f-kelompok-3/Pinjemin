from django.db.models import Avg
from transaksi.models import Ulasan, Pesanan
from barang.models import Barang
import xml.etree.ElementTree as ET

import requests
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import OnboardingForm, ProfileForm
from .models import Profile
from .services import get_blocking_transactions
from .sso import get_login_url, validate_ticket

User = get_user_model()


def _callback_url(request):
    # Harus IDENTIK saat redirect ke SSO dan saat validasi ticket
    return request.build_absolute_uri(reverse("accounts:sso_callback"))


def login_page(request):
    if request.user.is_authenticated:
        return redirect("/")
    return render(request, "accounts/login.html")


def sso_login(request):
    """Simpan tujuan awal, lalu lempar user ke halaman login SSO UI."""
    next_url = request.GET.get("next", "")
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        request.session["post_login_next"] = next_url
    return redirect(get_login_url(_callback_url(request)))


def sso_callback(request):
    ticket = request.GET.get("ticket")
    if not ticket:
        messages.error(request, "Login dibatalkan atau gagal. Silakan coba lagi.")
        return redirect("accounts:login")

    try:
        result = validate_ticket(ticket, _callback_url(request))
    except requests.HTTPError as exc:
        resp = exc.response
        status = resp.status_code if resp is not None else None
        print("SSO HTTP ERROR:", status, (resp.text[:300] if resp is not None else ""))
        if status == 400:
            messages.error(request, "SSO UI menolak permintaan login. Silakan coba lagi.")
        else:
            messages.error(request, "SSO UI sedang bermasalah. Coba lagi beberapa saat.")
        return redirect("accounts:login")
    except (requests.RequestException, ET.ParseError) as exc:
        print("SSO ERROR:", repr(exc))
        messages.error(request, "SSO UI sedang bermasalah. Coba lagi beberapa saat.")
        return redirect("accounts:login")

    if result is None:
        messages.error(request, "Validasi SSO gagal. Silakan login ulang.")
        return redirect("accounts:login")

    attrs = result["attributes"]

    # Pinjemin khusus mahasiswa UI
    role = attrs.get("peran_user", "").lower()
    if not attrs.get("npm"):
        messages.error(request, "Pinjemin hanya untuk mahasiswa Universitas Indonesia.")
        return redirect("accounts:login")

    user, created = User.objects.get_or_create(username=result["username"])
    if created:
        user.set_unusable_password()  # login hanya lewat SSO
        user.save()

    profile, _ = Profile.objects.get_or_create(user=user)
    profile.npm = attrs.get("npm", profile.npm)
    profile.full_name = attrs.get("nama", profile.full_name)
    profile.kode_org = attrs.get("kd_org", profile.kode_org)

    # Akun yang pernah dinonaktifkan diaktifkan kembali (SSO sudah membuktikan identitasnya)
    reactivated = profile.deactivated_at is not None
    if reactivated:
        profile.deactivated_at = None
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
    profile.save()

    # Akun yang dinonaktifkan pengelola (bukan oleh pemiliknya sendiri) tetap ditolak
    if not user.is_active:
        messages.error(request, "Akun ini tidak dapat digunakan. Hubungi pengelola.")
        return redirect("accounts:login")

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    if reactivated:
        messages.success(request, "Selamat datang kembali! Akunmu sudah aktif lagi.")

    if not profile.is_onboarded:
        return redirect("accounts:onboarding")
    return redirect(request.session.pop("post_login_next", "/"))


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "Kamu sudah keluar.")
    return redirect("accounts:login")


@login_required
def onboarding(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if profile.is_onboarded:
        return redirect("/")

    form = OnboardingForm(request.POST or None, request.FILES or None, instance=profile)
    start_step = 1

    if request.method == "POST":
        if form.is_valid():
            profile = form.save(commit=False)
            profile.is_onboarded = True
            profile.accepted_privacy_at = timezone.now()
            profile.save()
            messages.success(request, "Selamat datang di Pinjemin!")
            return redirect(request.session.pop("post_login_next", "/"))
        # kalau ada error, buka langkah yang bermasalah
        start_step = 3 if set(form.errors) <= {"accept_privacy", "mode"} else 2

    first_name = (profile.full_name or request.user.username).split()[0]
    return render(request, "accounts/onboarding.html", {
        "form": form,
        "profile": profile,
        "first_name": first_name,
        "start_step": start_step,
    })


@login_required
def profile_detail(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, "accounts/profile.html", {"profile": profile})


@login_required
def profile_edit(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profil berhasil diperbarui.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile_edit.html", {"form": form, "profile": profile})


@login_required
def profile_public(request, pk):
    profile = get_object_or_404(Profile, pk=pk, is_onboarded=True)
    if profile.deactivated_at:
        return render(request, "accounts/profile_unavailable.html", status=404)
    user = profile.user

    # Transaksi selesai milik pemilik barang ini
    done_count = Pesanan.objects.filter(pemilik=user, status=Pesanan.Status.COMPLETED).count()

    # Ulasan yang diterima pemilik ini dari para peminjam
    reviews = Ulasan.objects.filter(pemilik=user).select_related("peminjam", "peminjam__profile", "barang")
    review_count = reviews.count()
    avg_rating = reviews.aggregate(Avg("rating"))["rating__avg"]
    rating = f"{avg_rating:.1f}" if avg_rating is not None else "-"

    # Barang aktif yang sedang dipinjamkan / ditawarkan
    barang_list = Barang.objects.filter(pemilik=user, status_penawaran="aktif").select_related("kategori", "lokasi")

    return render(request, "accounts/profile_public.html", {
        "profile": profile,
        "is_owner": profile.user_id == request.user.id,
        "done_count": done_count,
        "review_count": review_count,
        "rating": rating,
        "reviews": reviews,
        "barang_list": barang_list,
    })


@login_required
@require_POST
def toggle_mode(request):
    profile = request.user.profile
    requested = request.POST.get("mode")
    if requested in Profile.Mode.values:
        profile.mode = requested
    else:
        profile.mode = (
            Profile.Mode.SELLER if profile.mode == Profile.Mode.RENTER else Profile.Mode.RENTER
        )
    profile.save(update_fields=["mode"])

    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = "/"
    return redirect(next_url)


@login_required
def deactivate_account(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    blocking = get_blocking_transactions(request.user)

    if request.method == "POST":
        if blocking:
            messages.error(request, "Akun belum bisa dinonaktifkan karena masih ada transaksi berjalan.")
        elif request.POST.get("confirm") != "yes":
            messages.error(request, "Centang konfirmasi dulu untuk melanjutkan.")
        else:
            user = request.user
            profile.deactivated_at = timezone.now()
            profile.save(update_fields=["deactivated_at"])
            # is_active=False juga mengakhiri sesi di perangkat lain dan dikenali filter
            # `pemilik__is_active=True` yang sudah dipakai modul katalog
            user.is_active = False
            user.save(update_fields=["is_active"])
            logout(request)
            messages.success(
                request,
                "Akunmu sudah dinonaktifkan. Login lagi dengan SSO UI kapan saja untuk mengaktifkannya kembali.",
            )
            return redirect("accounts:login")

    return render(request, "accounts/account_deactivate.html", {
        "profile": profile,
        "blocking": blocking,
    })