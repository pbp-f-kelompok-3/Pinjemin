# Pinjemin

Pinjemin adalah aplikasi berbagi, meminjam, dan menyewakan barang untuk warga kampus. Proyek ini dibuat sebagai penerapan pengembangan web Django dalam tema *Sustainable Living*.

## Menjalankan aplikasi secara lokal (Penting Aseli)

Pastikan Python dan `pip` tersedia. Jalankan perintah berikut dari folder proyek yang berisi `manage.py`.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Di Linux atau macOS, perintah aktivasi virtual environment adalah `source .venv/bin/activate`. Konfigurasi pengembangan menggunakan SQLite secara default; `PRODUCTION` tidak perlu diaktifkan untuk menjalankan aplikasi lokal. Buka `http://127.0.0.1:8000/` setelah server berjalan. Geolocation browser membutuhkan izin lokasi dan konteks aman seperti `localhost` atau HTTPS.

Untuk menjalankan pengujian, gunakan `python manage.py test`. Beberapa pengujian modul lokasi dapat dijalankan dengan `python manage.py test locations barang.test_pickup transaksi.tests`. Jangan memasukkan secret produksi, kredensial database, atau API key ke README maupun Git.

Dalam pengerjaan ingat selalu pull origin main untuk memastikan gaada file yang conflict

### Daftar Migrasi Penting

Setelah melakukan pull versi terbaru, pastikan untuk selalu menjalankan `python manage.py migrate`. Berikut beberapa migrasi penting yang dibuat dan diterapkan pada proyek:

1. **`barang`**:
   - `0003_alter_barang_kategori`: Menyesuaikan relasi foreign key `kategori` pada model `Barang` agar merujuk ke model `Category` terpusat dari modul `categories`.
2. **`transaksi`**:
   - `0003_ulasan`: Menambahkan model dan tabel `Ulasan` (OneToOne ke `Pesanan`, ForeignKey ke `peminjam`, `pemilik`, `barang`, rating bintang 1–5, dan komentar) untuk sistem ulasan peminjaman serta reputasi pemilik.
   - `0004_pesanan_diterima_at`: Menambahkan field timestamp pencatatan saat serah terima barang dikonfirmasi oleh peminjam.
3. **`accounts`**:
   - `0002_profile_deactivated_at`: Menambahkan field penanda waktu saat akun dinonaktifkan (soft-delete).
4. **`help_center`**:
   - `0001_initial`: Inisialisasi model dan tabel pusat bantuan (pertanyaan FAQ & tiket kendala pengguna).
5. **`categories`**:
   - `0003_seed_categories`: Data awal (*seeding*) kategori barang kampus.

## Simulasi flow pembayaran Midtrans

