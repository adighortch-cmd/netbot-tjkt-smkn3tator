import os
import glob
import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader

# ==========================================
# 1. DETEKSI OTOMATIS FILE LOGO DI GITHUB
# ==========================================
def find_logo():
    for name in ["logo.png", "logo.jpg", "logo.jpeg"]:
        if os.path.exists(name):
            return name
    images = sorted(glob.glob("*.jpeg") + glob.glob("*.jpg") + glob.glob("*.png"))
    return images[0] if images else None

LOGO_PATH = find_logo()

# ==========================================
# 2. KONFIGURASI HALAMAN & IDENTITAS KARYA
# ==========================================
st.set_page_config(
    page_title="RA'BUNG-NET AI - SMKN 3 Tana Toraja",
    page_icon=LOGO_PATH if LOGO_PATH else "🌐",
    layout="wide"
)

# Ubah Nama Guru di bawah ini sesuai nama lengkap dan gelar Anda
NAMA_GURU = "Adighoro."
ASAL_SEKOLAH = "SMK Negeri 3 Tana Toraja - Sulawesi Selatan"
KATEGORI_KARYA = "AI Agent dan Chatbot / Koding dan Kecerdasan Artifisial"

# ==========================================
# 3. FUNGSI OTOMATIS BACA SEMUA MODUL PDF DI GITHUB
# ==========================================
@st.cache_data(show_spinner=False)
def load_builtin_modules():
    """Membaca otomatis semua file .pdf yang diunggah guru di repositori GitHub."""
    combined_text = ""
    loaded_files = []
    pdf_files = sorted(glob.glob("*.pdf"))
    
    for pdf_path in pdf_files:
        try:
            reader = PdfReader(pdf_path)
            file_text = ""
            for page in reader.pages:
                file_text += (page.extract_text() or "") + "\n"
            if file_text.strip():
                combined_text += f"\n--- ISI MODUL: {os.path.basename(pdf_path)} ---\n{file_text}\n"
                loaded_files.append(os.path.basename(pdf_path))
        except Exception:
            continue
            
    return combined_text, loaded_files

MODUL_TEXT, DAFTAR_MODUL = load_builtin_modules()

# ==========================================
# 4. SYSTEM PROMPT (OTAK ASISTEN RA'BUNG-NET AI)
# ==========================================
BASE_SYSTEM_PROMPT = f"""
Kamu adalah 'RA'BUNG-NET AI', asisten virtual praktikum untuk siswa jurusan Teknik Jaringan Komputer dan Telekomunikasi (TJKT) di {ASAL_SEKOLAH}.
Tugas utamamu adalah membantu siswa melakukan troubleshooting konfigurasi jaringan (Mikrotik RouterOS, Cisco IOS), administrasi sistem jaringan (Linux Debian/Ubuntu), dan perhitungan Subnetting IPv4/IPv6.

Aturan Respons dan Pedagogis:
1. Berperanlah sebagai guru pembimbing lab yang ramah, sabar, dan memotivasi siswa.
2. JANGAN langsung memberikan kunci jawaban konfigurasi utuh tanpa penjelasan. Bantu siswa memahami letak kesalahannya (debugging/troubleshooting).
3. Berikan daftar periksa pengecekan (troubleshooting checklist), misalnya menyarankan perintah `ip address print`, `ip route print`, `ping`, `traceroute`, `systemctl status`, `journalctl -xe`, atau `nginx -t` / `named-checkconf`.
4. Untuk pertanyaan Subnetting, jelaskan langkah-langkah cara menghitungnya (mulai dari prefix, subnet mask, blok subnet, jumlah host, hingga range IP valid).
5. Ingatkan siswa untuk selalu menjaga keamanan jaringan dan tidak membagikan password asli/publik di dalam percakapan.
6. Jika siswa bertanya di luar topik jaringan komputer, server, pemrograman, atau pembelajaran SMK, tolak dengan sopan dan arahkan kembali ke materi praktikum TJKT.
"""

