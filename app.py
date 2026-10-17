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

NAMA_GURU = "Nama Anda, S.Kom., Gr."
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
# 6. FUNGSI HYBRID AI (GROQ + GOOGLE GEMINI)
# ==========================================
def generate_hybrid_response(groq_key_list, gemini_key_list, chat_messages, system_instruction):
    last_error = None

    # LAPIS 1: COBA GROQ TERLEBIH DAHULU
    if groq_key_list:
        g_keys = list(groq_key_list)
        random.shuffle(g_keys)

        groq_payload = [{"role": "system", "content": system_instruction}]
        for m in chat_messages:
            role = "user" if m["role"] == "user" else "assistant"
            groq_payload.append({"role": role, "content": m["content"]})

        groq_models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "qwen-qwq-32b",
            "gemma2-9b-it"
        ]

        for k in g_keys:
            try:
                client = Groq(api_key=k)
                for model_name in groq_models:
                    try:
                        completion = client.chat.completions.create(
                            model=model_name,
                            messages=groq_payload,
                            temperature=0.3,
                            max_tokens=2048,
                        )
                        reply_text = completion.choices[0].message.content
                        if reply_text:
                            return reply_text, f"Groq ({model_name})"
                    except Exception as e:
                        last_error = e
                        continue
            except Exception as e:
                last_error = e

    # LAPIS 2: CADANGAN OTOMATIS KE GOOGLE GEMINI
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

        gemini_priority = [
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash-lite",
            "gemma-3-27b-it",
            "gemma-3-12b-it",
            "gemini-3.1-flash-lite-preview",
            "gemini-3-flash-preview",
            "gemini-3.8-flash"
        ]

        for k in gem_keys:
