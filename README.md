(Send di wa untuk instalasi fullnya)
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
**Cakupan fitur:** Login dan logout melalui SSO UI mock API, pembuatan profil dari nama dan NPM SSO, serta pengelolaan nomor WhatsApp. Pengguna dapat melihat profil, beralih antara mode Peminjam dan Pemilik Barang, serta menonaktifkan akun tanpa menghapus riwayat pesanan. Tersedia Pusat Bantuan berisi tutorial dan Kebijakan Privasi.

| Operasi | Penjelasan | Pelaku |
| :--- | :--- | :--- |
| **Create** | Saat pertama kali login melalui SSO UI, nama dan NPM diambil dari akun SSO UI dan disimpan sebagai profil. Pengguna melengkapi nomor WhatsApp untuk fitur komunikasi | Pengguna |
| **Read** | Menampilkan data profil berupa nama, NPM, nomor WhatsApp, dan mode aktif | Pengguna |
| **Update** | Mengubah nomor WhatsApp dan beralih antara mode Peminjam dan Pemilik Barang. Nama dan NPM tidak dapat diubah karena bersumber dari SSO UI | Pengguna |
| **Delete** | Menonaktifkan akun (soft delete) jika tidak ada transaksi berjalan. Akun tidak dapat digunakan dan profil disembunyikan, tetapi riwayat pesanan tetap tersimpan. | Pengguna |

### 2. Manajemen Kategori

**Penanggung jawab:** Chelsea Stania Passikha
**Entitas:** Kategori
**Cakupan fitur:** Pengelolaan kategori untuk mengelompokkan barang dan menyediakan pilihan pada formulir unggah serta filter pencarian. Halaman utama menampilkan banner edukasi, pilihan kategori, dan barang yang sering dipinjam. Pengguna dapat mencari barang, menyaring berdasarkan kategori, harga, atau lokasi, serta melihat informasi lengkap pada halaman detail barang.

| Operasi | Penjelasan | Pelaku |
| :--- | :--- | :--- |
| **Create** | Menambah kategori barang baru | Admin |
| **Read** | Menampilkan pilihan kategori pada halaman utama, filter pencarian, dan formulir barang | Semua pengguna |
| **Update** | Mengubah nama kategori | Admin |
| **Delete** | Menghapus kategori yang tidak lagi digunakan | Admin |

### 3. Manajemen Lokasi

**Penanggung jawab:** I Nyoman Yadnya Suta Karmana  
**Entitas:** Lokasi Penjemputan 
**Cakupan fitur:** Pemilik Barang dapat memilih lokasi yang pernah disimpan, menambahkan lokasi baru, serta mengedit atau menghapusnya dari daftar lokasi tersimpan. Setiap lokasi memuat label, alamat, dan koordinat. Menghapus lokasi dari daftar tidak menghapus lokasi yang sudah tercatat pada barang atau pesanan. Lokasi penjemputan pada barang masih dapat diedit ketika pesanan belum disetujui oleh Pemilik Barang dan terkunci setelah disetujui. Peta berbasis OpenStreetMap membantu Peminjam mencari barang terdekat berdasarkan lokasi real-time dan melihat detail lokasi penjemputan setelah membuat pesanan.

| Operasi | Penjelasan | Pelaku |
| :--- | :--- | :--- |
| **Create** | Menambahkan lokasi penjemputan untuk disimpan dan dipilih saat mengunggah barang. | Pemilik Barang |
| **Read** | Melihat daftar lokasi tersimpan. Peminjam melihat detail lokasi penjemputan pada pesanannya. | Pemilik Barang dan Peminjam terkait |
| **Update** | Mengubah label, alamat, atau koordinat dalam daftar lokasi tersimpan. Perubahan tidak otomatis mengubah lokasi pada barang atau pesanan. Lokasi pada barang dapat diubah secara terpisah selama belum ada pesanan yang disetujui. | Pemilik Barang |
| **Delete** | Menghapus lokasi dari daftar lokasi tersimpan agar tidak muncul lagi sebagai pilihan saat mengunggah barang. Lokasi yang sudah tercatat pada barang atau pesanan tetap tersimpan. | Pemilik Barang |

**Fitur lokasi untuk Peminjam:**

- Melihat posisi barang pada peta dan jaraknya dari lokasi real-time Peminjam.
- Mencari barang terdekat berdasarkan posisi Peminjam saat itu.
- Melihat detail lokasi penjemputan setelah membuat pesanan. Detail tersebut hanya dapat diakses oleh Peminjam dan Pemilik Barang pada pesanan terkait.
- Menghubungi Pemilik Barang melalui tombol pengalihan ke WhatsApp setelah pesanan dibuat.


### 4. Manajemen Barang

**Penanggung jawab:** Fauzan Taqiy Santosa
**Entitas:** Barang
**Cakupan fitur:** Pemilik Barang dapat menambahkan barang beserta foto, deskripsi, kategori, jenis gratis atau sewa, tarif, dan lokasi penjemputan. Dashboard menampilkan daftar barang, barang yang sedang dipinjam, dan pesanan masuk. Data barang masih dapat diedit selama pesanan belum disetujui oleh Pemilik Barang dan terkunci setelah disetujui. Barang hanya dapat dihapus jika belum dipesan.

| Operasi | Penjelasan | Pelaku |
| :--- | :--- | :--- |
| **Create** | Menambahkan barang dengan mengisi nama, foto, deskripsi, kategori, jenis gratis atau sewa, tarif per hari, dan memilih lokasi penjemputan. | Pemilik Barang |
| **Read** | Melihat daftar dan detail barang milik sendiri. | Pemilik Barang |
| **Update** | Mengubah data barang selama belum ada pesanan yang disetujui. | Pemilik Barang |
| **Delete** | Menghapus barang selama belum dipesan. | Pemilik Barang |

### 5. Manajemen Transaksi

**Penanggung jawab:** Alphard Qodaruddin
**Entitas:** Pesanan beserta data Pembayaran
**Cakupan fitur:** Pembuatan pesanan melalui checkout dengan memilih tanggal dan durasi peminjaman, perhitungan biaya sewa, serta pembayaran melalui payment gateway mock API. Peminjam dapat melihat riwayat, rincian biaya, dan status pesanan, mengubah jadwal selama Menunggu Pembayaran, serta membatalkan sebelum masa peminjaman dimulai. Pemilik Barang dapat melihat pesanan masuk melalui dashboard.

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
| **Admin** | Memantau seluruh aktivitas platform, mengelola kategori barang,  |

## LINK FIGMA 
https://www.figma.com/design/cIcomyuXpNiIPvk3Wa4gwo/Design-System?node-id=0-1&p=f&t=STwAfPD95yE7Ky2X-0
