import os
import glob
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
ASAL_SEKOLAH = "SMKN 3 Tana Toraja - Sulawesi Selatan"
KATEGORI_KARYA = "AI Agent dan Chatbot / Koding dan Kecerdasan Artifisial"

# ==========================================
# 2. FUNGSI OTOMATIS BACA SEMUA MODUL PDF DI GITHUB
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
# 3. SYSTEM PROMPT (OTAK ASISTEN AI TJKT)
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
# 4. FUNGSI PEMANGGILAN AI DENGAN AUTO-FALLBACK
# ==========================================
def generate_ai_response(client, contents, system_instruction):
    candidate_models = [
        "gemini-3.8-flash",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite-preview",
        "gemini-flash-latest",
        "gemini-2.5-flash"
    ]
    
    last_error = None
    for model_name in candidate_models:
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
            if "404" in str(e) or "NOT_FOUND" in str(e) or "no longer available" in str(e):
                continue
            else:
                raise e

    for m in client.models.list():
        name = m.name.replace("models/", "")
        if "gemini" in name and "flash" in name and "tts" not in name and "image" not in name:
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
            except Exception:
                continue

    raise last_error

# ==========================================
# 5. BACA API KEY OTOMATIS DARI STREAMLIT SECRETS
# ==========================================
api_key = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

# ==========================================
# 6. SIDEBAR: BERSIH UNTUK SISWA & VALIDATOR
# ==========================================
with st.sidebar:
    st.title("🌐 NetBot TJKT")
    st.caption(f"Asisten Virtual Praktikum {ASAL_SEKOLAH}")
    st.divider()

    # Tampilkan status modul bawaan yang sudah tertanam otomatis
    st.subheader("📚 Basis Pengetahuan Aktif")
    if DAFTAR_MODUL:
        st.success(f"Terhubung dengan {len(DAFTAR_MODUL)} Modul/Jobsheet Sekolah:")
        for nama_file in DAFTAR_MODUL:
            st.markdown(f"- 📄 `{nama_file}`")
    else:
        st.info("Menggunakan Kurikulum Standar TJKT (Mikrotik, Cisco, Linux Debian/Ubuntu, & Subnetting).")

    st.divider()

    # Informasi Wajib Sesuai Juknis Bab V.D (Untuk Pemeriksaan Validator)
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
        Aplikasi ini dikembangkan secara orisinal menggunakan Python, Streamlit, dan model AI Google Gemini terbaru dengan instruksi khusus berbasis Kurikulum SMK TJKT.
        """)

    if st.button("🔄 Mulai Percakapan Baru", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 7. HALAMAN UTAMA (RUANG CHAT LANGSUNG)
# ==========================================
st.header("🤖 Asisten Troubleshooting Jaringan & Server Linux (TJKT)")
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
                "Halo Sobat TJKT! 👋 Saya **NetBot**, asisten praktikum virtualmu. "
                "Ada kendala konfigurasi Mikrotik, Cisco Packet Tracer, Linux Server, atau perhitungan Subnetting hari ini? "
                "Silakan ceritakan topologimu atau ketik pesan *error*-nya di bawah ini ya!"
            )
        }
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt_to_process = st.chat_input("Ketik pertanyaan atau tempel pesan error konfigurasi di sini...")

# ==========================================
# 8. LOGIKA PEMROSESAN AI GEMINI
# ==========================================
if prompt_to_process:
    st.session_state.messages.append({"role": "user", "content": prompt_to_process})
    with st.chat_message("user"):
        st.markdown(prompt_to_process)

    if not api_key:
        with st.chat_message("assistant"):
            st.error("⚠️ Sistem sedang dalam pemeliharaan (API Key belum diatur oleh Guru di menu Settings -> Secrets Streamlit Cloud).")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Menganalisis konfigurasi & menyusun langkah troubleshooting..."):
                try:
                    client = genai.Client(api_key=api_key)

                    full_system_instruction = BASE_SYSTEM_PROMPT
                    if MODUL_TEXT:
                        full_system_instruction += f"\n\nBERIKUT ADALAH ISI MODUL/JOBSHEET RESMI SEKOLAH SEBAGAI ACUAN UTAMA:\n{MODUL_TEXT[:30000]}"

                    contents = []
                    for m in st.session_state.messages:
                        role = "user" if m["role"] == "user" else "model"
                        contents.append(
                            types.Content(
                                role=role,
                                parts=[types.Part.from_text(text=m["content"])]
                            )
                        )

                    reply, used_model = generate_ai_response(client, contents, full_system_instruction)

                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})

                except Exception as e:
                    st.error(f"Terjadi kendala teknis saat menghubungi AI: {e}")