Payment gateway Midtrans yang digunakan di proyek ini adalah versi sandbox, jadi semua transaksi bersifat simulasi. Jangan gunakan kredensial dan uang asli untuk pengujian lokal ini.
Cara menguji alur pembayaran:
1. Pilih barang sewa dan lanjutkan ke checkout.
2. Pilih metode pembayaran QRIS.
3. Salin alamat gambar QRIS yang muncul (klik kanan gambar QRIS -> copy image address URL).
4. Buka link berikut di browser: [Midtrans QRIS Simulator](https://simulator.sandbox.midtrans.com/v2/qris/index).
5. Tempelkan alamat gambar QRIS yang disalin ke halaman simulator untuk menyelesaikan pembayaran. Transaksi akan dianggap berhasil secara otomatis di halaman pembayaran pinjemin (jika statusnya masih belum dibayar, klik tombol cek status pembayaran).

Untuk Refund, masih berupa simulasi saja. Ketika pesanan dibatalkan maka status pembayaran akan berubah menjadi dibatalkan dan uang disimulasikan dikembalikan ke akun pembayaran. Hal ini dikarenakan Midtrans sandbox tidak benar-benar memproses pembayaran, jadi tidak ada uang sungguhan yang berpindah tangan.

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

**Penerimaan barang dan pendapatan simulasi:**

- Pemilik memantau pesanan melalui `/transaksi/masuk/`, termasuk status pembayaran dan identitas peminjam terkait.
- Setelah pembayaran terverifikasi (atau langsung untuk barang gratis), peminjam mengonfirmasi **Barang sudah diterima** setelah serah terima. Konfirmasi ini menghentikan pembatalan pesanan dan mencatat waktu penerimaan.
- Halaman `/transaksi/pendapatan/` menampilkan biaya sewa yang masih menunggu serah terima serta pendapatan dari barang yang sudah diterima. Konfirmasi berulang tidak menggandakan nominal. Semua pendapatan adalah simulasi tanpa transfer rekening/GoPay.
- Pesanan selesai setelah pemilik mengonfirmasi **Barang dikembalikan**. Lewatnya jadwal tidak otomatis membuktikan pengembalian barang. Barang tetap terkunci sampai pengembalian dikonfirmasi.
- Data contoh lokal dapat dibuat dengan `python manage.py seed_demo_transaksi --owner USERNAME_PEMILIK`, memakai username pemilik yang sudah bisa login. Perintah tidak mengubah password atau hak akses akun pemilik. Akun demo tambahan adalah pengguna biasa, tanpa akses staff/admin. Lima pesanan contoh mencakup belum dibayar, sudah dibayar, diterima, dikembalikan, dan dibatalkan. Pembayaran contoh ini tidak dikirim ke Midtrans. Perintah ditolak jika `PRODUCTION=True`.
---

## Integrasi API

1. **OpenStreetMap tiles:** Menampilkan latar peta dan atribusi. Koordinat perangkat diperoleh dari Browser Geolocation API, bukan dari tile OpenStreetMap.
2. **Nominatim Reverse API:** Mengubah koordinat perangkat yang dibulatkan menjadi nama wilayah untuk navbar; hasil label area di-cache dan permintaan ke layanan dibatasi.
3. **Nearby Items API:** Endpoint aplikasi `/barang/api/terdekat/` menerima koordinat dan radius, menyaring barang aktif, lalu mengurutkan kandidat berdasarkan jarak Haversine. Pin publik memakai koordinat perkiraan.
4. **OSRM Route API:** Layanan routing berbasis jaringan jalan OpenStreetMap untuk rute kendaraan pada detail pesanan. Aplikasi menampilkan geometri, jarak, estimasi waktu, dan langkah perjalanan; Google Maps tersedia sebagai alternatif.
5. **SSO UI Service dan Payment Gateway:** Mock/sandbox untuk simulasi autentikasi mahasiswa UI dan alur pembayaran. Jangan gunakan konfigurasi development untuk transaksi nyata.

### Implementasi lokasi penjemputan

Pada **Barang saya → Tambah Barang** dan **Edit Barang**, pengguna dapat memilih riwayat akun atau menyimpan label, alamat, dan titik baru. Peta Leaflet/OpenStreetMap mendukung klik peta, geser pin, lokasi perangkat, dan koordinat manual. Saat mengedit, **Lokasi saat ini** menampilkan salinan lokasi pada barang, termasuk ketika riwayat asal sudah dihapus. Menggeser pin lalu menyimpan perubahan hanya memperbarui lokasi barang tersebut. Riwayat dapat dikelola juga melalui **Akun saya → Lokasi Tersimpan**.

- Jalankan `python manage.py migrate` setelah mengambil perubahan model lokasi.
- Tampilan pemilih: `templates/locations/picker.html`, `static/js/pickup-location.js`, dan `static/css/pickup-location.css`.
- Riwayat milik akun: `locations/models.py`, `locations/forms.py`, dan `locations/views.py`. Endpoint `/lokasi/api/penjemputan/` mendukung GET/POST; `/lokasi/api/penjemputan/<id>/` mendukung PATCH/DELETE dan memerlukan login serta CSRF untuk perubahan data.
- `barang/services.py` menyimpan salinan lokasi pada barang. Mengubah atau menghapus riwayat tidak mengubah salinan tersebut. Data lokasi barang lama tetap didukung.
- Saat pesanan diajukan, koordinat titik penjemputan ikut disimpan pada snapshot pesanan. Detail pesanan menampilkan pin dan dapat meminta rute dari posisi perangkat melalui OSRM. Rute membutuhkan izin lokasi dan koneksi internet; tautan Google Maps menjadi alternatif. Pesanan lama tanpa koordinat snapshot menggunakan titik barang saat ini jika masih tersedia.
- `OSM_TILE_URL` opsional untuk penyedia tile yang kompatibel; default menggunakan tile OpenStreetMap dengan atribusi. `OSRM_ROUTE_URL` dapat diubah untuk memakai server OSRM lain; default menggunakan layanan publik OSRM. Tombol lokasi perangkat membutuhkan izin browser dan HTTPS atau localhost. Nominatim yang sudah ada tetap digunakan untuk nama wilayah di navbar; memilih/menyeret pin tidak memanggil Nominatim.

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

## LINK PWS 
https://roisul-umam-pinjemin.pws.cs.ui.ac.id/

---

## AI Disclosure & Documentation

**I Nyoman Yadnya Suta Karmana / 2506615993**

**Alat:** ChatGPT/Codex, sebagai asisten AI untuk pengembangan.

AI digunakan untuk meninjau kebutuhan modul, mencari kemungkinan celah pada alur lokasi, menyusun usulan perubahan, membantu membuat pengujian, dan merapikan dokumentasi. Saran AI tidak langsung dianggap benar atau diterapkan tanpa pemeriksaan; perubahan dibandingkan dengan kode, kebutuhan tugas, dan hasil pengujian.

### Contoh prompt

Berikut beberapa contoh permintaan bantuan yang saya berikan selama mengerjakan modul. Saya tetap meninjau saran dan perubahan terhadap kode proyek sebelum menggunakannya:

1. “Aku sudah mengerjakan peta barang terdekat di beranda. Bantu cek bagian lokasi perangkat dan pilihan radius pencariannya, lalu beri tahu kalau ada yang perlu diperbaiki.”
2. “Di detail pesanan, bagian lokasi penjemputan masih berupa teks. Bantu tambahkan tampilan peta, saran rute, dan tautan ke Google Maps sesuai struktur proyekku.”
3. “Aku sudah punya fitur Manajemen Lokasi. Bantu tinjau CRUD, snapshot lokasi barang dan pesanan, serta pembatasan aksesnya terhadap jobdesk; jelaskan atau perbaiki bagian yang masih kurang.”
4. “Bantu dokumentasikan kontribusiku di modul Manajemen Lokasi, termasuk alur dan API yang benar-benar dipakai. Aku akan mencocokkan dokumentasinya dengan implementasi.”
5. “Bantu rapikan tampilan fitur lokasi dan sesuaikan agar tetap nyaman digunakan di berbagai ukuran layar.”

### Strategi dan validasi

Pengerjaan dilakukan bertahap: memberi konteks struktur proyek dan jobdesk, meminta audit atau perubahan yang spesifik, lalu memeriksa hasil terhadap implementasi aktual dan menguji alur penting. Prompt meminta solusi mengikuti API yang disetujui proyek, menjaga data lokasi milik setiap akun, dan tidak mengubah snapshot lama ketika riwayat diedit atau dihapus.

AI dapat salah membaca arsitektur, menyarankan algoritma yang tidak digunakan, atau melewatkan batas privasi dan kondisi tepi. AI juga tidak dapat membuktikan bahwa konfigurasi deployment atau layanan eksternal selalu tersedia hanya dari kode lokal.

Contoh pemeriksaan dan koreksi setelah meninjau source:

- Permintaan awal menyebut Dijkstra untuk rute. Kode aktual menghitung jarak dekat dengan Haversine dan meminta rute jalan melalui OSRM, jadi dokumentasi diperbaiki agar tidak mengklaim Dijkstra sebagai kode yang ditulis sendiri.
- Audit menemukan halaman barang dan API barang terdekat perlu membatasi ketelitian koordinat untuk pengunjung. Respons publik kini memakai area perkiraan, sedangkan titik persis dibatasi kepada pemilik dan peminjam pada pesanan terkait. Pengujian memeriksa bahwa koordinat presisi tidak bocor ke respons publik.
- Saran AI dan implementasi diperiksa terhadap validasi pemilik di server, CSRF, penyimpanan soft-delete, dan snapshot mandiri agar riwayat yang diedit/dihapus tidak mengubah data barang atau pesanan.

Validasi kode mencakup pengujian Django pada aplikasi `locations`, `barang`, dan `transaksi`, serta `python manage.py check`. Catatan: akses ke layanan eksternal dan keberhasilan deployment tetap perlu diverifikasi pada lingkungan yang menjalankannya.

**Alphard Qodaruddin / 2506632910**

**Alat:** ChatGPT/Codex (GPT-6.1 Sol), sebagai asisten AI untuk pengembangan.

AI saya gunakan untuk membuat planning bagaimana workflow yang optimal dalam mengerjakan modul bagian saya, memahami bagaimana payment gateway Midtrans bekerja, troubleshooting error dalam flow pembayaran dan refund, dan mempercantik visual (UI). Kode dan sistem kasarnya saya lakukan sendiri setelah memahami workflow yang direkomendasikan AI, kemudian setelah fitur cukup fungsional, AI membantu untuk merapikan kodenya dan mempercantik visualnya.

### Contoh prompt

Berikut beberapa contoh permintaan bantuan yang saya berikan selama mengerjakan modul. Saya tetap meninjau saran dan perubahan terhadap kode proyek sebelum menggunakannya:

1. "Aku harus menambahkan fitur transaksi pembayaran menggunakan suatu payment gateway untuk website ini, berikan rekomendasi pilihan payment gateway yang bisa saya gunakan dan berikan perbandingan diantaranya"
2. "Buatkan aku planning workflow yang paling optimal untuk mengerjakan modul transaksi ini menggunakan payment gatewa Midtrans untuk mengurangi resiko error atau kerja dua kali"
3. "Ada error berupa flow pembayaran yang terlihat looping (kembali ke awal setelah pembayaran), tolong scan project ini dan beri tahu aku masalahnya ada dimana agar bisa aku perbaiki"
4. "Flow pembayaran dan refund saat ini sudah sepenuhnya bagus, sekarang tolong percantik UI visualnya agar lebih menarik dilihat tanpa mengubah ubah pilihan opsi tombol atau informasi didalamnya."

### Strategi dan validasi

Penggunaan AI dilakukan secara bertahap, dimulai dari perencanaan workflow dan pemilihan payment gateway, dilanjutkan dengan pemahaman integrasi Midtrans, implementasi fitur transaksi, troubleshooting, dan penyempurnaan UI. Saya menggunakan AI untuk membantu memahami alur kerja dan mengidentifikasi kemungkinan masalah, tetapi tetap mengerjakan implementasi dasar secara mandiri berdasarkan pemahaman terhadap solusi yang direkomendasikan.

Dalam proses implementasi, AI digunakan sebagai alat bantu analisis ketika muncul masalah pada alur pembayaran, termasuk ketika proses pembayaran kembali ke halaman awal secara tidak semestinya. Saya meminta AI meninjau struktur proyek dan kode yang berkaitan untuk membantu menemukan kemungkinan penyebabnya. Hasil analisis tersebut menjadi acuan untuk pemeriksaan dan perbaikan, bukan dianggap sebagai bukti bahwa penyebab masalah telah ditemukan secara pasti.

Setelah alur transaksi pembayaran dan refund berfungsi sesuai kebutuhan, penggunaan AI dialihkan untuk membantu merapikan struktur kode dan meningkatkan kualitas visual antarmuka. Perubahan UI dibatasi pada aspek presentasi, seperti tata letak dan tampilan elemen, tanpa mengubah pilihan tombol, opsi yang tersedia, atau informasi yang ditampilkan kepada pengguna. Dengan demikian, penyempurnaan visual tidak dimaksudkan untuk mengubah fungsi bisnis yang sudah berjalan.

### Keterbatasan AI dan pemeriksaan hasil

AI dapat memberikan rekomendasi yang kurang sesuai dengan struktur proyek, salah memahami alur transaksi, atau mengidentifikasi penyebab error yang ternyata tidak berkaitan dengan masalah sebenarnya. Karena itu, rekomendasi AI tetap perlu diperiksa terhadap implementasi aktual dan kebutuhan modul.

Salah satu keterbatasan yang saya temui adalah AI tidak dapat secara langsung melakukan konfigurasi awal Midtrans melalui dashboard website Midtrans yang saya gunakan. AI dapat membantu menjelaskan tahapan setup, memberikan panduan konfigurasi, dan membantu memahami parameter yang diperlukan untuk integrasi. Namun, saya tetap harus membuka browser dan melakukan konfigurasi tersebut secara mandiri melalui website Midtrans, termasuk menyiapkan pengaturan awal yang dibutuhkan sebelum payment gateway dapat diintegrasikan dengan website proyek.

Dalam integrasi payment gateway, keberhasilan implementasi tidak cukup dinilai dari tampilan halaman atau respons yang terlihat di sisi pengguna. Alur pembayaran dan refund juga perlu diperiksa agar status transaksi, perpindahan halaman, dan hasil proses tetap konsisten. Selain itu, saran AI mengenai integrasi Midtrans perlu disesuaikan dengan API dan konfigurasi yang benar-benar digunakan dalam proyek.

Pada tahap penyempurnaan UI, hasil perubahan perlu diperiksa kembali untuk memastikan bahwa perbaikan tampilan tidak menghilangkan informasi, mengubah fungsi tombol, atau merusak alur transaksi yang sebelumnya sudah berjalan.

Secara keseluruhan, AI berperan sebagai asisten untuk mempercepat perencanaan, membantu memahami teknologi yang digunakan, mendukung proses troubleshooting, dan meningkatkan kualitas kode serta UI. Keputusan implementasi dan penilaian akhir terhadap kesesuaian fitur tetap dilakukan berdasarkan pemeriksaan kode dan pengujian terhadap kebutuhan modul.

**Roisul Umam / 2506620210**

**Alat:** Claude, sebagai asisten AI untuk pengembangan.

AI digunakan untuk meninjau kebutuhan modul, mencari kemungkinan celah pada alur autentikasi dan otorisasi, menyusun usulan struktur artikel bantuan, membantu membuat pengujian (test case), dan merapikan dokumentasi. Saran AI tidak langsung dianggap benar atau diterapkan tanpa pemeriksaan; perubahan dibandingkan dengan kode, kebutuhan tugas, dan hasil pengujian.

### Contoh prompt

Berikut beberapa contoh permintaan bantuan yang saya berikan selama mengerjakan modul. Saya tetap meninjau saran dan perubahan terhadap kode proyek sebelum menggunakannya:

1. “Aku sedang mengintegrasikan login SSO UI pada modul Accounts. Bantu cek konfigurasi middleware, penanganan token CAS/OAuth, dan alur validasi tiketnya, lalu beri tahu kalau ada yang perlu diperbaiki dari segi keamanan.”
2. “Di bagian Help Center, aku ingin membuat daftar kategori pertanyaan umum (FAQ). Bantu susun struktur artikel panduan, navigasi pencarian, dan layout pusat bantuan agar ramah bagi pengguna baru sesuai arsitektur proyekku.”
3. “Aku sudah punya fitur Manajemen Akun dan Pusat Bantuan punya temanku. Bantu tinjau integrasi session login, proteksi rute halaman bantuan untuk admin, serta pembatasan aksesnya terhadap jobdesk; jelaskan atau perbaiki bagian yang masih kurang.”
4. “Bantu rapikan tampilan antarmuka (UI) halaman login SSO dan Help Center, serta sesuaikan agar tetap nyaman digunakan di berbagai ukuran layar (responsif).”

### Strategi dan validasi

Pengerjaan dilakukan bertahap: memberi konteks struktur proyek dan jobdesk, meminta audit atau perubahan yang spesifik, lalu memeriksa hasil terhadap implementasi aktual dan menguji alur penting. Prompt meminta solusi mengikuti API yang disetujui proyek, menjaga keamanan data kredensial milik setiap akun, dan memastikan bahwa pengguna yang belum terautentikasi tetap bisa mengakses Help Center namun dibatasi untuk fitur akun.

Contoh pemeriksaan dan koreksi setelah meninjau source:

- Permintaan awal menyarankan penyimpanan token secara lokal tanpa enkripsi. Kode aktual menerapkan penyimpanan secure session cookies berbasis server, jadi dokumentasi diperbaiki agar tidak mengklaim metode penyimpanan lokal yang kurang aman sebagai kode yang ditulis sendiri.
- Saran AI dan implementasi diperiksa terhadap validasi token di server, perlindungan CSRF pada form login, penanganan session timeout, dan mekanisme clear session saat logout agar riwayat login lama tidak disalahgunakan.

**Chelsea Stania Passikha / 2506587876**

**Alat: ChatGPT**

AI digunakan untuk membantu saat debugging, memberikan saran mengenai implementasi MVT pada aplikasi, membantu merancang desain, membantu membuat pengujian, dan menyesuaikan modul kategori dengan modul-modul lain. Output dari AI tidak langsung  diterapkan tanpa peninjauan dan pengujian.

### Contoh prompt
Berikut beberapa contoh permintaan bantuan yang saya berikan selama mengerjakan modul:

- "Saya mendapatkan UnboundLocalError pada view saya. Apa yang dapat menyebabkan error ini?"
- "Object pada model categories muncul di page categories tapi tidak di homepage,  apa saja yang perlu diubah?"
- "Saya telah membuat CSS, namun tampilannya tidak sesuai dengan tampilan yang diinginkan. Bantu saya menyesuaikan CSS dengan template."

### Strategi dan validasi
Penggunaan AI melewati beberapa tahap. Saya menjelaskan masalah atau kebutuhan fitur dan meminta solusi awal, kemudian memeriksa hasilnya dan menyesuaikannya dengan kebutuhan proyek.

Contoh pemeriksaan dan koreksi setelah meninjau source:

- Kode CSS yang disarankan AI tidak konsisten dengan halaman lain. Misalnya, palet warna yang didapatkan berbeda dengan bagian lain.
- AI dapat memberi saran untuk mengubah satu view secara menyeluruh, namun yang perlu diganti hanya beberapa baris saja. Hal ini perlu dibenarkan secara manual.
- Saran AI mengenai autentikasi, serta peran dan akses pengguna diperiksa agar tidak terjadi kesalahan akses.

**Fauzan Taqiy Santosa / 2506607272**

**Alat:** Antigravity (Google DeepMind) sebagai asisten AI untuk pengembangan modul Manajemen Barang.

AI digunakan untuk merancang arsitektur integrasi antara katalog barang dengan alur peminjaman, menegakkan aturan bisnis (penguncian status, larangan edit/hapus barang yang sedang dipinjam aktif, pencegahan peminjaman barang sendiri), mengimplementasikan sistem penyelesaian pesanan dan ulasan bintang (rating 1–5), menulis pengujian unit (*test suite*) yang komprehensif, serta merapikan antarmuka dan modularitas CSS.

### Contoh prompt

Berikut beberapa contoh instruksi dan permintaan bantuan yang saya berikan selama pengerjaan modul:

1. "Bantu rancang integrasi alur peminjaman dari halaman detail barang ke pembuatan draft transaksi, lengkap dengan validasi kepemilikan agar pemilik tidak bisa meminjam barangnya sendiri."
2. "Terapkan aturan bisnis penguncian barang: jika barang memiliki pesanan yang berstatus dikonfirmasi/aktif dipinjam, tombol edit dan hapus harus terkunci dan backend view serta AJAX harus menolak permintaannya."
3. "Implementasikan alur pengembalian barang oleh pemilik (konfirmasi selesai), form pemberian ulasan bintang 1–5 bagi peminjam, serta tampilkan riwayat testimoni dan skor reputasi pemilik di halaman profil publik."
4. "Periksa seluruh file HTML dan CSS pada modul barang dan transaksi, pindahkan seluruh blok inline style ke file stylesheet terpisah, dan bersihkan semua karakter emoji menjadi ikon SVG vektor agar tampilan konsisten dan profesional."
5. "Buatkan unit test komprehensif untuk menguji seluruh skenario peminjaman, hak akses pengembalian barang, pencegahan ulasan ganda, dan tampilan profil publik pemilik."

### Strategi dan validasi

Pengerjaan modul dilakukan secara bertahap dan terstruktur. Setiap usulan logika bisnis dan kode dari AI selalu ditinjau kembali kesesuaiannya dengan spesifikasi proyek PBP dan peran rekan kelompok lainnya.

Beberapa contoh evaluasi, koreksi, dan pemeriksaan terhadap saran AI:
- **Pembersihan Komponen UI:** Pada implementasi awal, AI sempat menyertakan simbol emoji (seperti ⭐, 📦, 🔒, ⚡) pada teks dan tombol. Saya mengoreksi hal tersebut dengan meminta pembersihan menyeluruh dan menggantinya dengan ikon SVG vektor terstandarisasi serta memindahkan inline styling ke file CSS modular (`barang.css`, `profile.css`, dan `transaksi.css`).
- **Integritas Aturan Bisnis & Validasi Akses:** Memastikan logika penyelesaian transaksi hanya dapat dieksekusi oleh pemilik sah, serta form ulasan hanya terbuka untuk peminjam dari transaksi yang sudah berstatus selesai (*completed*). Dilakukan penguncian agar satu transaksi tidak dapat diulas lebih dari satu kali.
- **Validasi Pengujian Otomatis:** Setiap tahapan kode diverifikasi langsung dengan menjalankan *automated test suite* Django (`python manage.py test barang`). Seluruh 123 skenario pengujian dipastikan lulus (*OK*) sebelum kode diintegrasikan ke cabang utama.
