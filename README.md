# Pinjemin

## Menjalankan secara lokal (Windows PowerShell)

Jalankan dari folder `D:\TugasKelompokPBP` yang berisi `env` dan `Pinjemin`:

```powershell
.\env\Scripts\python.exe -m pip install -r .\Pinjemin\requirements.txt
.\env\Scripts\python.exe .\Pinjemin\manage.py migrate
.\env\Scripts\python.exe .\Pinjemin\manage.py runserver
```

Buka http://127.0.0.1:8000/. Jika `env` belum tersedia, buat dengan `py -m venv env`. Menggunakan executable Python di dalam `env` memastikan dependensi yang benar terpakai tanpa perlu mengaktifkan environment. Gunicorn digunakan untuk deployment; pengembangan lokal Windows memakai `runserver`.

### Template bersama

`templates/base.html` menyediakan navbar, footer, notifikasi, dan blok `title`, `navigation`, `account_navigation`, `content`, `extra_css`, serta `extra_js`. Halaman baru dapat memakai:

```html
{% extends 'base.html' %}
{% block title %}Judul halaman — Pinjemin{% endblock %}
{% block content %}
<section>
  <h1>Judul halaman</h1>
</section>
{% endblock %}
```

Style dasar ada di `static/css/base.css`, dengan warna utama `#FFDE01`. Halaman `/` menggunakan `templates/home.html` sebagai contoh sederhana. Desain halaman dan fitur tiap modul dapat dikembangkan oleh anggota tim.

Pinjemin adalah platform web bagi sesama mahasiswa Universitas Indonesia untuk saling meminjamkan barang secara gratis maupun menyewakannya dengan harga terjangkau. Platform ini hadir untuk mengurangi penumpukan barang yang jarang dipakai, menekan pembelian berlebih, dan mendukung gaya hidup ramah lingkungan melalui sistem autentikasi *SSO UI* yang aman.

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
* **Penumpukan barang yang jarang dipakai:** Banyak barang seperti jas sidang, setrika, alat perkakas, atau koper hanya dipakai sesekali lalu dibiarkan menumpuk di kosan.
* **Pengeluaran boros untuk barang musiman:** Mahasiswa sering terpaksa membeli barang mahal padahal hanya dipakai satu atau dua kali.
* **Kekhawatiran saat meminjamkan barang:** Meminjamkan barang ke orang lain menimbulkan keraguan karena risiko barang rusak atau tidak dikembalikan. Login SSO UI dan riwayat pemesanan membuat transaksi lebih aman dan pertanggungjawabannya lebih jelas.
* **Kesulitan mencari barang di sekitar:** Mahasiswa sering tidak tahu bahwa tetangga kos atau teman di sekitar mereka memiliki barang yang sedang dicari. Fitur peta mempermudah pencarian barang terdekat.

### Keterkaitan dengan Sustainable Living
* **Mendorong budaya berbagi:** Membiasakan mahasiswa memanfaatkan barang yang sudah ada bersama-sama, bukan selalu membeli baru.
* **Memperpanjang masa pakai barang:** Barang yang dirawat dan dipakai bergantian tidak cepat menjadi sampah.
* **Mengurangi sampah konsumsi:** Berkurangnya pembelian barang baru membantu menekan sampah kemasan plastik dan emisi dari pengiriman barang.

---

## Anggota Kelompok dan Pembagian Tugas

| NPM | Nama | Modul |
| :---: | :--- | :--- |
| **2506632910** | Alphard Qodaruddin | Manajemen Transaksi |
| **2506587876** | Chelsea Stania Passikha | Manajemen Kategori |
| **2506615993** | I Nyoman Yadnya Suta Karmana | Manajemen Lokasi |
| **2506607272** | Fauzan Taqiy Santosa | Manajemen Barang |
| **2506620210** | Roisul Umam | Manajemen Pengguna |

---

## Rincian Modul dan CRUD

### 1. Manajemen Pengguna

**Penanggung jawab:** Roisul Umam
**Entitas:** Profil Pengguna
**Cakupan fitur:** Login dan logout melalui SSO UI mock API, pengelolaan profil, peralihan mode Peminjam dan Pemilik Barang, serta Pusat Bantuan berisi tutorial dan Kebijakan Privasi.

| Operasi | Penjelasan | Pelaku |
| :--- | :--- | :--- |
| **Create** | Saat pertama kali login melalui SSO UI, nama dan NPM diambil dari akun SSO UI dan disimpan sebagai profil. Pengguna melengkapi nomor WhatsApp untuk fitur komunikasi | Pengguna |
| **Read** | Menampilkan data profil berupa nama, NPM, nomor WhatsApp, dan mode aktif | Pengguna |
| **Update** | Mengubah nomor WhatsApp dan beralih antara mode Peminjam dan Pemilik Barang. Nama dan NPM tidak dapat diubah karena bersumber dari SSO UI | Pengguna |
| **Delete** | Menonaktifkan akun. Data pesanan tetap tersimpan sebagai riwayat | Pengguna |

### 2. Manajemen Kategori

**Penanggung jawab:** Chelsea Stania Passikha
**Entitas:** Kategori
**Cakupan fitur:** Halaman utama yang memuat banner edukasi, pilihan kategori, dan barang yang sering dipinjam, pencarian, filter harga atau lokasi, serta halaman detail barang.

| Operasi | Penjelasan | Pelaku |
| :--- | :--- | :--- |
| **Create** | Menambah kategori barang baru | Admin |
| **Read** | Menampilkan pilihan kategori pada halaman utama, filter pencarian, dan formulir barang | Semua pengguna |
| **Update** | Mengubah nama kategori | Admin |
| **Delete** | Menghapus kategori yang tidak lagi digunakan | Admin |

