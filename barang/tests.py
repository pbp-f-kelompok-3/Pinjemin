"""
Unit Tests untuk Modul Manajemen Barang (Fauzan Taqiy Santosa - NPM: 2506607272)
Sesuai Rubrik Penilaian Proyek Pemrograman Berbasis Platform (PBP) Fasilkom UI
"""

import io
from PIL import Image
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from barang.models import Kategori, Lokasi, Barang
from categories.models import Category
from transaksi.models import Pesanan, Ulasan

User = get_user_model()


def generate_test_image():
    """Menghasilkan file gambar dummy dalam format in-memory PNG."""
    file = io.BytesIO()
    image = Image.new('RGB', (100, 100), color='blue')
    image.save(file, 'png')
    file.seek(0)
    return SimpleUploadedFile("test_foto.png", file.read(), content_type="image/png")


class BarangModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fauzan_test", password="testpassword123")
        self.kategori, _ = Category.objects.get_or_create(name="Elektronik Kost")
        self.lokasi = Lokasi.objects.create(
            nama_area="Area Kutek UI",
            short_label="Kutek UI",
            patokan="Dekat Alfamart Kutek"
        )

    def test_kategori_str(self):
        self.assertEqual(str(self.kategori), "Elektronik Kost")

    def test_lokasi_str(self):
        self.assertIn("Kutek UI", str(self.lokasi))

    def test_create_barang_sewa_valid(self):
        barang = Barang.objects.create(
            pemilik=self.user,
            nama_barang="Setrika Uap Philips",
            foto_utama=generate_test_image(),
            deskripsi="Setrika uap kondisi mulus 95%, watt rendah.",
            kategori=self.kategori,
            jenis_penawaran="sewa",
            tarif_per_hari=25000,
            lokasi=self.lokasi
        )
        self.assertEqual(barang.tarif_per_hari, 25000)
        self.assertEqual(barang.tarif_formatted, "25.000")
        self.assertTrue(barang.can_be_deleted())

    def test_create_barang_gratis_auto_zero(self):
        barang = Barang.objects.create(
            pemilik=self.user,
            nama_barang="Obeng Presisi Set",
            foto_utama=generate_test_image(),
            deskripsi="Dipinjamkan gratis untuk sesama anak kost.",
            kategori=self.kategori,
            jenis_penawaran="gratis",
            tarif_per_hari=50000,  # otomatis di-reset ke 0 oleh clean()
            lokasi=self.lokasi
        )
        self.assertEqual(barang.tarif_per_hari, 0)
        self.assertEqual(barang.tarif_formatted, "0")

    def test_barang_sewa_invalid_zero_price(self):
        barang = Barang(
            pemilik=self.user,
            nama_barang="Kamera DSLR Canon",
            foto_utama=generate_test_image(),
            deskripsi="Kamera sewa.",
            kategori=self.kategori,
            jenis_penawaran="sewa",
            tarif_per_hari=0,
            lokasi=self.lokasi
        )
        with self.assertRaises(ValidationError):
            barang.full_clean()

    def test_can_be_deleted_when_not_borrowed(self):
        barang = Barang.objects.create(
            pemilik=self.user,
            nama_barang="Jas Sidang Hitam",
            foto_utama=generate_test_image(),
            deskripsi="Jas sidang pria ukuran L.",
            kategori=self.kategori,
            jenis_penawaran="sewa",
            tarif_per_hari=30000,
            lokasi=self.lokasi
        )
        self.assertFalse(barang.is_sedang_dipinjam)
        self.assertTrue(barang.can_be_deleted())


