import os
import io
import re
import glob
import json
import base64
import random
import urllib.request
import urllib.parse
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
    for name in ["logo.png", "logo.jpg", "logo.jpeg", "LOGO.PNG", "LOGO.JPG"]:
        if os.path.exists(name):
            return name
    images = sorted(
        glob.glob("*.jpeg") + glob.glob("*.jpg") + glob.glob("*.png") +
        glob.glob("*.JPEG") + glob.glob("*.JPG") + glob.glob("*.PNG")
    )
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
# 3. FUNGSI OTOMATIS BACA SEMUA MODUL PDF & MARKDOWN (.MD) DI GITHUB
# ==========================================
def scan_pdf_files_in_repo():
    found_pdfs = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["venv", "__pycache__"]]
        for f in files:
            if f.lower().endswith((".pdf", ".md")):
                full_path = os.path.join(root, f)
                found_pdfs.append(full_path)
    return tuple(sorted(found_pdfs))

@st.cache_data(show_spinner=False)
def load_builtin_modules(pdf_files_tuple):
    combined_text = ""
    loaded_files = []
    for pdf_path in pdf_files_tuple:
        if not os.path.exists(pdf_path):
            continue
        loaded_files.append(pdf_path)
        try:
            if pdf_path.lower().endswith(".md"):
                with open(pdf_path, "r", encoding="utf-8", errors="ignore") as f_md:
                    file_text = f_md.read()
            else:
                reader = PdfReader(pdf_path)
                file_text = ""
                for page in reader.pages:
                    file_text += (page.extract_text() or "") + "\n"

            if file_text.strip():
                combined_text += f"\n--- ISI MODUL: {os.path.basename(pdf_path)} ---\n{file_text[:3000]}\n"
            else:
                combined_text += f"\n--- MODUL TERSEDIA: {os.path.basename(pdf_path)} ---\n"
        except Exception:
            continue
    return combined_text, loaded_files

CURRENT_PDF_FILES = scan_pdf_files_in_repo()
MODUL_TEXT, DAFTAR_MODUL = load_builtin_modules(CURRENT_PDF_FILES)

# ==========================================
# 4. SYSTEM PROMPT (OTAK ASISTEN RA'BUNG-NET AI)
# ==========================================
BASE_SYSTEM_PROMPT = f"""
Kamu adalah 'RA'BUNG-NET AI', asisten virtual praktikum untuk siswa jurusan Teknik Jaringan Komputer dan Telekomunikasi (TJKT) di {ASAL_SEKOLAH}.
Tugas utamamu adalah membantu siswa memahami materi TJKT (termasuk DNS BIND9, Mikrotik, Cisco, Linux), melakukan troubleshooting konfigurasi, dan perhitungan Subnetting IPv4/IPv6, serta menganalisis gambar infografis, screenshot error, topologi, atau file konfigurasi yang dikirimkan siswa.

Aturan Respons:
1. Berperanlah sebagai guru pembimbing lab yang ramah, sabar, dan memotivasi siswa SMK.
2. Berikan jawaban yang LENGKAP, UTUH, dan tidak terpotong. Jika menuliskan kode konfigurasi (seperti named.conf.local, db.domain, dll), berikan baris skrip lengkapnya.
3. Utamakan menjawab sesuai isi MODUL PRAKTIKUM SEKOLAH yang dilampirkan.
"""

# ==========================================
# 5. DETEKSI OTOMATIS API KEY GROQ & GEMINI
# ==========================================
groq_keys = []
gemini_keys = []

def extract_keys_from_any(raw_obj):
    text_val = str(raw_obj)
    for gk in re.findall(r"gsk_[A-Za-z0-9_-]{20,}", text_val):
        if gk not in groq_keys:
            groq_keys.append(gk)
    for gemk in re.findall(r"AIza[A-Za-z0-9_-]{20,}", text_val):
        if gemk not in gemini_keys:
            gemini_keys.append(gemk)

try:
    for k, v in st.secrets.items():
        extract_keys_from_any(v)
except Exception:
    pass

try:
    for k, v in os.environ.items():
        extract_keys_from_any(v)
except Exception:
    pass