### 3. Manajemen Lokasi

**Penanggung jawab:** I Nyoman Yadnya Suta Karmana
**Entitas:** Titik Lokasi dengan jenis Lokasi Barang dan Titik Penjemputan
**Cakupan fitur:** Peta berbasis OpenStreetMap, deteksi lokasi pengguna, pencarian barang terdekat, dan tombol pengalihan ke WhatsApp pemilik barang setelah pesanan dibuat.

| Operasi | Penjelasan | Pelaku |
| :--- | :--- | :--- |
| **Create** | Menyimpan koordinat lokasi barang saat pemilik menandai posisi pada peta di formulir tambah barang, dan menentukan titik penjemputan ketika pesanan dibuat | Pemilik Barang |
| **Read** | Menampilkan pin barang pada peta, mencari barang terdekat dari lokasi pengguna, dan menampilkan titik penjemputan pada detail pesanan | Semua pengguna, kecuali titik penjemputan yang hanya untuk Peminjam dan Pemilik pada pesanan terkait |
| **Update** | Menggeser pin atau mengubah alamat lokasi barang, serta mengubah titik penjemputan selama pesanan belum selesai | Pemilik Barang |
| **Delete** | Menghapus lokasi barang bersamaan dengan barangnya, dan menonaktifkan titik penjemputan apabila pesanan dibatalkan | Pemilik Barang dan sistem |

### 4. Manajemen Barang

**Penanggung jawab:** Fauzan Taqiy Santosa
**Entitas:** Barang
**Cakupan fitur:** Formulir pengelolaan barang, moderasi postingan oleh Admin, dan dashboard yang menampilkan barang yang sedang dipinjam, pesanan masuk, serta daftar barang yang ditawarkan.

| Operasi | Penjelasan | Pelaku |
| :--- | :--- | :--- |
| **Create** | Menambah barang melalui formulir yang memuat nama, foto, deskripsi, kategori, jenis gratis atau sewa, tarif per hari, dan lokasi | Pemilik Barang |
| **Read** | Menampilkan daftar barang milik sendiri, sedangkan Admin dapat melihat seluruh barang di platform | Pemilik Barang dan Admin |
| **Update** | Memperbarui data barang, termasuk tarif dan ketersediaan | Pemilik Barang |
| **Delete** | Menghapus barang yang tidak sedang dipinjam. Admin menghapus postingan yang melanggar aturan | Pemilik Barang dan Admin |

### 5. Manajemen Transaksi

**Penanggung jawab:** Alphard Qodaruddin
**Entitas:** Pesanan beserta data Pembayaran
**Cakupan fitur:** Formulir checkout, perhitungan total biaya, riwayat pesanan, dan pembayaran melalui payment gateway mock API.

| Operasi | Penjelasan | Pelaku |
| :--- | :--- | :--- |
| **Create** | Mengisi formulir checkout berupa tanggal peminjaman dan durasi sewa. Sistem menghitung total biaya, yaitu tarif per hari dikalikan durasi, lalu membuat pesanan berstatus Menunggu Pembayaran beserta transaksi pembayarannya. Barang gratis langsung berstatus Dikonfirmasi tanpa tagihan | Peminjam |
| **Read** | Menampilkan riwayat pesanan, rincian biaya, dan status pembayaran. Pemilik melihat pesanan masuk melalui dashboard | Peminjam dan Pemilik Barang |
| **Update** | Mengubah tanggal atau durasi selama pesanan berstatus Menunggu Pembayaran. Status berubah mengikuti alur Menunggu Pembayaran, Dikonfirmasi setelah pembayaran berhasil, dan Selesai setelah masa peminjaman berakhir | Peminjam dan sistem |
| **Delete** | Membatalkan pesanan sebelum masa peminjaman dimulai. Status berubah menjadi Dibatalkan dan pembayaran yang belum selesai ikut dibatalkan | Peminjam |

---

## Integrasi API

1. **OpenStreetMap API:** Public API yang digunakan untuk membaca titik koordinat lokasi, mencari barang dalam jarak terdekat, dan menampilkan lokasi penjemputan.
2. **SSO UI Service:** Mock API yang digunakan untuk simulasi sistem login mahasiswa Universitas Indonesia agar identitas pengguna terverifikasi.
3. **Payment Gateway:** Mock API yang digunakan untuk simulasi sistem pembayaran transaksi sewa secara langsung.

---

## Peran Pengguna

| Peran | Hak Akses |
| :--- | :--- |
| **Tamu** | Pengguna yang belum login. Hanya dapat melihat halaman utama, mencari barang, dan melihat informasi produk secara terbatas. |
| **Peminjam** | Mahasiswa UI yang sudah login. Dapat memesan barang sewa atau pinjam gratis, melihat titik temu, memantau riwayat pesanan, dan menghubungi pemilik lewat WhatsApp. |
| **Pemilik Barang** | Pengguna yang menyewakan atau meminjamkan barang. Dapat menambah, mengedit, dan menghapus barang miliknya, serta melihat pesanan masuk. |
| **Admin** | Memantau seluruh aktivitas platform, mengelola kategori barang, dan menghapus postingan barang yang melanggar aturan. |

## LINK FIGMA 
https://www.figma.com/design/cIcomyuXpNiIPvk3Wa4gwo/Design-System?node-id=0-1&p=f&t=STwAfPD95yE7Ky2X-0
