import os
import glob
import random
import streamlit as st
from groq import Groq
from google import genai
from google.genai import types
from pypdf import PdfReader
from PIL import Image

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
                loaded_files.append(pdf_path)
        except Exception:
            continue
    return combined_text, loaded_files

MODUL_TEXT, DAFTAR_MODUL = load_builtin_modules()

# ==========================================
# 4. SYSTEM PROMPT (OTAK ASISTEN RA'BUNG-NET AI)
# ==========================================
BASE_SYSTEM_PROMPT = f"""
Kamu adalah 'RA'BUNG-NET AI', asisten virtual praktikum untuk siswa jurusan Teknik Jaringan Komputer dan Telekomunikasi (TJKT) di {ASAL_SEKOLAH}.
Tugas utamamu adalah membantu siswa melakukan troubleshooting konfigurasi jaringan (Mikrotik RouterOS, Cisco IOS), administrasi sistem jaringan (Linux Debian/Ubuntu), dan perhitungan Subnetting IPv4/IPv6, termasuk menganalisis gambar/screenshot error konfigurasi yang dikirimkan siswa.

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
# 6. FUNGSI MULTIMODAL HYBRID AI (MENDUKUNG TEKS & GAMBAR)
# ==========================================
def generate_multimodal_response(groq_key_list, gemini_key_list, chat_messages, system_instruction, uploaded_image=None):
    errors_log = []

    # Prioritaskan Google Gemini untuk analisis gambar karena kemampuan Vision-nya sangat kuat
    if gemini_key_list and uploaded_image:
        gem_keys = list(gemini_key_list)
        random.shuffle(gem_keys)

        gemini_contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"[INSTRUKSI SISTEM WAJIB DIIKUTI]:\n{system_instruction}")]
            ),
            types.Content(
                role="model",
                parts=[types.Part.from_text(text="Siap, saya RA'BUNG-NET AI siap menganalisis teks dan gambar praktikum TJKT.")]
            )
        ]

        for m in chat_messages:
            role = "user" if m["role"] == "user" else "model"
            parts_list = []
            if isinstance(m["content"], list):
                for item in m["content"]:
                    if isinstance(item, str):
                        parts_list.append(types.Part.from_text(text=item))
                    elif hasattr(item, "format"): # Jika objek gambar PIL
                        parts_list.append(types.Part.from_image(item))
            else:
                parts_list.append(types.Part.from_text(text=str(m["content"])))
            
            gemini_contents.append(types.Content(role=role, parts=parts_list))

        for k in gem_keys:
            try:
                client = genai.Client(api_key=k)
                active_gemini_models = []
                try:
                    for m in client.models.list():
                        name = m.name.replace("models/", "")
                        if "gemini" in name and not any(x in name for x in ["tts", "embedding", "audio", "veo", "imagen"]):
                            active_gemini_models.append(name)
                except Exception as e:
                    errors_log.append(f"Gemini List Error: {e}")

                preferred_gem = ["flash", "pro"]
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
                            return response.text, f"Google Vision ({model_name})"
                    except Exception as e:
                        errors_log.append(f"Gemini Vision [{model_name}]: {e}")
                        continue
            except Exception as e:
                errors_log.append(f"Gemini Client Error: {e}")

    # Fallback / Chat Teks biasa via Groq atau Gemini
    # LAPIS 1: GROQ CLOUD
    if groq_key_list and not uploaded_image:
        g_keys = list(groq_key_list)
        random.shuffle(g_keys)

        groq_payload = [{"role": "system", "content": system_instruction}]
        for m in chat_messages:
            role = "user" if m["role"] == "user" else "assistant"
            content_str = m["content"]
            if isinstance(content_str, list):
                content_str = " ".join([str(x) for x in content_str if isinstance(x, str)])
            groq_payload.append({"role": role, "content": content_str})

        for k in g_keys:
            try:
                client = Groq(api_key=k)
                active_groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
                for model_name in active_groq_models:
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
                    except Exception:
                        continue
            except Exception:
                pass

    # LAPIS 2: GOOGLE GEMINI (TEKS BIASA)
    if gemini_key_list:
        gem_keys = list(gemini_key_list)
        random.shuffle(gem_keys)
        
        gemini_contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=f"[INSTRUKSI SISTEM]:\n{system_instruction}")]),
            types.Content(role="model", parts=[types.Part.from_text(text="Siap.")])
        ]
        for m in chat_messages:
            role = "user" if m["role"] == "user" else "model"
            content_str = m["content"]
            if isinstance(content_str, list):
                content_str = " ".join([str(x) for x in content_str if isinstance(x, str)])
            gemini_contents.append(types.Content(role=role, parts=[types.Part.from_text(text=content_str)]))

        for k in gem_keys:
            try:
                client = genai.Client(api_key=k)
                response = client.models.generate_content(
                    model="gemini-2.5-flash" if "gemini-2.5-flash" in str(client.models.list()) else "gemini-1.5-flash",
                    contents=gemini_contents,
                    config=types.GenerateContentConfig(temperature=0.3)
                )
                if response and response.text:
                    return response.text, "Google (Gemini Flash)"
            except Exception:
                continue

    raise RuntimeError(" | ".join(errors_log[-5:]) if errors_log else "Tidak ada model AI yang merespons.")

# ==========================================
# 7. SIDEBAR: LOGO, MODUL PRAKTIKUM & INFO KARYA
# ==========================================
extra_modul_text = ""

with st.sidebar:
    if LOGO_PATH:
        col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
        with col_s2:
            st.image(LOGO_PATH, use_container_width=True)

    st.markdown("<h2 style='text-align: center; margin-bottom: 0;'>RA'BUNG-NET AI</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: gray; font-size: 0.9em;'>Asisten Virtual Praktikum TJKT<br><b>{ASAL_SEKOLAH}</b></p>", unsafe_allow_html=True)
    st.divider()

    st.subheader("📚 Modul & Jobsheet Praktikum")
    if DAFTAR_MODUL:
        st.success(f"Tersedia {len(DAFTAR_MODUL)} Modul Praktikum Sekolah:")
        for file_path in DAFTAR_MODUL:
            nama_file = os.path.basename(file_path)
            col_m1, col_m2 = st.columns([3, 1])
            with col_m1:
                st.markdown(f"📄 `{nama_file}`")
            with col_m2:
                try:
                    with open(file_path, "rb") as f:
                        st.download_button("⬇️", f, file_name=nama_file, mime="application/pdf", key=f"dl_{nama_file}")
                except Exception:
                    pass
    else:
        st.info("Menggunakan Kurikulum Standar TJKT.")

    with st.expander("📤 Upload Materi Praktikum (PDF)", expanded=False):
        uploaded_pdfs = st.file_uploader("Unggah Jobsheet PDF:", type=["pdf"], accept_multiple_files=True)
        if uploaded_pdfs:
            for up_file in uploaded_pdfs:
                try:
                    reader = PdfReader(up_file)
                    file_text = ""
                    for page in reader.pages:
                        file_text += (page.extract_text() or "") + "\n"
                    if file_text.strip():
                        extra_modul_text += f"\n--- ISI MODUL: {up_file.name} ---\n{file_text}\n"
                        st.success(f"✅ Aktif: {up_file.name}")
                except Exception as e:
                    st.error(f"Gagal: {e}")

    active_engines = []
    if groq_keys: active_engines.append("Groq")
    if gemini_keys: active_engines.append("Gemini Vision")
    if active_engines:
        st.caption(f"🟢 Mesin AI Aktif: **{' + '.join(active_engines)}**")

    st.divider()

    with st.expander("📋 Identitas & Deskripsi Karya", expanded=False):
        st.markdown(f"""
        **Nama Karya:** RA'BUNG-NET AI  
        **Pembuat:** {NAMA_GURU}  
        **Satuan Pendidikan:** {ASAL_SEKOLAH}  
        **Kategori:** {KATEGORI_KARYA}  
        
        **Tujuan & Fungsi:**  
        Asisten AI 24/7 berbasis Multimodal (Teks & Analisis Gambar/Screenshot) untuk troubleshooting jaringan Mikrotik, Cisco, Linux, dan Subnetting.
        """)

    if st.button("🔄 Mulai Percakapan Baru", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 8. HALAMAN UTAMA & WIDGET UPLOAD GAMBAR
# ==========================================
if LOGO_PATH:
    col_h1, col_h2 = st.columns([1, 9])
    with col_h1:
        st.image(LOGO_PATH, width=85)
    with col_h2:
        st.header("RA'BUNG-NET AI: Asisten Praktikum Jaringan & Server Linux")
        st.write("Ketik pertanyaan, atau **unggah screenshot error** konfigurasi/topologi di bawah ini untuk dianalisis AI!")
else:
    st.header("🤖 RA'BUNG-NET AI: Asisten Praktikum Jaringan & Server Linux")
    st.write("Ketik pertanyaan, atau **unggah screenshot error** konfigurasi/topologi di bawah ini untuk dianalisis AI!")

st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Halo Sobat TJKT! 👋 Saya **RA'BUNG-NET AI**. "
                "Jika ada error saat praktikum, kamu bisa ketik pertanyaannya ATAU **unggah screenshot layar/error** pada panel di bawah agar saya bisa bantu menganalisisnya!"
            )
        }
    ]

# Tampilkan Riwayat Chat
assistant_avatar = LOGO_PATH if LOGO_PATH else "assistant"
for msg in st.session_state.messages:
    avatar_icon = assistant_avatar if msg["role"] == "assistant" else "user"
    with st.chat_message(msg["role"], avatar=avatar_icon):
        if isinstance(msg["content"], list):
            for c in msg["content"]:
                if hasattr(c, "format"): # Jika itu gambar PIL
                    st.image(c, caption="Gambar yang diunggah siswa", width=350)
                else:
                    st.markdown(str(c))
        else:
            st.markdown(str(c))

# Input File Gambar (Opsional di atas chat input)
uploaded_image_file = st.file_uploader("🖼️ Unggah Screenshot Error / Topologi (Opsional):", type=["png", "jpg", "jpeg"])
user_prompt = st.chat_input("Ketik pesan atau pertanyaan tentang error di atas...")

# ==========================================
# 9. PEMROSESAN PESAN & ANALISIS GAMBAR
# ==========================================
if user_prompt or uploaded_image_file:
    current_content = []
    pil_img = None

    if uploaded_image_file:
        try:
            pil_img = Image.open(uploaded_image_file)
            current_content.append(pil_img)
        except Exception:
            pass

    if user_prompt:
        current_content.append(user_prompt)
    elif pil_img and not user_prompt:
        current_content.append("Tolong analisis gambar screenshot konfigurasi/error ini dan berikan petunjuk troubleshooting-nya.")

    # Simpan ke session state
    st.session_state.messages.append({"role": "user", "content": current_content})

    with st.chat_message("user"):
        if pil_img:
            st.image(pil_img, caption="Screenshot dikirim", width=350)
        if user_prompt:
            st.markdown(user_prompt)

    if not groq_keys and not gemini_keys:
        with st.chat_message("assistant", avatar=assistant_avatar):
            st.error("⚠️ API Key belum diatur di Streamlit Secrets.")
    else:
        with st.chat_message("assistant", avatar=assistant_avatar):
            with st.spinner("RA'BUNG-NET AI sedang menganalisis gambar dan modul praktikum..."):
                try:
                    full_system_instruction = BASE_SYSTEM_PROMPT
                    gabungan_modul = (MODUL_TEXT + "\n" + extra_modul_text).strip()
                    if gabungan_modul:
                        full_system_instruction += f"\n\nBERIKUT RINGKASAN MODUL PRAKTIKUM SEKOLAH:\n{gabungan_modul[:15000]}"

                    recent_messages = st.session_state.messages[-4:]
                    reply, used_engine = generate_multimodal_response(
                        groq_keys, gemini_keys, recent_messages, full_system_instruction, uploaded_image=pil_img
                    )

                    st.markdown(reply)
                    st.caption(f"⚡ Dijawab melalui mesin: `{used_engine}`")
                    st.session_state.messages.append({"role": "assistant", "content": reply})

                except Exception as e:
                    st.error("⏳ Maaf, terjadi kendala saat memproses gambar atau teks.")
                    with st.expander("🔍 Detail Error"):
                        st.code(str(e))