if gemini_keys:
    os.environ["GEMINI_API_KEY"] = gemini_keys[0]
if groq_keys:
    os.environ["GROQ_API_KEY"] = groq_keys[0]

# ==========================================
# 6. FUNGSI KONVERSI GAMBAR & EKSTRAKSI TEKS (OCR)
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

def extract_text_from_image_ocr(img_bytes):
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
    for engine_num in ["2", "1"]:
        try:
            payload = urllib.parse.urlencode({
                "apikey": "helloworld",
                "base64Image": f"data:image/jpeg;base64,{img_b64}",
                "OCREngine": engine_num,
                "scale": "true",
                "isTable": "true"
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.ocr.space/parse/image",
                data=payload,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                parsed_list = result.get("ParsedResults", [])
                if parsed_list:
                    extracted = parsed_list[0].get("ParsedText", "").strip()
                    if extracted:
                        return extracted
        except Exception:
            continue
    return ""

# ==========================================
# 7. FUNGSI MULTIMODAL HYBRID AI (MAX TOKENS DITINGKATKAN AGAR TIDAK TERPOTONG)
# ==========================================
def generate_multimodal_response(
    groq_key_list,
    gemini_key_list,
    chat_messages,
    system_instruction,
    image_bytes_list=None,
    image_names_list=None
):
    errors_log = []

    if image_bytes_list:
        last_msg = chat_messages[-1]
        user_question = last_msg.get("text", "").strip()
        if not user_question:
            user_question = "Tolong lanjutkan materi atau jelaskan gambar ini secara lengkap."

        target_img_bytes = image_bytes_list[-1]
        img_b64 = base64.b64encode(target_img_bytes).decode("utf-8")
        img_names_str = ", ".join(image_names_list) if image_names_list else "gambar_praktikum.png"

        if gemini_key_list:
            gem_keys = list(gemini_key_list)
            random.shuffle(gem_keys)
            parts_payload = [
                types.Part.from_text(text=f"[INSTRUKSI]:\n{system_instruction}\n\n[PERTANYAAN]:\n{user_question}"),
                types.Part.from_bytes(data=target_img_bytes, mime_type="image/jpeg")
            ]
            for k in gem_keys:
                try:
                    client = genai.Client(api_key=k)
                    for m_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                        try:
                            response = client.models.generate_content(
                                model=m_name,
                                contents=[types.Content(role="user", parts=parts_payload)],
                                config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=2048)
                            )
                            if response and response.text:
                                return response.text, f"Google Vision ({m_name})"
                        except Exception as e:
                            errors_log.append(f"GemVision[{m_name}]: {str(e)[:50]}")
                except Exception:
                    pass

        ocr_extracted_text = extract_text_from_image_ocr(target_img_bytes)
        if ocr_extracted_text:
            chat_messages[-1]["text"] = (
                f"[GAMBAR: '{img_names_str}']\n[TEKS DALAM GAMBAR]:\n{ocr_extracted_text[:3500]}\n\n[PERTANYAAN]: {user_question}\n\nBerikan penjelasan lengkap dan utuh!"
            )
        else:
            chat_messages[-1]["text"] = f"[GAMBAR: '{img_names_str}']\n[PERTANYAAN]: {user_question}\n\nBerikan penjelasan lengkap dan utuh!"

    # PEMROSESAN UTAMA VIA GROQ LPU (max_tokens=2048 agar tidak terpotong)
    if groq_key_list:
        g_keys = list(groq_key_list)
        random.shuffle(g_keys)

        safe_sys_prompt = system_instruction[:4500]
        groq_payload = [{"role": "system", "content": safe_sys_prompt}]
        for m in chat_messages[-3:]:
            role = "user" if m["role"] == "user" else "assistant"
            text_val = m.get("text", "").strip()[:3000]
            if text_val:
                groq_payload.append({"role": role, "content": text_val})

        for k in g_keys:
            try:
                client = Groq(api_key=k)
                active_groq_models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
                try:
                    for m in client.models.list().data:
                        m_id = m.id
                        if not any(skip in m_id.lower() for skip in ["whisper", "guard", "tts", "embed", "playai", "allam", "orpheus", "canopylabs"]):
                            if m_id not in active_groq_models:
                                active_groq_models.insert(0, m_id)
                except Exception:
                    pass

                for model_name in active_groq_models:
                    try:
                        completion = client.chat.completions.create(
                            model=model_name,
                            messages=groq_payload,
                            temperature=0.3,
                            max_tokens=2048,  # Ditingkatkan agar jawaban tidak terpotong
                        )
                        reply_text = completion.choices[0].message.content
                        if reply_text:
                            engine_label = f"Groq Vision-OCR ({model_name})" if image_bytes_list else f"Groq ({model_name})"
                            return reply_text, engine_label
                    except Exception as e:
                        errors_log.append(f"Groq [{model_name}]: {str(e)[:80]}")
                        continue
            except Exception as e:
                errors_log.append(f"Groq Client Error: {e}")

    # FALLBACK GOOGLE GEMINI TEKS
    if gemini_key_list:
        gem_keys = list(gemini_key_list)
        random.shuffle(gem_keys)
        history_text = f"[INSTRUKSI]:\n{system_instruction[:4500]}\n\n"
        for m in chat_messages[-3:]:
            role_label = "SISWA" if m["role"] == "user" else "ASISTEN"
            text_val = m.get("text", "").strip()[:3000]
            if text_val:
                history_text += f"{role_label}: {text_val}\n\n"

        for k in gem_keys:
            try:
                client = genai.Client(api_key=k)
                for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=history_text,
                            config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=2048)
                        )
                        if response and response.text:
                            return response.text, f"Google ({model_name})"
                    except Exception:
                        continue
            except Exception:
                pass

    raise RuntimeError(" | ".join(errors_log[-5:]) if errors_log else "Pastikan API Key aktif di Streamlit Secrets.")

