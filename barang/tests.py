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
from barang.models import Kategori, Lokasi, Barang
from categories.models import Category

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
