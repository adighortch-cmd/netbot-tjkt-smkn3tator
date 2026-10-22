# JOBSHEET 02: ADMINISTRASI WEB SERVER (NGINX) & DNS SERVER (BIND9) DI LINUX DEBIAN 12
**Institusi:** Jurusan Teknik Jaringan Komputer dan Telekomunikasi (TJKT) - SMKN 3 Tana Toraja  
**Kode Praktikum:** TJKT-LNX-02  
**Sistem Operasi:** Linux Debian 12 (Bookworm) CLI / Ubuntu Server 22.04 LTS  

---

## 1. Spesifikasi Parameter Praktikum Sekolah
Setiap siswa membangun layanan Web Server dan DNS Server di mesin virtual (VirtualBox / Proxmox) atau PC Server Lab dengan ketentuan:
* **Nomor Absen Siswa:** `XY` (2 digit nomor urut absen)
* **IP Address Server Debian (`enp0s3` / `eth0`):** `192.168.XY.2/24`
* **Gateway (MikroTik Siswa):** `192.168.XY.1`
* **Nama Domain Praktikum:** `smkn3toraja-xy.lan` dan `www.smkn3toraja-xy.lan`
* **Direktori Root Website:** `/var/www/smkn3toraja-xy`

---

## 2. Panduan Pemeriksaan Konfigurasi Jaringan Linux
Sebelum menginstal paket atau menguji layanan server, pastikan jaringan dasar Debian berfungsi:
1. File konfigurasi IP statis terletak di `/etc/network/interfaces`.
2. Pastikan penulisan `address`, `netmask` (atau notasi CIDR `/24`), dan `gateway` tidak salah ketik.
3. Untuk menerapkan perubahan jaringan, gunakan:
   * `systemctl restart networking`
   * Verifikasi IP yang aktif dengan perintah: `ip a` atau `ip addr show`
   * Verifikasi tabel routing dengan perintah: `ip r` atau `ip route show`

---

## 3. Administrasi & Debugging DNS Server (BIND9)

### File Penting BIND9 di Debian:
* `/etc/bind/named.conf.options`: Pengaturan *forwarders* dan izin query (`allow-query { any; };`).
* `/etc/bind/named.conf.local`: Deklarasi zona *Forward* (`smkn3toraja-xy.lan`) dan zona *Reverse* (`XY.168.192.in-addr.arpa`).
* `/etc/bind/db.forward` & `/etc/bind/db.reverse`: File database record (`SOA`, `NS`, `A`, `PTR`, `CNAME`).

### Prosedur Troubleshooting BIND9 (Jika Service Error):
Jika siswa mengunggah screenshot error `Job for named.service failed` atau `bind9.service failed`:
1. **Jangan menebak-nebak isi file!** Arahkan siswa menjalankan alat pemeriksa sintaks bawaan BIND9:
   * Periksa file konfigurasi utama: `named-checkconf`
   * Periksa file zona forward: `named-checkzone smkn3toraja-xy.lan /etc/bind/db.forward`
2. **Kesalahan paling sering ditemukan pada screenshot siswa:**
   * Kurang tanda titik koma (`;`) di akhir baris blok `{ ... };` pada `named.conf.local`.
   * Kurang tanda titik (`.`) di akhir FQDN pada file zona (misal menulis `smkn3toraja-xy.lan` tanpa titik di akhir menjadi `smkn3toraja-xy.lan.`).
   * Lupa menaikkan angka **Serial** atau salah meletakkan tanda kurung tutup `)` pada blok `SOA`.
3. **Pengujian DNS:**
   * Periksa apakah `/etc/resolv.conf` sudah mengarah ke IP server sendiri (`nameserver 192.168.XY.2`).
   * Uji resolusi domain dengan perintah `nslookup smkn3toraja-xy.lan` atau `dig smkn3toraja-xy.lan`.

---

## 4. Administrasi & Debugging Web Server (Nginx / Apache2)

### Struktur Virtual Host (Server Block) Nginx:
* File konfigurasi dibuat di: `/etc/nginx/sites-available/smkn3toraja-xy`
* Diaktifkan melalui *symbolic link* ke: `/etc/nginx/sites-enabled/` menggunakan perintah `ln -s`.

### Prosedur Troubleshooting Web Server (Checklist Wajib):
Ketika siswa melaporkan halaman web tidak bisa dibuka atau service Nginx gagal berjalan:
1. **Cek Status Service dan Pesan Log:**
   * Jalankan: `systemctl status nginx`
   * Lihat baris log error secara spesifik dengan: `journalctl -xeu nginx.service`
2. **Uji Sintaks Konfigurasi Nginx:**
   * Jalankan perintah: `nginx -t`
   * Perintah ini akan langsung menampilkan **nama file** dan **nomor baris** tempat terjadinya kesalahan ketik (misal: `unexpected "}"` atau directive yang tidak diakhiri titik koma `;`).
3. **Deteksi Bentrok Port 80 (Port Conflict):**
   * Jika pada screenshot muncul pesan `bind() to 0.0.0.0:80 failed (98: Address already in use)`, artinya ada web server lain (biasanya `apache2` bawaan instalasi) yang masih menggunakan port 80.
   * Minta siswa memeriksa proses yang memakai port 80 dengan perintah: `ss -tulpn | grep :80`
   * Solusinya adalah menghentikan salah satu layanan (contoh: `systemctl stop apache2 && systemctl disable apache2`).
4. **Masalah Error `403 Forbidden` atau `404 Not Found`:**
   * Pastikan lokasi folder pada directive `root /var/www/smkn3toraja-xy;` sesuai dengan nama folder asli di sistem.
   * Pastikan kepemilikan dan izin akses file (`chown -R www-data:www-data /var/www/smkn3toraja-xy` dan `chmod -R 755 /var/www/smkn3toraja-xy`).