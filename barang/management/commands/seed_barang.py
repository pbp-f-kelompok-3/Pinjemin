from django.core.management.base import BaseCommand
from barang.models import Kategori, Lokasi
from categories.models import Category


class Command(BaseCommand):
    help = 'Mengisi data awal Kategori dan Lokasi kampus UI untuk modul Manajemen Barang'

    def handle(self, *args, **options):
        kategori_data = [
            {'nama': 'Pakaian & Formal', 'slug': 'pakaian-formal', 'deskripsi': 'Jas sidang, toga, kemeja batik, dan setelan formal.'},
            {'nama': 'Elektronik Kost', 'slug': 'elektronik-kost', 'deskripsi': 'Setrika, hair dryer, monitor portabel, printer, dsb.'},
            {'nama': 'Travel & Kebutuhan Lomba', 'slug': 'travel-lomba', 'deskripsi': 'Koper, ransel gunung, adaptor internasional, gimbal stabilizer.'},
            {'nama': 'Perlengkapan Acara', 'slug': 'perlengkapan-acara', 'deskripsi': 'Speaker portabel, mic wireless, proyektor mini, roll kabel.'},
            {'nama': 'Alat Ujian & Kuliah Teknik', 'slug': 'alat-ujian-teknik', 'deskripsi': 'Kalkulator scientific, jangka, busur teknik, helm safety proyek.'},
            {'nama': 'Buku & Referensi', 'slug': 'buku-referensi', 'deskripsi': 'Buku teks wajib kuliah, kamus, materi latihan toefl/ielts.'},
        ]

        lokasi_data = [
            {
                'nama_area': 'Area Kutek UI (Kukusan Teknik)',
                'kecamatan_kota': 'Kecamatan Beji, Kota Depok, Jawa Barat 16425',
                'kode_pos': '16425',
                'patokan': 'Dekat Alfamart Kutek / Gerbang Motor Teknik UI',
                'short_label': 'Kutek UI',
            },
            {
                'nama_area': 'Area Kukusan III (Kukusan, Beji)',
                'kecamatan_kota': 'Kecamatan Beji, Kota Depok, Jawa Barat 16425',
                'kode_pos': '16425',
                'patokan': 'Dekat Gang Pepaya / 300m dari Gerbang Kukusan Teknik UI',
                'short_label': 'Kukel',
            },
            {
                'nama_area': 'Area Barel UI (Bawah Rel Pocin)',
                'kecamatan_kota': 'Kecamatan Beji, Kota Depok, Jawa Barat 16424',
                'kode_pos': '16424',
                'patokan': 'Dekat Stasiun Pondok Cina / Gang Kober',
                'short_label': 'Barel UI',
            },
            {
                'nama_area': 'Area Pocin (Pondok Cina)',
                'kecamatan_kota': 'Kecamatan Beji, Kota Depok, Jawa Barat 16424',
                'kode_pos': '16424',
                'patokan': 'Seberang Margo City / Stasiun Pocin UI',
                'short_label': 'Pocin',
            },
            {
                'nama_area': 'Area Lingkungan Kampus UI Depok',
                'kecamatan_kota': 'Pondok Cina, Beji, Kota Depok 16424',
                'kode_pos': '16424',
                'patokan': 'Perpustakaan Pusat UI (Crystal Knowledge) / Rektorat',
                'short_label': 'Depok',
            },
        ]

        for k in kategori_data:
            obj, created = Kategori.objects.get_or_create(
                slug=k['slug'],
                defaults={'nama': k['nama'], 'deskripsi': k['deskripsi']}
            )
            cat_obj, cat_created = Category.objects.get_or_create(
                id=obj.id,
                defaults={'name': k['nama']}
            )
            if created or cat_created:
                self.stdout.write(self.style.SUCCESS(f"Kategori '{obj.nama}' berhasil ditambahkan."))

        for loc in lokasi_data:
            obj, created = Lokasi.objects.get_or_create(
                nama_area=loc['nama_area'],
                defaults=loc
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Lokasi '{obj.nama_area}' berhasil ditambahkan."))

        self.stdout.write(self.style.SUCCESS('Selesai inisialisasi data awal Barang!'))
