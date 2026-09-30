# Pinjemin

Pinjemin adalah platform web bagi sesama mahasiswa Universitas Indonesia untuk dapat saling meminjamkan barang secara gratis maupun menyewakannya dengan harga terjangkau. Platform ini hadir untuk mengurangi penumpukan barang yang jarang dipakai, menekan pembelian berlebih, dan mendukung gaya hidup ramah lingkungan melalui sistem autentikasi *SSO UI* yang aman.
---

## Tema Proyek

* **Tema Utama:** Sustainable Living
* **Subtema:** Collaborative Consumption & Circular Economy

---

## Latar Belakang dan Relevansi Tema

### Target Pengguna
Pengguna utama Pinjemin adalah warga kampus Universitas Indonesia:
* **Mahasiswa umum:** Mahasiswa yang butuh barang untuk keperluan kuliah, acara organisasi, atau alat kosan untuk jangka pendek tanpa perlu membeli baru.
* **Pemilik barang:** Mahasiswa yang memiliki barang menganggur di kosan dan ingin menyewakannya untuk tambahan uang saku atau meminjamkannya secara sukarela.
* **Pengurus organisasi atau panitia acara:** Mahasiswa yang memerlukan perlengkapan kegiatan kampus seperti proyektor, megafon, kabel rol, atau tenda.

### Permasalahan yang Diselesaikan
Aplikasi ini menyelesaikan beberapa persoalan nyata:
* **Penumpukan barang yang jarang dipakai:** Banyak barang seperti jas sidang, setrika, alat perkakas, atau koper hanya dipakai sesekali lalu dibiarkan menumpuk di kosan.
* **Pengeluaran boros untuk barang musiman:** Mahasiswa sering terpaksa membeli barang mahal padahal cuma dipakai satu atau dua kali.
* **Kekhawatiran saat meminjamkan barang:** Meminjamkan barang ke orang lain sering menimbulkan rasa ragu karena risiko barang rusak atau tidak dikembalikan. Sistem login SSO UI dan riwayat pemesanan membuat transaksi lebih aman dan jelas pertanggungjawabannya.
* **Kesulitan mencari barang di sekitar:** Mahasiswa sering tidak tahu bahwa tetangga kos atau teman di sekitar mereka sebenarnya memiliki barang yang sedang dicari. Fitur peta mempermudah pencarian barang terdekat.

### Keterkaitan dengan Sustainable Living
Pinjemin mendukung gaya hidup berkelanjutan dengan cara:
* **Mendorong budaya berbagi:** Membiasakan mahasiswa untuk memanfaatkan barang yang sudah ada bersama-sama daripada selalu membeli baru.
* **Memperpanjang masa pakai barang:** Barang yang dirawat dan dipakai bergantian tidak cepat terbuang menjadi sampah rongsokan.
* **Mengurangi sampah konsumsi:** Berkurangnya pembelian barang baru membantu menekan sampah kemasan plastik dan emisi dari pengiriman barang.

---

## Anggota Kelompok dan Pembagian Tugas

| NPM | Nama | Modul yang Dikerjakan |
| :---: | :--- | :--- |
| **2506632910** | Alphard Qodaruddin | Checkout, Transaksi, dan Pembayaran |
| **2506587876** | Chelsea Stania Passikha | Halaman Utama, Kategori, dan Detail Barang |
| **2506615993** | I Nyoman Yadnya Suta Karmana | Peta, Titik Lokasi, dan Komunikasi |
| **2506607272** | Fauzan Taqiy Santosa | Manajemen Barang dan Dashboard |
| **2506620210** | Roisul Umam | Autentikasi, Profil, dan Pusat Bantuan |

---

## Rincian Modul & CRUD Aplikasi

### 1. Autentikasi, Profil, dan Pusat Bantuan

**Penanggung jawab:** Roisul Umam
**Ruang lingkup:** Login SSO UI, pengelolaan profil, peralihan mode Peminjam dan Pemilik Barang, serta konten bantuan.

