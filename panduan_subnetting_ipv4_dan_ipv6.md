# MODUL 03: PANDUAN STANDAR PERHITUNGAN SUBNETTING IPv4 & IPv6

**Institusi:** Jurusan Teknik Jaringan Komputer dan Telekomunikasi (TJKT) - SMKN 3 Tana Toraja

**Kode Materi:** TJKT-NET-03

## 1. Metode Pedagogis Perhitungan Subnetting IPv4 (Urutan 5 Langkah)

> **Instruksi Khusus untuk RA'BUNG-NET AI:**
>
> Setiap kali siswa bertanya tentang perhitungan Subnetting IPv4 (misalnya `192.168.10.0/26` atau `172.16.0.0/20`), **WAJIB** menjelaskan menggunakan urutan **5 Langkah Standar SMKN 3 Tana Toraja** di bawah ini secara berurutan. Jangan langsung memberikan hasil akhir tanpa memaparkan cara mendapatkannya.

### Langkah 1: Menentukan Prefix (CIDR) & Konversi ke Subnet Mask

* Identifikasi nilai prefix `/N` (jumlah bit bernilai `1` dari total $32\text{ bit}$ alamat IPv4).

* Tuliskan susunan $32\text{ bit}$ biner yang dibagi menjadi 4 oktet (masing-masing $8\text{ bit}$), lalu ubah ke angka desimal menggunakan nilai tempat biner:
  

  $$
  128 \quad 64 \quad 32 \quad 16 \quad 8 \quad 4 \quad 2 \quad 1
  $$

* *Contoh untuk `/26`:*

  * Biner: `11111111.11111111.11111111.11000000`

  * Oktet ke-4 memiliki dua angka `1` di awal ($128 + 64 = 192$).

  * Maka Subnet Mask desimalnya adalah `255.255.255.192`.

### Langkah 2: Menghitung Jumlah Subnet (Jaringan Baru)

* Hitung jumlah bit bernilai `1` yang dipinjam pada oktet aktif (dilambangkan dengan variabel $x$).

* Gunakan rumus:
  

  $$
  \text{Jumlah Subnet} = 2^x
  $$

* *Contoh untuk `/26` (Kelas C):* Jumlah angka `1` pada oktet ke-4 adalah $x = 2$, maka:
  

  $$
  \text{Jumlah Subnet} = 2^2 = 4 \text{ subnet}
  $$

### Langkah 3: Menghitung Blok Subnet (Kelipatan Gang/Blok)

* Blok subnet menunjukkan kelipatan alamat Network ID dari satu subnet ke subnet berikutnya.

* Gunakan rumus pengurangan konstanta $256$:
  

  $$
  \text{Blok Subnet} = 256 - \text{Nilai Desimal Oktet Terakhir Subnet Mask}
  $$

* *Contoh untuk `/26`:*
  

  $$
  \text{Blok Subnet} = 256 - 192 = 64
  $$

* Artinya, kelipatan subnet dimulai dari `0`, kemudian `64`, `128`, dan `192`.

### Langkah 4: Menghitung Jumlah Host Valid per Subnet

* Hitung sisa bit bernilai `0` (bit host, dilambangkan dengan variabel $y$, di mana $y = 32 - \text{Prefix}$).

* Dikurangi $2$ karena alamat paling awal digunakan sebagai **Network ID** dan alamat paling akhir digunakan sebagai **Broadcast Address**:
  

  $$
  \text{Jumlah Host Valid} = 2^y - 2
  $$

* *Contoh untuk `/26`:* Sisa angka `0` adalah $y = 32 - 26 = 6$, maka:
  

  $$
  \text{Jumlah Host Valid} = 2^6 - 2 = 64 - 2 = 62 \text{ host per subnet}
  $$

### Langkah 5: Menyusun Tabel Rentang IP (Network, Range Host Valid, Broadcast)

Aturan menyusun tabel untuk setiap blok subnet:

1. **Network ID:** Angka awal dari setiap kelipatan blok subnet (tidak boleh dipasang di PC/perangkat).

2. **IP Host Pertama (Awal Range Valid):** $\text{Network ID} + 1$ (biasanya dipasang pada interface Router/Gateway).

3. **Broadcast Address:** $\text{Network ID subnet berikutnya} - 1$ (digunakan untuk pengiriman paket ke seluruh host dalam satu subnet).

