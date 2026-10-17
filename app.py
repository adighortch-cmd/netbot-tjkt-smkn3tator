import os
import io
import glob
import base64
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
Tugas utamamu adalah membantu siswa melakukan troubleshooting konfigurasi jaringan (Mikrotik RouterOS, Cisco IOS), administrasi sistem jaringan (Linux Debian/Ubuntu), dan perhitungan Subnetting IPv4/IPv6, termasuk menganalisis gambar screenshot error, topologi, atau file konfigurasi yang dikirimkan siswa.

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
# 6. FUNGSI KONVERSI GAMBAR KE JPEG BYTES MURNI
# ==========================================
def convert_uploaded_image_to_jpeg_bytes(uploaded_file):
    uploaded_file.seek(0)
    raw_bytes = uploaded_file.read()
    pil_img = Image.open(io.BytesIO(raw_bytes))
    rgb_im = pil_img.convert("RGB")
    rgb_im.thumbnail((1024, 1024))
    buf = io.BytesIO()
    rgb_im.save(buf, format="JPEG", quality=80)
    return buf.getvalue()

# ==========================================
# 7. FUNGSI MULTIMODAL HYBRID AI (AUTO-DISCOVERY ANTI 404)
# ==========================================
def generate_multimodal_response(groq_key_list, gemini_key_list, chat_messages, system_instruction, image_bytes_list=None):
    errors_log = []

    # ---------------------------------------------------------
    # A. JIKA ADA GAMBAR: SCAN SEMUA MODEL AKTIF DI GEMINI & GROQ
    # ---------------------------------------------------------
    if image_bytes_list:
        last_msg = chat_messages[-1]
        user_question = last_msg.get("text", "").strip()
        if not user_question:
            user_question = "Tolong analisis gambar screenshot praktikum/konfigurasi/error ini secara detail dan berikan langkah troubleshooting-nya."

        target_img_bytes = image_bytes_list[-1]
        img_b64 = base64.b64encode(target_img_bytes).decode("utf-8")

        # 1. COBA GOOGLE GEMINI VISION (Deteksi Otomatis Semua Model Gemini Aktif)
        if gemini_key_list:
            gem_keys = list(gemini_key_list)
            random.shuffle(gem_keys)

            parts_payload = [
                types.Part.from_text(text=f"[INSTRUKSI SISTEM]:\n{system_instruction}\n\n[PERTANYAAN SISWA TERKAIT GAMBAR TERLAMPIR]:\n{user_question}"),
                types.Part.from_bytes(data=target_img_bytes, mime_type="image/jpeg")
            ]

            for k in gem_keys:
                try:
                    client = genai.Client(api_key=k)
                    available_gem_models = []
                    try:
                        for m in client.models.list():
                            name = m.name.replace("models/", "")
                            if ("gemini" in name or "gemma" in name) and not any(x in name for x in ["tts", "audio", "embedding", "imagen", "veo", "aqa"]):
                                available_gem_models.append(name)
                    except Exception as e:
                        errors_log.append(f"Gemini List: {e}")

                    # Urutkan model flash/pro di paling atas
                    sorted_gem = []
                    for kw in ["flash", "pro", "gemma"]:
                        for m_id in available_gem_models:
                            if kw in m_id.lower() and m_id not in sorted_gem:
                                sorted_gem.append(m_id)
                    for m_id in available_gem_models:
                        if m_id not in sorted_gem:
                            sorted_gem.append(m_id)

                    for m_name in sorted_gem:
                        try:
                            response = client.models.generate_content(
                                model=m_name,
                                contents=[types.Content(role="user", parts=parts_payload)],
                                config=types.GenerateContentConfig(temperature=0.3)
                            )
                            if response and response.text:
                                return response.text, f"Google Vision ({m_name})"
                        except Exception as e:
                            errors_log.append(f"GemVision[{m_name}]: {str(e)[:80]}")
                            continue
                except Exception as e:
                    errors_log.append(f"Gemini Client: {e}")

        # 2. COBA GROQ VISION (Scan Otomatis Hanya Model yang Benar-Benar Ada di Server Groq Saat Ini)
        if groq_key_list:
            g_keys = list(groq_key_list)
            random.shuffle(g_keys)

            vision_content = [
                {"type": "text", "text": f"{system_instruction}\n\nPertanyaan Siswa terkait gambar ini:\n{user_question}"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
            ]

            for k in g_keys:
                try:
                    client = Groq(api_key=k)
                    all_groq_models = []
                    try:
                        for m in client.models.list().data:
                            m_id = m.id
                            if not any(skip in m_id.lower() for skip in ["whisper", "guard", "tts", "embed", "playai", "allam"]):
                                all_groq_models.append(m_id)
                    except Exception as e:
                        errors_log.append(f"Groq List: {e}")

                    # Prioritaskan model yang namanya mengandung indikasi multimodal/vision, lalu coba seluruh model aktif lainnya
                    sorted_vision_candidates = []
                    for kw in ["vision", "llama-4", "scout", "maverick", "pixtral", "llava", "multimodal", "omni"]:
                        for m_id in all_groq_models:
                            if kw in m_id.lower() and m_id not in sorted_vision_candidates:
                                sorted_vision_candidates.append(m_id)
                    for m_id in all_groq_models:
                        if m_id not in sorted_vision_candidates:
                            sorted_vision_candidates.append(m_id)

                    for v_model in sorted_vision_candidates:
                        try:
                            completion = client.chat.completions.create(
                                model=v_model,
                                messages=[{"role": "user", "content": vision_content}],
                                temperature=0.3,
                                max_tokens=1500
                            )
                            reply_text = completion.choices[0].message.content
                            if reply_text:
                                return reply_text, f"Groq Vision ({v_model})"
                        except Exception as e:
                            errors_log.append(f"GroqVision[{v_model}]: {str(e)[:80]}")
                            continue
                except Exception as e:
                    errors_log.append(f"Groq Client: {e}")

        # Jika semua model menolak gambar (misalnya akun hanya punya GROQ_API_KEY dan Groq sedang menonaktifkan semua model Vision gratis)
        raise RuntimeError(
            "Saat ini server Groq menonaktifkan model Vision (pembaca gambar) pada API Key Anda, atau kuota GEMINI_API_KEY belum aktif. "
            "Solusi: Pastikan GEMINI_API_KEY (dimulai dengan 'AIza...') sudah dimasukkan di Streamlit Secrets untuk mengaktifkan Google Gemini Vision, "
            "atau unggah file dalam bentuk PDF / Teks (.txt/.rsc). Detail: " + (" | ".join(errors_log[:3]))
        )

    # ---------------------------------------------------------
    # B. JIKA TEKS / FILE DOKUMEN (TANPA GAMBAR)
    # ---------------------------------------------------------
    if groq_key_list:
        g_keys = list(groq_key_list)
        random.shuffle(g_keys)

        groq_payload = [{"role": "system", "content": system_instruction}]
        for m in chat_messages:
            role = "user" if m["role"] == "user" else "assistant"
            text_val = m.get("text", "").strip()
            if text_val:
                groq_payload.append({"role": role, "content": text_val})

        for k in g_keys:
            try:
                client = Groq(api_key=k)
                active_groq_models = []
                try:
                    for m in client.models.list().data:
                        m_id = m.id
                        if not any(skip in m_id.lower() for skip in ["whisper", "guard", "tts", "embed", "playai", "allam"]):
                            active_groq_models.append(m_id)
                except Exception:
                    pass

                preferred_keywords = ["llama-3.3", "llama-3.1", "llama-4", "qwen", "deepseek", "mixtral", "gemma"]
                sorted_groq_models = []
                for kw in preferred_keywords:
                    for m_id in active_groq_models:
                        if kw in m_id.lower() and m_id not in sorted_groq_models:
                            sorted_groq_models.append(m_id)
                for m_id in active_groq_models:
                    if m_id not in sorted_groq_models:
                        sorted_groq_models.append(m_id)

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

    if gemini_key_list:
        gem_keys = list(gemini_key_list)
        random.shuffle(gem_keys)

        gemini_contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=f"[INSTRUKSI SISTEM]:\n{system_instruction}")]),
            types.Content(role="model", parts=[types.Part.from_text(text="Siap.")])
        ]
        for m in chat_messages:
            role = "user" if m["role"] == "user" else "model"
            text_val = m.get("text", "").strip()
            if text_val:
                gemini_contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text_val)]))

        for k in gem_keys:
            try:
                client = genai.Client(api_key=k)
                avail_gem = []
                try:
                    for m in client.models.list():
                        name = m.name.replace("models/", "")
                        if "gemini" in name and not any(x in name for x in ["tts", "audio", "embedding", "imagen", "veo"]):
                            avail_gem.append(name)
                except Exception:
                    avail_gem = ["gemini-2.5-flash", "gemini-2.0-flash"]

                for model_name in avail_gem:
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

    raise RuntimeError(" | ".join(errors_log[-5:]) if errors_log else "Pastikan API Key aktif di Streamlit Secrets.")

