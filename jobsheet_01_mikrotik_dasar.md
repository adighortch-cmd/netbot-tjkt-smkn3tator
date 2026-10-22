# JOBSHEET 01: KONFIGURASI DASAR MIKROTIK ROUTEROS (GATEWAY & NAT)
**Institusi:** Jurusan Teknik Jaringan Komputer dan Telekomunikasi (TJKT) - SMKN 3 Tana Toraja  
**Kode Praktikum:** TJKT-MKT-01  
**Perangkat:** MikroTik RouterBOARD (RB941-2nD / RB750Gr3) / CHR  

---

## 1. Standar Penomoran & Variabel Siswa (Wajib Dipatuhi)
Dalam seluruh praktikum di Lab TJKT SMKN 3 Tana Toraja, setiap siswa wajib menggunakan variabel **`XY`** yang merupakan **2 digit nomor urut absen siswa** (contoh: Absen 5 ditulis `5`, Absen 18 ditulis `18`).

### Topologi & Skema Pengalamatan Standar Lab:
* **Identity Router:** `R-TJKT-AbsenXY` (Contoh: `R-TJKT-Absen12`)
* **`ether1` (Jalur WAN / Sumber Internet Lab):**
  * Mode: DHCP Client (otomatis dari router utama lab) atau IP Statis `10.10.10.XY/24` dengan Gateway `10.10.10.1`.
* **`ether2` (Jalur LAN Kabel ke PC Siswa):**
  * IP Address: `192.168.XY.1/24`
  * Rentang DHCP Pool: `192.168.XY.10` s.d. `192.168.XY.100`
* **`wlan1` (Jalur Wireless / Hotspot Lab):**
  * IP Address: `172.16.XY.1/24`
  * SSID: `LAB-TJKT-SISWA-XY`

---

## 2. Alur Konfigurasi Bertahap (Konsep & Fungsi)

> **Catatan untuk Asisten AI (RA'BUNG-NET AI):**  
> Jangan berikan seluruh perintah CLI sekaligus kepada siswa. Pandu siswa memahami fungsi setiap tahapan di bawah ini dan minta mereka mengecek hasilnya per langkah.

### Tahap A: Identitas & Keamanan Dasar Router
1. Mengubah nama router melalui menu **System -> Identity** atau perintah CLI pada sub-menu `/system identity`.
2. Mengamankan akses user router melalui menu **System -> Users**. Siswa dilarang menggunakan password kosong di jaringan produksi, namun selama sesi debugging tidak boleh mengetikkan password asli ke ruang chat.

### Tahap B: Konfigurasi IP Address pada Interface
1. Pastikan nama dan status interface aktif (`R` = *Running*) menggunakan pemeriksaan `/interface print`.
2. Tambahkan IP Address pada `ether2` sesuai nomor absen (`192.168.XY.1/24`).
   * **Kesalahan Umum Siswa:** Lupa menambahkan prefix `/24` saat mengetik IP Address di WinBox (menu **IP -> Addresses**), sehingga subnet mask otomatis menjadi `/32` (Host tunggal) dan PC klien tidak bisa terhubung.

### Tahap C: Konfigurasi WAN (DHCP Client / Default Route) & DNS
1. Jika sumber internet lab menggunakan DHCP, aktifkan pada `ether1` melalui **IP -> DHCP Client** dan pastikan statusnya mencapai **`bound`**.
2. Jika menggunakan IP Statis, siswa wajib mengisi **IP -> Routes** dengan `dst-address=0.0.0.0/0` dan `gateway=10.10.10.1`.
3. Pada menu **IP -> DNS**, isi `servers=8.8.8.8,1.1.1.1` dan **wajib mencentang** opsi **`Allow Remote Requests`** agar router dapat meneruskan permintaan DNS dari PC klien.

### Tahap D: Konfigurasi Firewall NAT (Masquerade)
Agar IP Private di jaringan LAN (`192.168.XY.0/24`) dapat mengakses internet melalui IP WAN (`ether1`), siswa harus mengaktifkan fitur *Source NAT (srcnat)*:
* **Chain:** `srcnat`
* **Out. Interface:** `ether1` (Harus mengarah ke interface sumber internet, **bukan** `ether2`).
* **Action:** `masquerade`

---

## 3. Daftar Periksa Troubleshooting (Troubleshooting Checklist)

Apabila siswa melaporkan **"PC Klien tidak mendapat internet"** atau mengunggah screenshot WinBox yang bermasalah, pandu mereka melakukan pengecekan berurutan berikut:

1. **Cek Koneksi Fisik & IP Router:**
   * Jalankan perintah: `ip address print`
   * *Pertanyaan Evaluasi ke Siswa:* "Apakah di sebelah interface `ether1` dan `ether2` sudah muncul huruf **`R`** (*Running*)? Apakah IP di `ether2` sudah memakai `/24` dan bukan `/32`?"
2. **Cek Tabel Routing & Koneksi Router ke Internet:**
   * Jalankan perintah: `ip route print`
   * *Pertanyaan Evaluasi ke Siswa:* "Apakah sudah ada baris dengan tanda **`DAS`** atau **`AS`** menuju `dst-address=0.0.0.0/0`? Coba jalankan `ping 8.8.8.8` dari New Terminal MikroTik, apakah *reply* atau *timeout*?"
3. **Cek Resolusi Nama Domain (DNS):**
   * Jalankan perintah: `ip dns print` lalu uji dengan `ping google.com` di terminal router.
   * *Indikasi Masalah:* Jika `ping 8.8.8.8` berhasil tetapi `ping google.com` gagal, berarti konfigurasi DNS Server belum terisi atau belum dicentang `allow-remote-requests: yes`.
4. **Cek Aturan Translasi IP (Firewall NAT):**
   * Jalankan perintah: `ip firewall nat print`
   * *Indikasi Masalah:* Jika di terminal MikroTik sudah bisa `ping google.com` tetapi PC klien tetap tidak bisa internetan, periksa apakah `out-interface` pada rule `masquerade` salah diarahkan ke `ether2` atau apakah ada tanda **`X`** (*Disabled*) maupun **`I`** (*Invalid*).