| Entitas | Create | Read | Update | Delete |
| :--- | :--- | :--- | :--- | :--- |
| Profil Pengguna | Saat pertama kali login melalui SSO UI, nama dan NPM diambil dari akun SSO UI dan disimpan sebagai profil. Pengguna kemudian melengkapi nomor WhatsApp yang dibutuhkan untuk fitur komunikasi | Menampilkan data profil pengguna yang sedang login | Mengubah nomor WhatsApp dan beralih antara mode Peminjam dan Pemilik Barang. Nama dan NPM tidak dapat diubah karena bersumber dari SSO UI | - |
| Sesi Login | Pengguna login dengan akun SSO UI (mock API), lalu sistem membuat sesi login | Memeriksa status login untuk menentukan apakah pengguna berstatus Tamu atau sudah terautentikasi | - | Logout mengakhiri sesi login |
| Tutorial, Pusat Bantuan, dan Kebijakan Privasi | - (konten statis) | Menampilkan panduan cara meminjam dan menyewakan barang, Pusat Bantuan, serta Kebijakan Privasi | - | - |

### 2. Halaman Utama, Kategori, dan Detail Barang

**Penanggung jawab:** Chelsea Stania Passikha
**Ruang lingkup:** Tampilan halaman depan, pengelolaan kategori, pencarian dan filter, serta halaman detail barang.

| Entitas | Create | Read | Update | Delete |
| :--- | :--- | :--- | :--- | :--- |
| Kategori | Admin menambah kategori barang baru | Menampilkan pilihan kategori pada halaman utama dan pada formulir barang | Admin mengubah nama kategori | Admin menghapus kategori |
| Halaman Utama | - (banner edukasi berupa konten statis) | Menampilkan banner edukasi, pilihan kategori, dan daftar barang yang sering dipinjam (diurutkan dari jumlah pesanan terbanyak) | - | - |
| Pencarian dan Filter | - | Mencari barang berdasarkan kata kunci pada kolom pencarian, lalu menyaring hasil berdasarkan rentang harga atau lokasi | - | - |
| Detail Barang | - (data barang dibuat pada modul Manajemen Barang) | Menampilkan foto, deskripsi, tarif sewa per hari atau label pinjam gratis, lokasi barang, dan kontak pemilik. Kontak pemilik hanya tampil bagi pengguna yang sudah login | - | - |

### 3. Peta, Titik Lokasi, dan Komunikasi

**Penanggung jawab:** I Nyoman Yadnya Suta Karmana
**Ruang lingkup:** Peta berbasis OpenStreetMap, penyimpanan koordinat barang, pencarian barang terdekat, penentuan titik penjemputan, dan pengalihan ke WhatsApp.

| Entitas | Create | Read | Update | Delete |
| :--- | :--- | :--- | :--- | :--- |
| Koordinat Barang | Pemilik menandai lokasi barang pada peta di formulir tambah barang, lalu koordinat (latitude dan longitude) disimpan bersama data barang | Menampilkan pin barang pada peta dan mencari barang terdekat dari lokasi pengguna | Pemilik menggeser pin atau mengubah lokasi ketika barang berpindah tempat | Koordinat dihapus bersamaan dengan barang yang bersangkutan |
| Titik Penjemputan | Pemilik menentukan titik penjemputan pada peta ketika pesanan dibuat. Secara bawaan, titik ini sama dengan koordinat barang | Peminjam dan Pemilik melihat titik penjemputan pada detail pesanan | Pemilik mengubah titik penjemputan selama pesanan belum selesai | Titik penjemputan dinonaktifkan apabila pesanan dibatalkan |
| Lokasi Pengguna | Mendeteksi lokasi pengguna melalui izin lokasi peramban saat fitur peta digunakan | Menampilkan posisi pengguna dan menghitung jarak ke barang | - (lokasi dideteksi ulang setiap sesi dan tidak disimpan permanen) | - |
| Tombol WhatsApp | - (tombol dibentuk otomatis setelah pesanan dibuat) | Mengalihkan Peminjam langsung ke WhatsApp pemilik menggunakan nomor pada profil pemilik | - | - |