class BarangViewTest(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.user = User.objects.create_user(username="fauzan_mhs", password="password123")
        self.kategori = Category.objects.create(name="Pakaian")
        self.lokasi = Lokasi.objects.create(nama_area="Barel UI", short_label="Barel UI", patokan="Dekat Kober")
        self.barang = Barang.objects.create(
            pemilik=self.user,
            nama_barang="Kemeja Putih Formal",
            foto_utama=generate_test_image(),
            deskripsi="Kemeja putih lengan panjang untuk sidang.",
            kategori=self.kategori,
            jenis_penawaran="sewa",
            tarif_per_hari=20000,
            lokasi=self.lokasi
        )

    def test_dashboard_unauthenticated_redirects(self):
        response = self.client.get(reverse('barang:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/akun/login/', response.url)

    def test_dashboard_authenticated_success(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('barang:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kemeja Putih Formal")

    def test_tambah_barang_page_accessible(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('barang:tambah'))
        self.assertEqual(response.status_code, 200)

    def test_tambah_barang_post_success(self):
        self.client.force_login(self.user)
        data = {
            'nama_barang': 'Kalkulator Casio FX-991EX',
            'foto_utama': generate_test_image(),
            'deskripsi': 'Kalkulator scientific untuk ujian Teknik & Fasilkom.',
            'kategori': self.kategori.pk,
            'jenis_penawaran': 'sewa',
            'tarif_per_hari': 15000,
            'lokasi': self.lokasi.pk,
        }
        response = self.client.post(reverse('barang:tambah'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Barang.objects.filter(nama_barang='Kalkulator Casio FX-991EX').exists())

    def test_xss_protection_strips_html(self):
        self.client.force_login(self.user)
        data = {
            'nama_barang': '<b>Kamera Canon</b>',
            'foto_utama': generate_test_image(),
            'deskripsi': '<i>Kondisi mulus sekali</i>',
            'kategori': self.kategori.pk,
            'jenis_penawaran': 'sewa',
            'tarif_per_hari': 50000,
            'lokasi': self.lokasi.pk,
        }
        response = self.client.post(reverse('barang:tambah'), data)
        self.assertEqual(response.status_code, 302)
        barang = Barang.objects.get(tarif_per_hari=50000)
        self.assertEqual(barang.nama_barang, 'Kamera Canon')
        self.assertEqual(barang.deskripsi, 'Kondisi mulus sekali')

    def test_edit_barang_post_success(self):
        self.client.force_login(self.user)
        data = {
            'nama_barang': 'Kemeja Putih Formal (Size L)',
            'deskripsi': 'Sudah di-laundry wangi.',
            'kategori': self.kategori.pk,
            'jenis_penawaran': 'sewa',
            'tarif_per_hari': 25000,
            'lokasi': self.lokasi.pk,
            'status_penawaran': 'aktif',
        }
        response = self.client.post(reverse('barang:edit', kwargs={'pk': self.barang.pk}), data)
        self.assertEqual(response.status_code, 302)
        self.barang.refresh_from_db()
        self.assertEqual(self.barang.nama_barang, 'Kemeja Putih Formal (Size L)')

    def test_hapus_barang_success(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('barang:hapus', kwargs={'pk': self.barang.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Barang.objects.filter(pk=self.barang.pk).exists())

    def test_hapus_barang_ajax_success(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('barang:hapus_ajax', kwargs={'pk': self.barang.pk}))
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data['status'], 'success')
        self.assertFalse(Barang.objects.filter(pk=self.barang.pk).exists())

    def test_hapus_barang_ajax_unauthorized_user(self):
        other_user = User.objects.create_user(username="other", password="password")
        self.client.force_login(other_user)
        response = self.client.post(reverse('barang:hapus_ajax', kwargs={'pk': self.barang.pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Barang.objects.filter(pk=self.barang.pk).exists())


class BarangAPITest(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.user = User.objects.create_user(username="api_user", password="password123")
        self.kategori = Category.objects.create(name="Buku")
        self.lokasi = Lokasi.objects.create(nama_area="Pocin", short_label="Pocin", patokan="Stasiun Pocin")
        self.barang = Barang.objects.create(
            pemilik=self.user,
            nama_barang="Buku Algoritma & Struktur Data",
            foto_utama=generate_test_image(),
            deskripsi="Buku teks kuliah Fasilkom UI.",
            kategori=self.kategori,
            jenis_penawaran="gratis",
            tarif_per_hari=0,
            lokasi=self.lokasi
        )

    def test_show_json(self):
        response = self.client.get(reverse('barang:show_json'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertContains(response, "Buku Algoritma & Struktur Data")

    def test_show_json_by_id(self):
        response = self.client.get(reverse('barang:show_json_by_id', kwargs={'pk': self.barang.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertContains(response, "Buku Algoritma & Struktur Data")

    def test_show_xml(self):
        response = self.client.get(reverse('barang:show_xml'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')
        self.assertContains(response, "<django-objects")


class KatalogBerandaTest(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.user = User.objects.create_user(username="katalog_user", password="password123")
        self.kat_buku = Category.objects.create(name="Buku")
        self.kat_elektronik = Category.objects.create(name="Elektronik")
        self.lokasi = Lokasi.objects.create(nama_area="Pocin", short_label="Pocin", patokan="Stasiun Pocin")

        # Barang 1: Buku - Gratis - dilihat 5
        self.b1 = Barang.objects.create(
            pemilik=self.user,
            nama_barang="Buku Kalkulus Purcel",
            foto_utama=generate_test_image(),
            deskripsi="Buku paket edisi 9.",
            kategori=self.kat_buku,
            jenis_penawaran="gratis",
            tarif_per_hari=0,
            lokasi=self.lokasi,
            dilihat_count=5
        )
        # Barang 2: Mouse Wireless - Sewa 15.000 - dilihat 20
        self.b2 = Barang.objects.create(
            pemilik=self.user,
            nama_barang="Mouse Logitech Wireless",
            foto_utama=generate_test_image(),
            deskripsi="Mouse ergonomis kondisi mulus.",
            kategori=self.kat_elektronik,
            jenis_penawaran="sewa",
            tarif_per_hari=15000,
            lokasi=self.lokasi,
            dilihat_count=20
        )
        # Barang 3: Proyektor Epson - Sewa 50.000 - dilihat 10
        self.b3 = Barang.objects.create(
            pemilik=self.user,
            nama_barang="Proyektor Epson HDMI",
            foto_utama=generate_test_image(),
            deskripsi="Proyektor terang untuk presentasi.",
            kategori=self.kat_elektronik,
            jenis_penawaran="sewa",
            tarif_per_hari=50000,
            lokasi=self.lokasi,
            dilihat_count=10
        )

    def test_home_status_code_and_render(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")
        self.assertEqual(len(response.context['barang_list']), 3)

    def test_home_search_query(self):
        response = self.client.get(reverse('home'), {'q': 'Logitech'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['barang_list']), 1)
        self.assertEqual(response.context['barang_list'][0].pk, self.b2.pk)
        self.assertEqual(response.context['current_q'], 'Logitech')

    def test_home_filter_kategori(self):
        response = self.client.get(reverse('home'), {'kategori': self.kat_elektronik.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['barang_list']), 2)
        self.assertEqual(response.context['current_kategori'], str(self.kat_elektronik.pk))

    def test_home_filter_price_type_and_range(self):
        # Filter sewa dengan harga 10.000 s.d 20.000
        response = self.client.get(reverse('home'), {
            'price_type': 'sewa',
            'min_price': '10000',
            'max_price': '20000',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['barang_list']), 1)
        self.assertEqual(response.context['barang_list'][0].pk, self.b2.pk)
        self.assertEqual(response.context['current_price_type'], 'sewa')
        self.assertEqual(response.context['current_min_price'], 10000)
        self.assertEqual(response.context['current_max_price'], 20000)
        # Check inputs value retained in HTML
        self.assertContains(response, 'value="10000"')
        self.assertContains(response, 'value="20000"')

    def test_home_sorting_harga_asc(self):
        response = self.client.get(reverse('home'), {'sort': 'harga_asc'})
        self.assertEqual(response.status_code, 200)
        items = list(response.context['barang_list'])
        self.assertEqual([item.pk for item in items], [self.b1.pk, self.b2.pk, self.b3.pk])

    def test_home_sorting_harga_desc(self):
        response = self.client.get(reverse('home'), {'sort': 'harga_desc'})
        self.assertEqual(response.status_code, 200)
        items = list(response.context['barang_list'])
        self.assertEqual([item.pk for item in items], [self.b3.pk, self.b2.pk, self.b1.pk])

    def test_home_sorting_nama_asc(self):
        response = self.client.get(reverse('home'), {'sort': 'nama_asc'})
        self.assertEqual(response.status_code, 200)
        items = list(response.context['barang_list'])
        self.assertEqual([item.pk for item in items], [self.b1.pk, self.b2.pk, self.b3.pk])

    def test_home_sorting_sering_dipinjam(self):
        response = self.client.get(reverse('home'), {'sort': 'sering_dipinjam'})
        self.assertEqual(response.status_code, 200)
        items = list(response.context['barang_list'])
        self.assertEqual([item.pk for item in items], [self.b2.pk, self.b3.pk, self.b1.pk])

    def test_home_combined_filters_preservation(self):
        response = self.client.get(reverse('home'), {
            'kategori': self.kat_elektronik.pk,
            'q': 'Proyektor',
            'price_type': 'sewa',
            'min_price': '30000',
            'max_price': '60000',
            'sort': 'harga_desc'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['barang_list']), 1)
        self.assertEqual(response.context['barang_list'][0].pk, self.b3.pk)
        self.assertEqual(response.context['current_q'], 'Proyektor')
        self.assertEqual(response.context['current_kategori'], str(self.kat_elektronik.pk))
        self.assertEqual(response.context['current_sort'], 'harga_desc')


class BorrowFlowIntegrationTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner_user", password="password123")
        self.borrower = User.objects.create_user(username="borrower_user", password="password123")
        self.kategori = Category.objects.create(name="Peralatan Belajar")
        self.lokasi = Lokasi.objects.create(
            nama_area="Perpustakaan Pusat UI",
            short_label="Perpusat UI",
            patokan="Lantai 1 dekat Starbucks"
        )
        self.barang = Barang.objects.create(
            pemilik=self.owner,
            nama_barang="Kalkulator Ilmiah Casio",
            foto_utama=generate_test_image(),
            deskripsi="Kalkulator scientific fx-991EX mulus.",
            kategori=self.kategori,
            jenis_penawaran="sewa",
            tarif_per_hari=15000,
            lokasi=self.lokasi,
            status_penawaran="aktif"
        )

    def test_detail_page_cta_anonymous_user(self):
        response = self.client.get(reverse('barang:detail', args=[self.barang.pk]))
        self.assertEqual(response.status_code, 200)
        login_url = reverse('accounts:login')
        self.assertContains(response, f'{login_url}?next=')
        self.assertContains(response, "Masuk dengan SSO UI untuk Pinjam")

    def test_detail_page_cta_for_owner(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('barang:detail', args=[self.barang.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ini adalah barang inventaris milikmu sendiri")
        self.assertContains(response, reverse('barang:edit', args=[self.barang.pk]))
        self.assertNotContains(response, 'onclick="openBorrowModal()"')

    def test_detail_page_cta_for_borrower(self):
        self.client.force_login(self.borrower)
        response = self.client.get(reverse('barang:detail', args=[self.barang.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'onclick="openBorrowModal()"')
        self.assertContains(response, "Sewa Barang Sekarang")
        self.assertContains(response, reverse('transaksi:buat', args=[self.barang.pk]))

    def test_detail_page_cta_for_inactive_item(self):
        self.barang.status_penawaran = "nonaktif"
        self.barang.save()
        self.client.force_login(self.borrower)
        response = self.client.get(reverse('barang:detail', args=[self.barang.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Barang Dinonaktifkan Sementara")
        self.assertNotContains(response, 'onclick="openBorrowModal()"')

    def test_checkout_create_view_rejects_owner(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('transaksi:buat', args=[self.barang.pk]))
        self.assertRedirects(response, reverse('barang:detail', args=[self.barang.pk]))

    def test_checkout_create_view_allows_borrower(self):
        self.client.force_login(self.borrower)
        response = self.client.get(reverse('transaksi:buat', args=[self.barang.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kalkulator Ilmiah Casio")


class Phase34BusinessRulesAndLenderTest(TestCase):
    def setUp(self):
        from accounts.models import Profile
        self.owner = User.objects.create_user(username="lender_user", password="password123")
        self.borrower = User.objects.create_user(username="renter_user", password="password123")
        
        owner_profile, _ = Profile.objects.get_or_create(user=self.owner)
        owner_profile.phone = "081298765432"
        owner_profile.save()
        
        borrower_profile, _ = Profile.objects.get_or_create(user=self.borrower)
        borrower_profile.phone = "081211112222"
        borrower_profile.save()

        self.kategori = Category.objects.create(name="Alat Musik Kost")
        self.lokasi = Lokasi.objects.create(
            nama_area="Kutek UI",
            short_label="Kutek",
            patokan="Dekat Gang Kober"
        )
        self.barang = Barang.objects.create(
            pemilik=self.owner,
            nama_barang="Gitar Akustik Yamaha",
            foto_utama=generate_test_image(),
            deskripsi="Gitar akustik senar nilon empuk.",
            kategori=self.kategori,
            jenis_penawaran="sewa",
            tarif_per_hari=20000,
            lokasi=self.lokasi,
            status_penawaran="aktif"
        )

    def test_dashboard_shows_pesanan_masuk_and_locked_status(self):
        now = timezone.now()
        Pesanan.objects.create(
            peminjam=self.borrower,
            barang=self.barang,
            pemilik=self.owner,
            mulai=now + timedelta(days=1),
            durasi=2,
            selesai=now + timedelta(days=3),
            tarif_per_hari=20000,
            total=40000,
            nama_barang=self.barang.nama_barang,
            lokasi_snapshot={"label": "Kutek", "alamat": "Kutek UI"},
            status=Pesanan.Status.CONFIRMED
        )

        self.client.force_login(self.owner)
        response = self.client.get(reverse('barang:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pesanan_masuk_count'], 1)
        self.assertContains(response, "Pesanan Masuk")
        self.assertContains(response, "Terkunci")
        self.assertNotContains(response, reverse('barang:edit', args=[self.barang.pk]))

    def test_edit_barang_rejected_when_transaksi_terkunci(self):
        now = timezone.now()
        Pesanan.objects.create(
            peminjam=self.borrower,
            barang=self.barang,
            pemilik=self.owner,
            mulai=now + timedelta(days=1),
            durasi=2,
            selesai=now + timedelta(days=3),
            tarif_per_hari=20000,
            total=40000,
            nama_barang=self.barang.nama_barang,
            status=Pesanan.Status.CONFIRMED
        )

        self.client.force_login(self.owner)
        response = self.client.get(reverse('barang:edit', args=[self.barang.pk]))
        self.assertRedirects(response, reverse('barang:dashboard'))

        post_response = self.client.post(reverse('barang:edit', args=[self.barang.pk]), {
            'nama_barang': 'Gitar Berubah',
            'deskripsi': 'Gitar akustik senar nilon empuk.',
            'jenis_penawaran': 'sewa',
            'tarif_per_hari': 25000,
            'kategori': self.kategori.pk,
            'status_penawaran': 'aktif',
            'pickup_point_choice': 'saved_1'
        })
        self.assertRedirects(post_response, reverse('barang:dashboard'))

    def test_hapus_barang_rejected_when_not_can_be_deleted(self):
        now = timezone.now()
        Pesanan.objects.create(
            peminjam=self.borrower,
            barang=self.barang,
            pemilik=self.owner,
            mulai=now + timedelta(days=1),
            durasi=2,
            selesai=now + timedelta(days=3),
            tarif_per_hari=20000,
            total=40000,
            nama_barang=self.barang.nama_barang,
            status=Pesanan.Status.CONFIRMED
        )

        self.client.force_login(self.owner)
        response = self.client.post(reverse('barang:hapus', args=[self.barang.pk]))
        self.assertRedirects(response, reverse('barang:dashboard'))
        self.assertTrue(Barang.objects.filter(pk=self.barang.pk).exists())

    def test_hapus_barang_ajax_rejected_when_not_can_be_deleted(self):
        now = timezone.now()
        Pesanan.objects.create(
            peminjam=self.borrower,
            barang=self.barang,
            pemilik=self.owner,
            mulai=now + timedelta(days=1),
            durasi=2,
            selesai=now + timedelta(days=3),
            tarif_per_hari=20000,
            total=40000,
            nama_barang=self.barang.nama_barang,
            status=Pesanan.Status.CONFIRMED
        )

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('barang:hapus_ajax', args=[self.barang.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Barang.objects.filter(pk=self.barang.pk).exists())

    def test_whatsapp_coordination_in_transaksi_detail(self):
        now = timezone.now()
        order = Pesanan.objects.create(
            peminjam=self.borrower,
            barang=self.barang,
            pemilik=self.owner,
            mulai=now + timedelta(days=1),
            durasi=2,
            selesai=now + timedelta(days=3),
            tarif_per_hari=20000,
            total=40000,
            nama_barang=self.barang.nama_barang,
            lokasi_snapshot={"label": "Kutek", "alamat": "Kutek UI"},
            status=Pesanan.Status.CONFIRMED
        )

        # Borrower sees WhatsApp button to owner
        self.client.force_login(self.borrower)
        borrower_resp = self.client.get(reverse('transaksi:detail', args=[order.pk]))
        self.assertEqual(borrower_resp.status_code, 200)
        self.assertContains(borrower_resp, "Hubungi pemilik via WhatsApp")
        self.assertContains(borrower_resp, "6281298765432")

        # Owner sees WhatsApp button to borrower
        self.client.force_login(self.owner)
        owner_resp = self.client.get(reverse('transaksi:detail', args=[order.pk]))
        self.assertEqual(owner_resp.status_code, 200)
        self.assertContains(owner_resp, "Hubungi peminjam via WhatsApp")
        self.assertContains(owner_resp, "6281211112222")


class Phase56ReturnAndReviewTest(TestCase):
    def setUp(self):
        from accounts.models import Profile
        self.owner = User.objects.create_user(username="owner_user", password="password123")
        self.borrower = User.objects.create_user(username="renter_user", password="password123")
        self.third_party = User.objects.create_user(username="other_user", password="password123")

        self.owner_profile, _ = Profile.objects.get_or_create(user=self.owner)
        self.owner_profile.full_name = "Fauzan Owner"
        self.owner_profile.phone = "081298765432"
        self.owner_profile.is_onboarded = True
        self.owner_profile.save()

        self.borrower_profile, _ = Profile.objects.get_or_create(user=self.borrower)
        self.borrower_profile.full_name = "Budi Borrower"
        self.borrower_profile.phone = "081211112222"
        self.borrower_profile.is_onboarded = True
        self.borrower_profile.save()

        self.kategori = Category.objects.create(name="Perlengkapan Belajar")
        self.lokasi = Lokasi.objects.create(
            nama_area="Kutek UI",
            short_label="Kutek",
            patokan="Kutek Dekat Indomaret"
        )
        self.barang = Barang.objects.create(
            pemilik=self.owner,
            nama_barang="Kalkulator Saintifik Casio",
            foto_utama=generate_test_image(),
            deskripsi="Kalkulator saintifik FX-991EX mulus.",
            kategori=self.kategori,
            jenis_penawaran="sewa",
            tarif_per_hari=15000,
            lokasi=self.lokasi,
            status_penawaran="aktif"
        )
        now = timezone.now()
        self.order = Pesanan.objects.create(
            peminjam=self.borrower,
            barang=self.barang,
            pemilik=self.owner,
            mulai=now - timedelta(days=1),
            durasi=2,
            selesai=now + timedelta(days=1),
            tarif_per_hari=15000,
            total=30000,
            nama_barang=self.barang.nama_barang,
            lokasi_snapshot={"label": "Kutek", "alamat": "Kutek Dekat Indomaret"},
            status=Pesanan.Status.CONFIRMED
        )

    def test_owner_can_complete_confirmed_order(self):
        # Initial state: barang sedang dipinjam
        self.assertTrue(self.barang.is_sedang_dipinjam)

        self.client.force_login(self.owner)
        response = self.client.post(reverse('transaksi:selesaikan', args=[self.order.pk]))
        self.assertRedirects(response, reverse('transaksi:detail', args=[self.order.pk]))

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Pesanan.Status.COMPLETED)
        # Barang is now available again
        self.assertFalse(self.barang.is_sedang_dipinjam)

    def test_non_owner_cannot_complete_order(self):
        self.client.force_login(self.borrower)
        response = self.client.post(reverse('transaksi:selesaikan', args=[self.order.pk]))
        self.assertRedirects(response, reverse('transaksi:detail', args=[self.order.pk]))

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Pesanan.Status.CONFIRMED)

    def test_borrower_can_submit_review_on_completed_order(self):
        # Complete order first
        self.order.status = Pesanan.Status.COMPLETED
        self.order.save()

        self.client.force_login(self.borrower)
        get_resp = self.client.get(reverse('transaksi:beri_ulasan', args=[self.order.pk]))
        self.assertEqual(get_resp.status_code, 200)

        post_resp = self.client.post(reverse('transaksi:beri_ulasan', args=[self.order.pk]), {
            'rating': 5,
            'komentar': 'Kalkulator sangat bagus, baterai awet, pemilik sangat ramah!'
        })
        self.assertRedirects(post_resp, reverse('transaksi:detail', args=[self.order.pk]))

        ulasan = Ulasan.objects.get(pesanan=self.order)
        self.assertEqual(ulasan.rating, 5)
        self.assertEqual(ulasan.komentar, 'Kalkulator sangat bagus, baterai awet, pemilik sangat ramah!')
        self.assertEqual(ulasan.peminjam, self.borrower)
        self.assertEqual(ulasan.pemilik, self.owner)
        self.assertEqual(ulasan.barang, self.barang)

    def test_duplicate_review_is_prevented(self):
        self.order.status = Pesanan.Status.COMPLETED
        self.order.save()

        Ulasan.objects.create(
            pesanan=self.order,
            peminjam=self.borrower,
            pemilik=self.owner,
            barang=self.barang,
            rating=5,
            komentar="Review pertama."
        )

        self.client.force_login(self.borrower)
        response = self.client.post(reverse('transaksi:beri_ulasan', args=[self.order.pk]), {
            'rating': 4,
            'komentar': 'Mencoba review kedua.'
        })
        self.assertRedirects(response, reverse('transaksi:detail', args=[self.order.pk]))
        self.assertEqual(Ulasan.objects.filter(pesanan=self.order).count(), 1)

    def test_non_borrower_cannot_review(self):
        self.order.status = Pesanan.Status.COMPLETED
        self.order.save()

        self.client.force_login(self.third_party)
        response = self.client.get(reverse('transaksi:beri_ulasan', args=[self.order.pk]))
        self.assertRedirects(response, reverse('transaksi:detail', args=[self.order.pk]), target_status_code=404)

    def test_cannot_review_uncompleted_order(self):
        # Order is still CONFIRMED
        self.client.force_login(self.borrower)
        response = self.client.get(reverse('transaksi:beri_ulasan', args=[self.order.pk]))
        self.assertRedirects(response, reverse('transaksi:detail', args=[self.order.pk]))

    def test_public_profile_displays_reputation_and_reviews(self):
        self.order.status = Pesanan.Status.COMPLETED
        self.order.save()

        Ulasan.objects.create(
            pesanan=self.order,
            peminjam=self.borrower,
            pemilik=self.owner,
            barang=self.barang,
            rating=5,
            komentar="Pemilik sangat ramah dan barang terawat prima!"
        )

        self.client.force_login(self.borrower)
        response = self.client.get(reverse('accounts:profile_public', args=[self.owner_profile.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "5.0")
        self.assertContains(response, "Pemilik sangat ramah dan barang terawat prima!")
        self.assertContains(response, "Kalkulator Saintifik Casio")

    def test_detail_barang_contains_profile_link(self):
        response = self.client.get(reverse('barang:detail', args=[self.barang.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lihat Profil")
        self.assertContains(response, reverse('accounts:profile_public', args=[self.owner_profile.pk]))

