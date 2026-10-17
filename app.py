import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader

# ==========================================
# 1. KONFIGURASI HALAMAN & IDENTITAS KARYA
# ==========================================
st.set_page_config(
    page_title="NetBot TJKT - Asisten Praktikum Jaringan & Linux",
    page_icon="🌐",
    layout="wide"
)

# Ubah data di bawah ini sesuai identitas Anda
NAMA_GURU = "Adinegoro Mangentang"
ASAL_SEKOLAH = "SMK Negeri 3 Tana Toraja"
KATEGORI_KARYA = "AI Agent dan Chatbot / Koding dan Kecerdasan Artifisial"

# ==========================================
# 2. SYSTEM PROMPT (OTAK ASISTEN AI TJKT)
# ==========================================
BASE_SYSTEM_PROMPT = f"""
Kamu adalah 'NetBot TJKT', asisten virtual praktikum untuk siswa jurusan Teknik Jaringan Komputer dan Telekomunikasi (TJKT) di {ASAL_SEKOLAH}.
Tugas utamamu adalah membantu siswa melakukan troubleshooting konfigurasi jaringan (Mikrotik RouterOS, Cisco IOS), administrasi sistem jaringan (Linux Debian/Ubuntu), dan perhitungan Subnetting IPv4/IPv6.

Aturan Respons dan Pedagogis:
1. Berperanlah sebagai guru pembimbing lab yang ramah, sabar, dan memotivasi.
2. JANGAN langsung memberikan kunci jawaban konfigurasi utuh tanpa penjelasan. Bantu siswa memahami letak kesalahannya (debugging/troubleshooting).
3. Berikan daftar periksa pengecekan (troubleshooting checklist), misalnya menyarankan perintah `ip address print`, `ip route print`, `ping`, `traceroute`, `systemctl status`, `journalctl -xe`, atau `nginx -t` / `named-checkconf`.
4. Untuk pertanyaan Subnetting, jelaskan langkah-langkah cara menghitungnya (mulai dari prefix, subnet mask, blok subnet, jumlah host, hingga range IP valid).
5. Ingatkan siswa untuk selalu menjaga keamanan jaringan dan tidak membagikan password asli/publik di dalam percakapan.
6. Jika siswa bertanya di luar topik jaringan komputer, server, pemrograman, atau pembelajaran SMK, tolak dengan sopan dan arahkan kembali ke materi praktikum TJKT.
"""

# ==========================================
# 3. SIDEBAR: DOKUMENTASI VALIDASI JUKNIS
# ==========================================
with st.sidebar:
    st.title("🌐 NetBot TJKT")
    st.caption("Karya Digital Guru Provinsi Sulawesi Selatan Tahun 2026")
    st.divider()

    # Pengaturan API Key (Otomatis baca dari Streamlit Secrets jika sudah di-deploy)
    api_key = None
    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets.get("GEMINI_API_KEY", None)
    except Exception:
        pass

    if not api_key:
        api_key = st.text_input(
            "🔑 Masukkan Gemini API Key:",
            type="password",
            help="Dapatkan API Key gratis di https://aistudio.google.com/app/apikey"
        )

    # Fitur Tambahan: Unggah Jobsheet PDF sebagai referensi tambahan AI
    st.subheader("📄 Konteks Jobsheet (Opsional)")
    uploaded_pdf = st.file_uploader(
        "Unggah Jobsheet Praktikum (PDF) agar bot menjawab sesuai modul kelas:",
        type=["pdf"]
    )
    pdf_text = ""
    if uploaded_pdf:
        try:
            reader = PdfReader(uploaded_pdf)
            for page in reader.pages:
                pdf_text += page.extract_text() + "\n"
            st.success(f"Jobsheet '{uploaded_pdf.name}' berhasil dimuat ke memori AI!")
        except Exception as e:
            st.error(f"Gagal membaca PDF: {e}")

    st.divider()

    # Informasi Wajib Sesuai Juknis Bab V.D (Agar mudah diperiksa Validator)
    with st.expander("📋 Identitas & Deskripsi Karya", expanded=False):
        st.markdown(f"""
        **Pembuat:** {NAMA_GURU}  
        **Satuan Pendidikan:** {ASAL_SEKOLAH}  
        **Kategori:** {KATEGORI_KARYA}  
        
        **Permasalahan:**  
        Keterbatasan waktu guru saat mendampingi 30+ siswa praktikum jaringan & server secara bersamaan ketika terjadi *error* konfigurasi.
        
        **Tujuan & Fungsi:**  
        Menyediakan asisten AI 24/7 untuk mendiagnosis pesan *error* konfigurasi Mikrotik, Cisco, Linux Debian/Ubuntu, serta memandu perhitungan *subnetting* secara bertahap.
        
        **Manfaat:**  
        Mempercepat *troubleshooting* mandiri siswa di laboratorium dan rumah, serta meningkatkan efisiensi bimbingan praktik guru.
        """)

    with st.expander("🛡️ Etika, Privasi & Orisinalitas", expanded=False):
        st.markdown("""
        **Keamanan & Privasi Data:**  
        Pengguna dilarang memasukkan informasi sensitif, data pribadi, IP Publik produksi, atau *password* asli ke dalam percakapan.
        
        **Transparansi & Atribusi:**  
        Aplikasi ini dikembangkan secara orisinal menggunakan Python, Streamlit, dan model AI Google Gemini (`gemini-2.5-flash`) dengan instruksi khusus berbasis Kurikulum SMK TJKT.
        """)

    if st.button("🗑️ Bersihkan Riwayat Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 4. HALAMAN UTAMA & CONTOH PROMPT UJI COBA
# ==========================================
st.header("🤖 Asisten Troubleshooting Jaringan & Server Linux (TJKT)")
st.write(
    "Mengalami *error* saat konfigurasi **Mikrotik, Cisco, Linux Server (Debian/Ubuntu)**, atau bingung menghitung **Subnetting**? "
    "Ketik pesan *error* yang muncul di layar kamu atau klik tombol contoh kasus di bawah ini!"
)

# Inisialisasi Riwayat Percakapan
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Halo Sobat TJKT! 👋 Saya **NetBot**, asisten praktikum virtualmu. "
                "Ada kendala konfigurasi Mikrotik, Cisco Packet Tracer, Linux Server, atau perhitungan Subnetting hari ini? "
                "Silakan ceritakan topologimu atau tempelkan pesan *error*-nya di sini ya!"
            )
        }
    ]

