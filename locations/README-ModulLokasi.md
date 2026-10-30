# Manajemen Lokasi

**Nama:** I Nyoman Yadnya Suta Karmana<br>
**NPM:** 2506615993<br>
**Bagian:** Manajemen Lokasi (`locations`)

Modul ini mengelola riwayat lokasi penjemputan milik pemilik barang, membantu pemilik memilih titik lokasi untuk barang, dan menyediakan informasi lokasi yang sesuai hak akses bagi peminjam.

## Alur fitur

1. Pemilik membuka **Akun Saya → Lokasi Tersimpan** atau pemilih lokasi saat menambah/mengedit barang.
2. Pemilik memilih lokasi dari riwayat atau menambahkan lokasi dengan label, alamat, dan koordinat. Titik dapat ditentukan dengan klik/geser pin di peta, lokasi perangkat, atau koordinat manual.
3. Saat lokasi digunakan pada barang, aplikasi membuat salinan lokasi barang. Mengedit atau menghapus entri riwayat tidak mengubah lokasi yang telah disalin ke barang.
4. Saat pesanan diajukan, lokasi barang disalin lagi ke snapshot pesanan. Perubahan lokasi barang berikutnya tidak mengubah snapshot pesanan tersebut.
5. Peminjam dapat memberi izin lokasi perangkat untuk melihat barang di radius 1 atau 2 km. Halaman publik hanya menampilkan area perkiraan; detail titik penjemputan pada halaman pesanan tersedia untuk pemilik dan peminjam yang terkait.

## Operasi CRUD lokasi tersimpan

| Operasi | Implementasi |
| --- | --- |
| **Create** | Pemilik mengisi label, alamat, latitude, dan longitude melalui formulir peta. Server memvalidasi data, menetapkan pemilik dari sesi login (bukan dari input klien), lalu menyimpan lokasi. |
| **Read** | Pemilik melihat lokasi aktif miliknya pada halaman Lokasi Tersimpan atau pemilih lokasi. Endpoint daftar hanya mengembalikan lokasi yang `owner`-nya adalah akun aktif. |
| **Update** | Pemilik mengubah label, alamat, dan/atau koordinat. Server mencari lokasi berdasarkan ID sekaligus pemilik dan status aktif. Perubahan hanya berlaku pada entri riwayat; snapshot barang dan pesanan tidak ikut berubah. |
| **Delete** | Lokasi dihapus secara lunak dengan mengubah `is_active` menjadi `False`. Lokasi tidak muncul lagi di daftar dan pilihan berikutnya, sedangkan data pada barang dan pesanan tetap ada. UI memperbarui daftar tanpa reload dan mengembalikan baris jika permintaan server gagal. |

Semua operasi perubahan memerlukan login dan perlindungan CSRF. Pengguna tidak dapat membaca atau mengubah lokasi milik akun lain. Koordinat divalidasi pada form/model dengan rentang latitude -90 sampai 90 dan longitude -180 sampai 180.

## API dan layanan peta

| API/layanan | Kegunaan dalam aplikasi |
| --- | --- |
| **OpenStreetMap tiles** (`OSM_TILE_URL`) | Menampilkan peta pada pemilih lokasi, peta barang terdekat, detail barang, dan detail pesanan. Atribusi OpenStreetMap ditampilkan pada peta. |
| **Nominatim Reverse API** (`NOMINATIM_REVERSE_URL`) | Mengubah koordinat lokasi perangkat menjadi nama area untuk navbar. Aplikasi mengirim koordinat yang dibulatkan, hanya menyimpan label area pada cache 24 jam, menggunakan timeout dan pembatasan permintaan bersama, serta mengembalikan pesan yang dapat dicoba ulang jika layanan gagal atau membatasi permintaan. Ini bukan layanan pencarian alamat lengkap. |
| **Browser Geolocation API** | Meminta izin browser untuk memperoleh posisi perangkat pada pencarian barang terdekat dan permintaan rute. Koordinat posisi peminjam digunakan sementara untuk menghitung jarak atau meminta rute. Fitur membutuhkan HTTPS atau localhost dan izin lokasi. |
| **Nearby Items API** (`GET /barang/api/terdekat/?latitude=...&longitude=...&radius=1`) | Mengembalikan barang aktif dalam radius 1 atau 2 km, diurutkan dari jarak terdekat. Endpoint memakai bounding box untuk mempersempit kandidat di database lalu menghitung jarak dengan rumus Haversine. Koordinat pin publik dibulatkan agar menunjukkan area perkiraan. |
| **OSRM Route API** (`OSRM_ROUTE_URL`) | Meminta rute jalan kendaraan dari lokasi perangkat ke koordinat snapshot pesanan. Respons OSRM menyediakan geometri rute, jarak, durasi, dan langkah perjalanan untuk digambar pada peta. Google Maps disediakan sebagai tautan alternatif. |

### Catatan algoritma rute

Pada kode saat ini, perhitungan jarak barang terdekat memakai **Haversine**, sedangkan rute jalan diminta dari **OSRM Route API**. Aplikasi tidak mengimplementasikan algoritma Dijkstra sendiri atau mengirim graf jalan untuk menghitung rute secara lokal. Karena itu, dokumentasi ini menyebut OSRM sebagai layanan perutean dan tidak mengklaim Dijkstra sebagai algoritma yang ditulis di modul.

## Endpoint CRUD riwayat

| Method dan URL | Fungsi | Hak akses |
| --- | --- | --- |
| `GET /lokasi/api/penjemputan/` | Membaca riwayat aktif milik akun sendiri | Login |
| `POST /lokasi/api/penjemputan/` | Membuat lokasi tersimpan | Login dan CSRF |
| `PATCH /lokasi/api/penjemputan/<id>/` | Mengubah lokasi tersimpan milik sendiri | Login dan CSRF |
| `DELETE /lokasi/api/penjemputan/<id>/` | Menonaktifkan lokasi dari riwayat (soft delete) | Login dan CSRF |
| `POST /lokasi/terkini/` | Mendapatkan nama area dari koordinat perangkat melalui Nominatim | CSRF; pembatasan permintaan layanan geocoding |

## File utama

- `locations/models.py`: model `PickupLocation` dan cache geocoding.
- `locations/forms.py`: validasi label, alamat, dan koordinat.
- `locations/views.py`: endpoint riwayat, halaman lokasi tersimpan, dan pencarian nama area.
- `locations/services.py`: konteks peta, reverse geocoding, cache, dan pembatasan penggunaan Nominatim.
- `templates/locations/picker.html` dan `templates/locations/saved.html`: UI pemilih dan pengelolaan riwayat.
- `static/js/pickup-location.js`: interaksi peta dan CRUD tanpa reload.
- Integrasi salinan lokasi barang berada di `barang/services.py`; snapshot lokasi dan peta pesanan berada di `transaksi/services.py` dan `transaksi/views.py`.

## Validasi dan penggunaan AI

Saya memeriksa alur dan hak akses melalui pengujian untuk CRUD, kepemilikan lokasi, CSRF, validasi koordinat, snapshot barang/pesanan, serta pembatasan detail lokasi. Saya menggunakan AI sebagai alat bantu, lalu meninjau dan memvalidasi kembali hasilnya melalui kode dan pengujian.