# ==========================================
# 5. FUNGSI ROTASI MODEL & API KEY (ANTI ERROR 429 & 404)
# ==========================================
def generate_ai_response(api_keys_list, contents, system_instruction):
    # Urutan prioritas: dahulukan model Lite/Flash yang kuota hariannya lebih longgar
    priority_models = [
        "gemini-3.1-flash-lite-preview",
        "gemini-flash-lite-latest",
        "gemini-3-flash-preview",
        "gemini-flash-latest",
        "gemini-3.8-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash"
    ]
    
    last_error = None

    # Coba setiap API Key yang tersedia
    for current_key in api_keys_list:
        client = genai.Client(api_key=current_key)
        tried_models = set()

        # 1. Coba daftar model prioritas
        for model_name in priority_models:
            tried_models.add(model_name)
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.3,
                    )
                )
                return response.text, model_name
            except Exception as e:
                last_error = e
                err_str = str(e)
                # Jika model tidak ada (404) ATAU kuota model tersebut habis (429), otomatis pindah ke model berikutnya!
                if any(k in err_str for k in ["404", "NOT_FOUND", "429", "RESOURCE_EXHAUSTED", "quota", "no longer available"]):
                    continue
                else:
                    raise e

        # 2. Jika semua model di atas habis kuotanya, cari model teks lain yang masih aktif di akun Google tersebut
        try:
            for m in client.models.list():
                name = m.name.replace("models/", "")
                if name in tried_models:
                    continue
                if ("gemini" in name or "gemma" in name) and not any(x in name for x in ["tts", "image", "embedding", "vision", "audio", "veo", "imagen"]):
                    try:
                        response = client.models.generate_content(
                            model=name,
                            contents=contents,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                temperature=0.3,
                            )
                        )
                        return response.text, name
                    except Exception as e2:
                        last_error = e2
                        continue
        except Exception:
            continue

    raise last_error

# ==========================================
# 6. BACA API KEY DARI STREAMLIT SECRETS (MENDUKUNG MULTI-KEY)
# ==========================================
api_keys = []
try:
    if "GEMINI_API_KEY" in st.secrets:
        raw_keys = st.secrets["GEMINI_API_KEY"]
        # Mendukung 1 key atau banyak key yang dipisahkan tanda koma
        api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
except Exception:
    pass