# Tombol Contoh Prompt untuk memudahkan Siswa & Tim Validator menguji fungsi karya
st.markdown("##### 💡 Uji Coba Cepat (Klik salah satu skenario praktikum):")
col1, col2, col3, col4 = st.columns(4)

sample_prompt = None
with col1:
    if st.button("🔴 NAT Mikrotik Client No Internet", use_container_width=True):
        sample_prompt = (
            "Pak Bot, saya sedang praktik Mikrotik. PC Client sudah dapat IP dari DHCP Server Mikrotik, "
            "dan dari terminal Mikrotik sudah bisa ping 8.8.8.8. Tapi PC Client tidak bisa akses internet. "
            "Apa saja yang harus saya cek?"
        )
with col2:
    if st.button("🐧 DNS Bind9 Debian Failed", use_container_width=True):
        sample_prompt = (
            "Saat saya menjalankan perintah 'systemctl restart bind9' di Linux Debian, muncul pesan error: "
            "'Job for named.service failed because the control process exited with error code'. "
            "Bagaimana langkah mengecek letak salah ketik konfigurasinya?"
        )
with col3:
    if st.button("🔢 Hitung Subnetting /27", use_container_width=True):
        sample_prompt = (
            "Tolong jelaskan langkah demi langkah cara menghitung Subnet Mask, jumlah host valid, "
            "Network ID, dan Broadcast ID untuk IP 192.168.10.70/27!"
        )
with col4:
    if st.button("🖧 VLAN Cisco Tidak Bisa Ping", use_container_width=True):
        sample_prompt = (
            "Di Cisco Packet Tracer, saya membuat VLAN 10 (Lab) dan VLAN 20 (Guru) di dua Switch berbeda "
            "yang dihubungkan satu kabel. Kenapa PC di VLAN 10 Switch A tidak bisa ping ke PC VLAN 10 di Switch B?"
        )

st.divider()

# Menampilkan Riwayat Chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Menangkap input dari chat box atau dari tombol contoh skenario
user_input = st.chat_input("Ketik pertanyaan atau tempel pesan error konfigurasi di sini...")
prompt_to_process = sample_prompt if sample_prompt else user_input

# ==========================================
# 5. LOGIKA PEMROSESAN AI GEMINI
# ==========================================
if prompt_to_process:
    # Tampilkan pesan pengguna
    st.session_state.messages.append({"role": "user", "content": prompt_to_process})
    with st.chat_message("user"):
        st.markdown(prompt_to_process)

    # Validasi ketersediaan API Key
    if not api_key:
        with st.chat_message("assistant"):
            st.warning("⚠️ Silakan masukkan **Gemini API Key** terlebih dahulu pada menu di sebelah kiri (Sidebar) untuk memulai percakapan.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Menganalisis konfigurasi & menyusun langkah troubleshooting..."):
                try:
                    client = genai.Client(api_key=api_key)

                    # Gabungkan System Prompt dengan isi PDF Jobsheet jika ada yang diunggah
                    full_system_instruction = BASE_SYSTEM_PROMPT
                    if pdf_text:
                        full_system_instruction += f"\n\nBERIKUT ADALAH ISI JOBSHEET PRAKTIKUM SEKOLAH SEBAGAI ACUAN UTAMA:\n{pdf_text[:20000]}"

                    # Susun histori percakapan untuk dikirim ke Gemini
                    contents = []
                    for m in st.session_state.messages:
                        role = "user" if m["role"] == "user" else "model"
                        contents.append(
                            types.Content(
                                role=role,
                                parts=[types.Part.from_text(text=m["content"])]
                            )
                        )

                    # Panggil model Gemini 2.5 Flash
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=full_system_instruction,
                            temperature=0.3, # Rendah agar jawaban teknis tetap akurat & konsisten
                        )
                    )

                    reply = response.text
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})

                except Exception as e:
                    st.error(f"Terjadi kendala teknis saat menghubungi AI: {e}")