### 4. Manajemen Barang dan Dashboard

**Penanggung jawab:** Fauzan Taqiy Santosa
**Ruang lingkup:** Formulir pengelolaan barang oleh pemilik, moderasi oleh Admin, dan dashboard pemantauan.

| Entitas | Create | Read | Update | Delete |
| :--- | :--- | :--- | :--- | :--- |
| Barang | Pemilik menambah barang melalui formulir yang memuat nama, foto, deskripsi, kategori, jenis (gratis atau sewa), tarif per hari, dan lokasi | Pemilik melihat daftar barang miliknya. Admin melihat seluruh barang di platform | Pemilik memperbarui data barang, termasuk tarif dan ketersediaan | Pemilik menghapus barang miliknya yang tidak sedang dipinjam. Admin menghapus postingan yang melanggar aturan |
| Dashboard | - | Menampilkan barang milik pemilik yang sedang dipinjam orang lain, pesanan masuk beserta statusnya, dan daftar barang yang sedang ditawarkan | - | - |

Pengelolaan daftar barang pada dashboard dilakukan melalui operasi CRUD entitas Barang di atas.

### 5. Checkout, Transaksi, dan Pembayaran

**Penanggung jawab:** Alphard Qodaruddin
**Ruang lingkup:** Formulir pemesanan, perhitungan biaya, riwayat pesanan, dan simulasi pembayaran.

| Entitas | Create | Read | Update | Delete |
| :--- | :--- | :--- | :--- | :--- |
| Pesanan | Peminjam mengisi formulir checkout berupa tanggal peminjaman dan durasi sewa. Sistem menghitung total biaya (tarif per hari dikalikan durasi), lalu membuat pesanan berstatus Menunggu Pembayaran. Barang gratis langsung berstatus Dikonfirmasi | Peminjam melihat riwayat pesanannya beserta rincian biaya. Pemilik melihat pesanan masuk melalui Dashboard | Status pesanan berubah mengikuti alur: Menunggu Pembayaran, Dikonfirmasi (setelah pembayaran berhasil), dan Selesai (setelah masa peminjaman berakhir) | Peminjam membatalkan pesanan sebelum masa peminjaman dimulai. Status berubah menjadi Dibatalkan |
| Pembayaran | Sistem membuat transaksi melalui payment gateway (mock API) untuk barang sewa. Barang pinjaman gratis tidak memiliki tagihan dan langsung berhasil | Menampilkan status (Menunggu, Berhasil, atau Gagal) dan rincian pembayaran | Status diperbarui sesuai respons payment gateway | - |

---

## Integrasi API

1. **OpenStreetMap API (Public API):** Digunakan untuk membaca titik koordinat lokasi, mencari barang dalam jarak terdekat, dan menampilkan lokasi penjemputan.
2. **SSO UI Service (Mock API):** Digunakan untuk simulasi sistem login mahasiswa Universitas Indonesia agar identitas pengguna terverifikasi.
3. **Payment Gateway (Mock API):** Digunakan untuk simulasi sistem pembayaran transaksi sewa secara langsung.

---

## Peran Pengguna

| Peran | Hak Akses |
| :--- | :--- |
| **Tamu** | Pengguna yang belum login. Hanya bisa melihat halaman utama, mencari barang, dan melihat info produk secara terbatas. |
| **Peminjam** | Mahasiswa UI yang sudah login. Dapat memesan barang sewa atau pinjam gratis, melihat titik temu, memantau riwayat pesanan, dan menghubungi pemilik lewat WhatsApp. |
| **Pemilik Barang** | Pengguna yang menyewakan atau meminjamkan barang. Bisa menambah, mengedit, dan menghapus daftar barang miliknya, serta melihat pesanan masuk. |
| **Admin** | Memantau seluruh aktivitas platform, mengelola kategori barang, dan menghapus postingan barang yang melanggar aturan. |