# ==========================================
# 8. SIDEBAR: LOGO, MODUL & INFO KARYA
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

    with st.expander("📤 Upload Modul Guru (PDF)", expanded=False):
        uploaded_pdfs = st.file_uploader("Tambah Modul Referensi:", type=["pdf"], accept_multiple_files=True)
        if uploaded_pdfs:
            for up_file in uploaded_pdfs:
                try:
                    up_file.seek(0)
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
    if groq_keys: active_engines.append(f"Groq ({len(groq_keys)} Key)")
    if gemini_keys: active_engines.append(f"Gemini Vision ({len(gemini_keys)} Key)")
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
        Asisten AI 24/7 berbasis Multimodal (Teks, File & Analisis Gambar/Screenshot) untuk troubleshooting jaringan Mikrotik, Cisco, Linux, dan Subnetting.
        """)

    if st.button("🔄 Mulai Percakapan Baru", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 9. HALAMAN UTAMA & RIWAYAT CHAT
# ==========================================
if LOGO_PATH:
    col_h1, col_h2 = st.columns([1, 9])
    with col_h1:
        st.image(LOGO_PATH, width=85)
    with col_h2:
        st.header("RA'BUNG-NET AI: Asisten Praktikum Jaringan & Server Linux")
        st.write(
            "Klik ikon **Lampirkan File/Foto (`+` / 📎)** di sebelah kiri kotak chat bawah untuk mengirim **screenshot error** "
            "(Winbox, Cisco, Linux) atau **file konfigurasi**, lalu ketik pertanyaanmu!"
        )
else:
    st.header("🤖 RA'BUNG-NET AI: Asisten Praktikum Jaringan & Server Linux")
    st.write(
        "Klik ikon **Lampirkan File/Foto (`+` / 📎)** di sebelah kiri kotak chat bawah untuk mengirim **screenshot error** "
        "(Winbox, Cisco, Linux) atau **file konfigurasi**, lalu ketik pertanyaanmu!"
    )

st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "text": (
                "Halo Sobat TJKT! 👋 Saya **RA'BUNG-NET AI**, asisten praktikum virtualmu di **SMK Negeri 3 Tana Toraja**. "
                "Kamu bisa langsung mengetik pertanyaan ATAU klik tombol **Lampirkan (`+` / 📎)** di sebelah kiri kolom ketik "
                "untuk mengunggah **foto/screenshot error** maupun **file praktikum** untuk saya analisis!"
            ),
            "images": [],
            "files": []
        }
    ]

assistant_avatar = LOGO_PATH if LOGO_PATH else "assistant"
for msg in st.session_state.messages:
    if "text" not in msg and "content" in msg:
        msg["text"] = str(msg["content"]) if not isinstance(msg["content"], list) else ""
        msg["images"] = []
        msg["files"] = []

    avatar_icon = assistant_avatar if msg["role"] == "assistant" else "user"
    with st.chat_message(msg["role"], avatar=avatar_icon):
        for img_bytes in msg.get("images", []):
            st.image(img_bytes, caption="Lampiran Gambar Siswa", width=350)
        if msg.get("files"):
            st.caption("📎 Lampiran File: " + ", ".join(msg["files"]))
        if msg.get("display_text"):
            st.markdown(msg["display_text"])
        elif msg.get("text"):
            st.markdown(msg["text"])

# ==========================================
# 10. KOLOM CHAT MODERN DENGAN TOMBOL UPLOAD MENYATU
# ==========================================
user_text = None
attached_files = []

try:
    chat_val = st.chat_input(
        "Tanyakan kendala praktikum atau lampirkan foto/file lewat ikon (+) di kiri...",
        accept_file="multiple",
        file_type=["png", "jpg", "jpeg", "webp", "pdf", "txt", "conf", "rsc", "log"]
    )
    if chat_val:
        user_text = chat_val.text
        attached_files = chat_val.files if hasattr(chat_val, "files") and chat_val.files else []
except TypeError:
    with st.popover("➕ Add photos & files (Upload dari Komputer/HP)"):
        fallback_files = st.file_uploader(
            "Pilih gambar screenshot error atau file praktikum:",
            type=["png", "jpg", "jpeg", "webp", "pdf", "txt", "conf", "rsc", "log"],
            accept_multiple_files=True,
            key="fallback_uploader"
        )
    raw_prompt = st.chat_input("Tanyakan kendala praktikum atau ketik pesan di sini...")
    if raw_prompt or fallback_files:
        user_text = raw_prompt
        attached_files = fallback_files if fallback_files else []

# ==========================================
# 11. PEMROSESAN PESAN, GAMBAR & FILE DARI SISWA
# ==========================================
if user_text or attached_files:
    image_bytes_list = []
    file_names_info = []
    extracted_docs_text = ""

    for f in attached_files:
        fname = getattr(f, "name", "lampiran")
        fname_lower = fname.lower()
        mime_type = getattr(f, "type", "").lower()

        is_image_file = fname_lower.endswith((".png", ".jpg", ".jpeg", ".webp")) or "image" in mime_type

        if is_image_file:
            try:
                img_bytes = convert_uploaded_image_to_jpeg_bytes(f)
                image_bytes_list.append(img_bytes)
                file_names_info.append(f"🖼️ `{fname}`")
            except Exception as e:
                st.warning(f"Gagal memproses gambar {fname}: {e}")
        elif fname_lower.endswith(".pdf") or "pdf" in mime_type:
            try:
                f.seek(0)
                reader = PdfReader(f)
                pdf_extracted = ""
                for p in reader.pages:
                    pdf_extracted += (p.extract_text() or "") + "\n"
                if pdf_extracted.strip():
                    extracted_docs_text += f"\n\n=== ISI FILE PDF YANG DIUNGGAH SISWA ({fname}) ===\n{pdf_extracted[:10000]}\n=====================================\n"
                    file_names_info.append(f"📄 `{fname}`")
                else:
                    file_names_info.append(f"📄 `{fname}` (PDF hasil scan/gambar)")
            except Exception as e:
                st.warning(f"Gagal membaca PDF {fname}: {e}")
        else:
            try:
                f.seek(0)
                txt_extracted = f.read().decode("utf-8", errors="ignore")
                if txt_extracted.strip():
                    extracted_docs_text += f"\n\n=== ISI FILE KONFIGURASI/TEKS SISWA ({fname}) ===\n```\n{txt_extracted[:10000]}\n```\n=====================================\n"
                    file_names_info.append(f"📝 `{fname}`")
            except Exception as e:
                st.warning(f"Gagal membaca file {fname}: {e}")

    display_text = user_text if user_text else "*[Mengirim lampiran untuk dianalisis]*"
    ai_prompt_text = user_text if user_text else "Tolong analisis lampiran yang saya kirimkan ini secara detail dan berikan langkah-langkah penyelesaiannya."

    if extracted_docs_text:
        ai_prompt_text = f"{ai_prompt_text}\n{extracted_docs_text}"

    st.session_state.messages.append({
        "role": "user",
        "text": ai_prompt_text,
        "display_text": display_text,
        "images": image_bytes_list,
        "files": file_names_info
    })

    with st.chat_message("user"):
        for img_b in image_bytes_list:
            st.image(img_b, caption="Screenshot dikirim ke AI", width=350)
        if file_names_info:
            st.caption("📎 Lampiran terkirim: " + ", ".join(file_names_info))
        st.markdown(display_text)

    if not groq_keys and not gemini_keys:
        with st.chat_message("assistant", avatar=assistant_avatar):
            st.error("⚠️ API Key belum diatur di Streamlit Secrets.")
    else:
        with st.chat_message("assistant", avatar=assistant_avatar):
            with st.spinner("RA'BUNG-NET AI sedang memeriksa isi lampiran & menyusun panduan troubleshooting..."):
                try:
                    full_system_instruction = BASE_SYSTEM_PROMPT
                    gabungan_modul = (MODUL_TEXT + "\n" + extra_modul_text).strip()
                    if gabungan_modul:
                        full_system_instruction += f"\n\nBERIKUT RINGKASAN MODUL PRAKTIKUM SEKOLAH:\n{gabungan_modul[:15000]}"

                    recent_messages = st.session_state.messages[-4:]
                    reply, used_engine = generate_multimodal_response(
                        groq_keys,
                        gemini_keys,
                        recent_messages,
                        full_system_instruction,
                        image_bytes_list=image_bytes_list
                    )

                    st.markdown(reply)
                    st.caption(f"⚡ Dijawab melalui mesin: `{used_engine}`")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "text": reply,
                        "display_text": reply,
                        "images": [],
                        "files": []
                    })

                except Exception as e:
                    st.error("⏳ Maaf, terjadi kendala saat menganalisis lampiran.")
                    with st.expander("🔍 Lihat Detail Teknis Error (Untuk Guru)"):
                        st.code(str(e))
# --- AKHIR DARI FILE APP.PY ---