4. **IP Host Terakhir (Akhir Range Valid):** $\text{Broadcast Address} - 1$.

## 2. Tabel Referensi Cepat CIDR Kelas C (`/24` s.d. `/30`)

| Prefix (CIDR) | Subnet Mask Desimal | Oktet Biner ke-4 | Jumlah Subnet ($2^x$) | Blok Subnet ($256 - M$) | Jumlah Host Valid ($2^y - 2$) | 
| ----- | ----- | ----- | ----- | ----- | ----- | 
| `/24` | `255.255.255.0` | `00000000` | $2^0 = 1$ | $256 - 0 = 256$ | $2^8 - 2 = 254$ | 
| `/25` | `255.255.255.128` | `10000000` | $2^1 = 2$ | $256 - 128 = 128$ | $2^7 - 2 = 126$ | 
| `/26` | `255.255.255.192` | `11000000` | $2^2 = 4$ | $256 - 192 = 64$ | $2^6 - 2 = 62$ | 
| `/27` | `255.255.255.224` | `11100000` | $2^3 = 8$ | $256 - 224 = 32$ | $2^5 - 2 = 30$ | 
| `/28` | `255.255.255.240` | `11110000` | $2^4 = 16$ | $256 - 240 = 16$ | $2^4 - 2 = 14$ | 
| `/29` | `255.255.255.248` | `11111000` | $2^5 = 32$ | $256 - 248 = 8$ | $2^3 - 2 = 6$ | 
| `/30` | `255.255.255.252` | `11111100` | $2^6 = 64$ | $256 - 252 = 4$ | $2^2 - 2 = 2$ | 

## 3. Panduan Dasar Pengalamatan & Subnetting IPv6

Ketika siswa menanyakan materi IPv6, jelaskan poin-poin inti berikut secara terstruktur:

1. **Struktur Panjang Bit:**

   * IPv6 memiliki panjang $128\text{ bit}$ yang ditulis dalam format **heksadesimal** (`0-9` dan `a-f`), dibagi menjadi **8 grup (hextet)** yang dipisahkan tanda titik dua (`:`).

   * Setiap 1 grup (hextet) bernilai $16\text{ bit}$ (terdiri dari 4 digit heksadesimal, di mana $1\text{ digit heksadesimal} = 4\text{ bit biner}$).

2. **Dua Aturan Penyingkatan IPv6:**

   * **Aturan 1 (*Omit Leading Zeros*):** Menghilangkan angka nol di depan pada setiap hextet. Contoh: `:0db8:` ditulis `:db8:`, dan `:0000:` ditulis `:0:`.

   * **Aturan 2 (*Double Colon* `::`):** Mengganti satu rangkaian grup yang berisi nol berurutan (`:0000:0000:...`) dengan tanda titik dua ganda `::`. **Penting:** Tanda `::` hanya boleh digunakan **maksimal 1 kali** dalam satu alamat IPv6 agar tidak membingungkan perhitungan sisa bit.

3. **Pembagian Prefix Subnetting IPv6 (`/48` ke `/64`):**

   * Alokasi standar untuk jaringan LAN adalah **`/64`** ($64\text{ bit pertama}$ sebagai *Network Prefix*, dan $64\text{ bit terakhir}$ sebagai *Interface ID* / Host).

   * Jika sebuah institusi mendapat alokasi Global Routing Prefix `/48` (misal `2001:db8:acad::/48`) dan ingin membaginya menjadi beberapa subnet `/64`, maka terdapat selisih $64 - 48 = 16\text{ bit}$ (*Subnet ID* pada hextet ke-4).

   * Jumlah subnet `/64` yang dapat dibuat adalah:
     

     $$
     2^{16} = 65.536 \text{ subnet}
     $$

   * Penomoran subnet cukup menaikkan nilai heksadesimal pada hextet ke-4 secara berurutan:

     * Subnet 1: `2001:db8:acad:0000::/64` (ditulis `2001:db8:acad::/64`)

     * Subnet 2: `2001:db8:acad:0001::/64` (ditulis `2001:db8:acad:1::/64`)

     * Subnet 3: `2001:db8:acad:0002::/64` (ditulis `2001:db8:acad:2::/64`)

     * ... hingga `2001:db8:acad:ffff::/64`.