# ==========================================
# 8. SIDEBAR: LOGO, MODUL & INFO KARYA
# ==========================================
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
        for idx, file_path in enumerate(DAFTAR_MODUL):
            nama_file = os.path.basename(file_path)
            is_md = nama_file.lower().endswith(".md")
            icon_doc = "📝" if is_md else "📄"
            mime_doc = "text/markdown" if is_md else "application/pdf"

            col_m1, col_m2 = st.columns([4, 1])
            with col_m1:
                st.markdown(f"{icon_doc} `{nama_file}`")
            with col_m2:
                try:
                    with open(file_path, "rb") as f:
                        st.download_button("⬇️", f, file_name=nama_file, mime=mime_doc, key=f"dl_{idx}_{nama_file}")
                except Exception:
                    pass
    else:
        st.info("Kurikulum Standar TJKT.")

    st.divider()

    with st.expander("📋 Identitas & Deskripsi Karya", expanded=False):
        st.markdown(f"""
        **Nama Karya:** RA'BUNG-NET AI  
        **Pembuat:** {NAMA_GURU}  
        **Satuan Pendidikan:** {ASAL_SEKOLAH}  
        **Kategori:** {KATEGORI_KARYA}  
        """)

    if st.button("🔄 Mulai Percakapan Baru", use_container_width=True):
        st.cache_data.clear()
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
        st.write("Kirimkan screenshot error, infografis, atau tanyakan materi praktikum TJKT di bawah ini!")
else:
    st.header("🤖 RA'BUNG-NET AI: Asisten Praktikum Jaringan & Server Linux")
    st.write("Kirimkan screenshot error, infografis, atau tanyakan materi praktikum TJKT di bawah ini!")

st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "text": "Halo Sobat TJKT! 👋 Saya **RA'BUNG-NET AI**. Silakan ketik pertanyaan atau lampirkan foto/file materi praktikum.",
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
            st.image(img_bytes, caption="Lampiran Gambar", width=350)
        if msg.get("files"):
            st.caption("📎 File: " + ", ".join(msg["files"]))
        if msg.get("display_text"):
            st.markdown(msg["display_text"])
        elif msg.get("text"):
            st.markdown(msg["text"])

# ==========================================
# 10. KOLOM CHAT & PEMROSESAN PESAN
# ==========================================
user_text = None
attached_files = []

