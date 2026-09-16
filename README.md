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

## Rincian Modul Aplikasi

### 1. Autentikasi, Profil, dan Pusat Bantuan
* **Penanggung Jawab:** Roisul Umam
* **Autentikasi dan Profil:** Login menggunakan akun SSO UI, manajemen data profil, dan tombol untuk beralih ke mode penjual atau penyewa barang.
* **Tutorial dan Bantuan:** Panduan cara meminjam dan menyewakan barang, Pusat Bantuan, serta Kebijakan Privasi.

### 2. Peta, Titik Lokasi, dan Komunikasi
* **Penanggung Jawab:** I Nyoman Yadnya Suta Karmana
* **Peta dan Lokasi:** Menampilkan peta untuk mendeteksi lokasi pengguna, menyimpan titik koordinat barang, mencari barang terdekat, dan menentukan lokasi penjemputan barang.
* **Komunikasi:** Tombol pengalihan langsung ke WhatsApp pemilik barang setelah pesanan dibuat.

### 3. Halaman Utama, Kategori, dan Detail Barang
* **Penanggung Jawab:** Chelsea Stania Passikha
* **Halaman Utama dan Pencarian:** Halaman depan dengan banner edukasi, pilihan kategori, daftar barang yang sering dipinjam, kolom pencarian, dan filter harga atau lokasi.
* **Detail Barang:** Informasi lengkap barang mulai dari foto, deskripsi, tarif sewa per hari atau label pinjam gratis, lokasi barang, dan kontak pemilik.

### 4. Manajemen Barang dan Dashboard
* **Penanggung Jawab:** Fauzan Taqiy Santosa
* **Manajemen Barang:** Formulir untuk menambah, memperbarui, dan menghapus barang yang ingin dipinjamkan atau disewakan.
* **Dashboard:** Halaman panel untuk memantau barang yang sedang dipinjam dan mengelola daftar barang yang sedang ditawarkan.

### 5. Checkout, Transaksi, dan Pembayaran
* **Penanggung Jawab:** Alphard Qodaruddin
* **Checkout:** Formulir pemesanan barang dengan pilihan tanggal peminjaman, durasi sewa, dan rincian total biaya.
* **Pembayaran:** Integrasi proses pembayaran untuk transaksi sewa barang. Untuk barang pinjaman gratis, transaksi langsung berhasil tanpa tagihan.

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