import os
import glob
import random
import streamlit as st
from groq import Groq
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

NAMA_GURU = "Adi Ghoro"
ASAL_SEKOLAH = "SMK Negeri 3 Tana Toraja - Sulawesi Selatan"
KATEGORI_KARYA = "AI Agent dan Chatbot / Koding dan Kecerdasan Artifisial"

# ==========================================
# 3. FUNGSI OTOMATIS BACA SEMUA MODUL PDF DI GITHUB
# ==========================================
@st.cache_data(show_spinner=False)
def load_builtin_modules():
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
1. Berperanlah sebagai guru pembimbing lab yang ramah, sabar, dan memotivasi siswa. Gunakan Bahasa Indonesia yang jelas dan mudah dipahami siswa SMK.
2. JANGAN langsung memberikan kunci jawaban konfigurasi utuh tanpa penjelasan. Bantu siswa memahami letak kesalahannya (debugging/troubleshooting).
3. Berikan daftar periksa pengecekan (troubleshooting checklist), misalnya menyarankan perintah `ip address print`, `ip route print`, `ping`, `traceroute`, `systemctl status`, `journalctl -xe`, atau `nginx -t` / `named-checkconf`.
4. Untuk pertanyaan Subnetting, jelaskan langkah-langkah cara menghitungnya (mulai dari prefix, subnet mask, blok subnet, jumlah host, hingga range IP valid).
5. Ingatkan siswa untuk selalu menjaga keamanan jaringan dan tidak membagikan password asli/publik di dalam percakapan.
6. Jika siswa bertanya di luar topik jaringan komputer, server, pemrograman, atau pembelajaran SMK, tolak dengan sopan dan arahkan kembali ke materi praktikum TJKT.
"""

# ==========================================
# 5. BACA & PISAHKAN API KEY GROQ DAN GEMINI OTOMATIS
# ==========================================
groq_keys = []
gemini_keys = []

try:
    for secret_name in ["GROQ_API_KEY", "GEMINI_API_KEY"]:
        if secret_name in st.secrets:
            raw_val = st.secrets[secret_name]
            cleaned = str(raw_val).replace('"', '').replace("'", "").strip()
            for k in cleaned.split(","):
                k = k.strip()
                if k.startswith("gsk_") and k not in groq_keys:
                    groq_keys.append(k)
                elif k.startswith("AIza") and k not in gemini_keys:
                    gemini_keys.append(k)
except Exception:
    pass

# ==========================================
# 6. FUNGSI HYBRID AI DENGAN AUTO-DISCOVERY MODEL AKTIF
# ==========================================
def generate_hybrid_response(groq_key_list, gemini_key_list, chat_messages, system_instruction):
    errors_log = []

    # LAPIS 1: GROQ CLOUD (DETEKSI OTOMATIS MODEL AKTIF)
    if groq_key_list:
        g_keys = list(groq_key_list)
        random.shuffle(g_keys)

        groq_payload = [{"role": "system", "content": system_instruction}]
        for m in chat_messages:
            role = "user" if m["role"] == "user" else "assistant"
            groq_payload.append({"role": role, "content": m["content"]})

        for k in g_keys:
            try:
                client = Groq(api_key=k)
                active_groq_models = []
                try:
                    models_resp = client.models.list()
                    for m in models_resp.data:
                        m_id = m.id
                        if not any(skip in m_id.lower() for skip in ["whisper", "guard", "tts", "vision", "embed", "playai", "allam"]):
                            active_groq_models.append(m_id)
                except Exception as e:
                    errors_log.append(f"Groq List Error: {e}")

                preferred_keywords = ["llama-3.3", "llama-3.1", "llama3", "qwen", "deepseek", "mixtral", "gemma"]
                sorted_groq_models = []
                for kw in preferred_keywords:
                    for m_id in active_groq_models:
                        if kw in m_id.lower() and m_id not in sorted_groq_models:
                            sorted_groq_models.append(m_id)
                for m_id in active_groq_models:
                    if m_id not in sorted_groq_models:
                        sorted_groq_models.append(m_id)

                if not sorted_groq_models:
                    sorted_groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

                for model_name in sorted_groq_models:
                    try:
                        completion = client.chat.completions.create(
                            model=model_name,
                            messages=groq_payload,
                            temperature=0.3,
                            max_tokens=1500,
                        )
                        reply_text = completion.choices[0].message.content
                        if reply_text:
                            return reply_text, f"Groq ({model_name})"
                    except Exception as e:
                        errors_log.append(f"Groq [{model_name}]: {e}")
                        continue
            except Exception as e:
                errors_log.append(f"Groq Client Error: {e}")

    # LAPIS 2: GOOGLE GEMINI (DETEKSI OTOMATIS MODEL AKTIF)
    if gemini_key_list:
        gem_keys = list(gemini_key_list)
        random.shuffle(gem_keys)

        gemini_contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"[INSTRUKSI SISTEM WAJIB DIIKUTI]:\n{system_instruction}\n\nJika paham, jawab pertanyaan siswa berikut sesuai instruksi di atas.")]
            ),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="Siap, saya RA'BUNG-NET AI akan mematuhi seluruh instruksi tersebut.")]
            )
        ]

        for m in chat_messages:
            role = "user" if m["role"] == "user" else "model"
            gemini_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=m["content"])]
                )
            )

        for k in gem_keys:
            try:
                client = genai.Client(api_key=k)
                active_gemini_models = []
                try:
                    for m in client.models.list():
                        name = m.name.replace("models/", "")
                        if ("gemini" in name or "gemma" in name) and not any(x in name for x in ["tts", "image", "embedding", "vision", "audio", "veo", "imagen", "robotics", "computer-use"]):
                            active_gemini_models.append(name)
                except Exception as e:
                    errors_log.append(f"Gemini List Error: {e}")

                preferred_gem = ["flash-lite", "gemma-3", "flash"]
                sorted_gemini = []
                for kw in preferred_gem:
                    for m_id in active_gemini_models:
                        if kw in m_id.lower() and m_id not in sorted_gemini:
                            sorted_gemini.append(m_id)
                for m_id in active_gemini_models:
                    if m_id not in sorted_gemini:
                        sorted_gemini.append(m_id)

                for model_name in sorted_gemini:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=gemini_contents,
                            config=types.GenerateContentConfig(temperature=0.3)
                        )
                        if response and response.text:
                            return response.text, f"Google ({model_name})"
                    except Exception as e:
                        errors_log.append(f"Gemini [{model_name}]: {e}")
                        continue
            except Exception as e:
                errors_log.append(f"Gemini Client Error: {e}")

    raise RuntimeError(" | ".join(errors_log[-5:]) if errors_log else "Tidak ada model yang merespons.")

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

    active_engines = []
    if groq_keys:
        active_engines.append("Groq LPU")
    if gemini_keys:
        active_engines.append("Google Gemini")
    if active_engines:
        st.caption(f"🟢 Mesin AI Aktif: **{' + '.join(active_engines)}**")

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
        Aplikasi RA'BUNG-NET AI dikembangkan secara orisinal menggunakan Python, Streamlit, serta arsitektur Hybrid AI (Groq Cloud LPU & Google Gemini) berbasis Kurikulum SMK TJKT.
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
# 9. LOGIKA PEMROSESAN HYBRID AI
# ==========================================
if prompt_to_process:
    st.session_state.messages.append({"role": "user", "content": prompt_to_process})
    with st.chat_message("user"):
        st.markdown(prompt_to_process)

    if not groq_keys and not gemini_keys:
        with st.chat_message("assistant", avatar=assistant_avatar):
            st.error("⚠️ API Key belum terbaca di Streamlit Secrets. Pastikan Anda sudah memasukkan GROQ_API_KEY = \"gsk_...\" di menu Settings -> Secrets.")
    else:
        with st.chat_message("assistant", avatar=assistant_avatar):
            with st.spinner("RA'BUNG-NET AI sedang menganalisis konfigurasi & menyusun langkah troubleshooting..."):
                try:
                    full_system_instruction = BASE_SYSTEM_PROMPT
                    if MODUL_TEXT:
                        full_system_instruction += f"\n\nBERIKUT RINGKASAN MODUL SEKOLAH:\n{MODUL_TEXT[:4000]}"

                    recent_messages = st.session_state.messages[-4:]
                    reply, used_engine = generate_hybrid_response(
                        groq_keys, gemini_keys, recent_messages, full_system_instruction
                    )

                    st.markdown(reply)
                    st.caption(f"⚡ Dijawab melalui mesin: `{used_engine}`")
                    st.session_state.messages.append({"role": "assistant", "content": reply})

                except Exception as e:
                    st.error("⏳ Maaf, terjadi kendala saat menghubungi server AI.")
                    with st.expander("🔍 Lihat Detail Teknis Error (Untuk Guru)"):
                        st.code(str(e))
# --- AKHIR DARI FILE APP.PY ---