# ==========================================
# 7. SIDEBAR: LOGO SEKOLAH & INFORMASI KARYA
# ==========================================
with st.sidebar:
    if LOGO_PATH:
        col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
        with col_s2:
            st.image(LOGO_PATH, use_container_width=True)

    st.markdown("<h2 style='text-align: center; margin-bottom: 0;'>RA'BUNG-NET AI</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: gray; font-size: 0.9em;'>Asisten Virtual Praktikum TJKT<br><b>{ASAL_SEKOLAH}</b></p>", unsafe_allow_html=True)
    st.divider()

    st.subheader("📚 Basis Pengetahuan Aktif")
    if DAFTAR_MODUL:
        st.success(f"Terhubung dengan {len(DAFTAR_MODUL)} Modul/Jobsheet Sekolah:")
        for nama_file in DAFTAR_MODUL:
            st.markdown(f"- 📄 `{nama_file}`")
    else:
        st.info("Menggunakan Kurikulum Standar TJKT (Mikrotik, Cisco, Linux Debian/Ubuntu, & Subnetting).")

    st.divider()

    with st.expander("📋 Identitas & Deskripsi Karya", expanded=False):
        st.markdown(f"""
        **Nama Karya:** RA'BUNG-NET AI  
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
        Aplikasi RA'BUNG-NET AI dikembangkan secara orisinal menggunakan Python, Streamlit, dan model AI Google Gemini terbaru dengan instruksi khusus berbasis Kurikulum SMK TJKT.
        """)

    if st.button("🔄 Mulai Percakapan Baru", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 8. HALAMAN UTAMA (HEADER DENGAN LOGO + RUANG CHAT)
# ==========================================
if LOGO_PATH:
    col_h1, col_h2 = st.columns([1, 9])
    with col_h1:
        st.image(LOGO_PATH, width=85)
    with col_h2:
        st.header("RA'BUNG-NET AI: Asisten Praktikum Jaringan & Server Linux")
        st.write(
            "Mengalami *error* saat konfigurasi **Mikrotik, Cisco, Linux Server (Debian/Ubuntu)**, atau bingung menghitung **Subnetting**? "
            "Ketik pertanyaan atau tempelkan pesan *error* yang muncul di layar kamu pada kolom chat di bawah ini!"
        )
else:
    st.header("🤖 RA'BUNG-NET AI: Asisten Praktikum Jaringan & Server Linux")
    st.write(
        "Mengalami *error* saat konfigurasi **Mikrotik, Cisco, Linux Server (Debian/Ubuntu)**, atau bingung menghitung **Subnetting**? "
        "Ketik pertanyaan atau tempelkan pesan *error* yang muncul di layar kamu pada kolom chat di bawah ini!"
    )

st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Halo Sobat TJKT! 👋 Saya **RA'BUNG-NET AI**, asisten praktikum virtualmu di **SMK Negeri 3 Tana Toraja**. "
                "Ada kendala konfigurasi Mikrotik, Cisco Packet Tracer, Linux Server, atau perhitungan Subnetting hari ini? "
                "Silakan ceritakan topologimu atau ketik pesan *error*-nya di bawah ini ya!"
            )
        }
    ]

assistant_avatar = LOGO_PATH if LOGO_PATH else "assistant"

for msg in st.session_state.messages:
    avatar_icon = assistant_avatar if msg["role"] == "assistant" else "user"
    with st.chat_message(msg["role"], avatar=avatar_icon):
        st.markdown(msg["content"])

prompt_to_process = st.chat_input("Ketik pertanyaan atau tempel pesan error konfigurasi di sini...")

# ==========================================
# 9. LOGIKA PEMROSESAN AI GEMINI
# ==========================================
if prompt_to_process:
    st.session_state.messages.append({"role": "user", "content": prompt_to_process})
    with st.chat_message("user"):
        st.markdown(prompt_to_process)

    if not api_keys:
        with st.chat_message("assistant", avatar=assistant_avatar):
            st.error("⚠️ Sistem sedang dalam pemeliharaan (API Key belum diatur oleh Guru di menu Settings -> Secrets Streamlit Cloud).")
    else:
        with st.chat_message("assistant", avatar=assistant_avatar):
            with st.spinner("RA'BUNG-NET AI sedang menganalisis konfigurasi & menyusun langkah troubleshooting..."):
                try:
                    full_system_instruction = BASE_SYSTEM_PROMPT
                    if MODUL_TEXT:
                        # Batasi ukuran teks modul agar hemat kuota token per menit
                        full_system_instruction += f"\n\nBERIKUT ADALAH ISI MODUL/JOBSHEET RESMI SEKOLAH SEBAGAI ACUAN UTAMA:\n{MODUL_TEXT[:15000]}"

                    # Ambil maksimal 6 pesan terakhir agar hemat kuota token
                    recent_messages = st.session_state.messages[-6:]
                    contents = []
                    for m in recent_messages:
                        role = "user" if m["role"] == "user" else "model"
                        contents.append(
                            types.Content(
                                role=role,
                                parts=[types.Part.from_text(text=m["content"])]
                            )
                        )

                    reply, used_model = generate_ai_response(api_keys, contents, full_system_instruction)

                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})

                except Exception as e:
                    st.error(
                        "⏳ Maaf, trafik penggunaan AI sedang sangat padat (batas kuota gratis tercapai). "
                        "Silakan tunggu sekitar 1 menit lalu coba kirim ulang pertanyaanmu ya!"
                    )