try:
    chat_val = st.chat_input(
        "Ketik pertanyaan atau lampirkan foto/file...",
        accept_file="multiple",
        file_type=["png", "jpg", "jpeg", "webp", "pdf", "md", "txt", "conf", "rsc", "log"]
    )
    if chat_val:
        user_text = chat_val.text
        attached_files = chat_val.files if hasattr(chat_val, "files") and chat_val.files else []
except TypeError:
    with st.popover("➕ Lampirkan Foto/File"):
        fallback_files = st.file_uploader(
            "Pilih file:",
            type=["png", "jpg", "jpeg", "webp", "pdf", "md", "txt", "conf", "rsc", "log"],
            accept_multiple_files=True,
            key="fallback_uploader"
        )
    raw_prompt = st.chat_input("Ketik pertanyaan...")
    if raw_prompt or fallback_files:
        user_text = raw_prompt
        attached_files = fallback_files if fallback_files else []

if user_text or attached_files:
    image_bytes_list = []
    raw_image_names = []
    file_names_info = []
    extracted_docs_text = ""

    for f in attached_files:
        fname = getattr(f, "name", "lampiran")
        fname_lower = fname.lower()
        is_image_file = fname_lower.endswith((".png", ".jpg", ".jpeg", ".webp"))

        if is_image_file:
            try:
                img_bytes = convert_uploaded_image_to_jpeg_bytes(f)
                image_bytes_list.append(img_bytes)
                raw_image_names.append(os.path.splitext(fname)[0].replace("_", " ").replace("-", " "))
                file_names_info.append(f"🖼️ `{fname}`")
            except Exception as e:
                st.warning(f"Gagal memproses gambar {fname}: {e}")
        elif fname_lower.endswith(".pdf"):
            try:
                f.seek(0)
                reader = PdfReader(f)
                pdf_extracted = ""
                for p in reader.pages:
                    pdf_extracted += (p.extract_text() or "") + "\n"
                if pdf_extracted.strip():
                    extracted_docs_text += f"\n\n=== PDF ({fname}) ===\n{pdf_extracted[:3000]}\n"
                    file_names_info.append(f"📄 `{fname}`")
            except Exception as e:
                st.warning(f"Gagal membaca PDF: {e}")
        else:
            try:
                f.seek(0)
                txt_extracted = f.read().decode("utf-8", errors="ignore")
                if txt_extracted.strip():
                    extracted_docs_text += f"\n\n=== FILE ({fname}) ===\n```\n{txt_extracted[:3000]}\n```\n"
                    file_names_info.append(f"📝 `{fname}`")
            except Exception as e:
                st.warning(f"Gagal membaca file: {e}")

    display_text = user_text if user_text else "*[Mengirim lampiran]*"
    ai_prompt_text = user_text if user_text else "Tolong analisis lampiran ini secara lengkap."
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
            st.image(img_b, width=350)
        if file_names_info:
            st.caption("Lampiran: " + ", ".join(file_names_info))
        st.markdown(display_text)

    if not groq_keys and not gemini_keys and not os.environ.get("GEMINI_API_KEY"):
        with st.chat_message("assistant", avatar=assistant_avatar):
            st.error("⚠️ API Key belum diatur di Streamlit Secrets.")
    else:
        with st.chat_message("assistant", avatar=assistant_avatar):
            with st.spinner("RA'BUNG-NET AI sedang menyusun jawaban lengkap..."):
                try:
                    full_system_instruction = BASE_SYSTEM_PROMPT
                    if MODUL_TEXT.strip():
                        full_system_instruction += f"\n\nMODUL SEKOLAH:\n{MODUL_TEXT[:3500]}"

                    recent_messages = [dict(m) for m in st.session_state.messages[-3:]]
                    reply, used_engine = generate_multimodal_response(
                        groq_keys,
                        gemini_keys,
                        recent_messages,
                        full_system_instruction,
                        image_bytes_list=image_bytes_list,
                        image_names_list=raw_image_names
                    )

                    st.markdown(reply)
                    st.caption(f"⚡ Mesin: `{used_engine}`")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "text": reply,
                        "display_text": reply,
                        "images": [],
                        "files": []
                    })
                except Exception as e:
                    st.error("⏳ Maaf, terjadi kendala saat memproses.")
                    with st.expander("Detail Error"):
                        st.code(str(e))
