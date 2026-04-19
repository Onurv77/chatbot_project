# .gitignore
import streamlit as st
import os
import time
from google import genai

# ── Sayfa Ayarları ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="YÜ Öğrenci Asistanı",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS Yükle (style.css'den oku) ────────────────────────────────────────────
def load_css(path: str):
    with open(path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("assets/style.css")

# ── Sık Sorulan Sorular ──────────────────────────────────────────────────────
QUICK_QUESTIONS = [
    ("📅", "Akademik takvimde final sınavları ne zaman başlıyor?"),
    ("💰", "Burs için başvuru şartları nelerdir?"),
    ("📄", "Tek ders sınavı için nasıl dilekçe yazmalıyım?"),
    ("🔄", "Ders muafiyeti için hangi adımları izlemeliyim?"),
    ("📋", "Kayıt silme / çıkarma süreci nasıl işliyor?"),
    ("🎓", "Çift anadal veya yandal başvurusu nasıl yapılır?"),
]

# ── Session State ────────────────────────────────────────────────────────────
defaults = {
    "chat": None,
    "messages": [],
    "docs_ready": False,
    "client": None,
    "uploaded_files": [],
    "pending_question": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Yardımcı: Retry ile mesaj gönder ─────────────────────────────────────────
def send_with_retry(chat, prompt, max_retries: int = 4, wait: int = 25):
    """503 / 429 hatalarında otomatik yeniden dener."""
    for attempt in range(max_retries):
        try:
            return chat.send_message(prompt)
        except Exception as e:
            msg = str(e)
            if attempt < max_retries - 1 and ("503" in msg or "429" in msg or "UNAVAILABLE" in msg or "EXHAUSTED" in msg):
                time.sleep(wait)
            else:
                raise

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-badge">Yeditepe Üniversitesi</div>
    <h1 class="hero-title">Öğrenci <em>Asistanı</em></h1>
    <p class="hero-sub">Yönetmelikler, takvimler ve burslar hakkında anında yanıt alın.</p>
</div>
""", unsafe_allow_html=True)

# ── Belge Yükleme ─────────────────────────────────────────────────────────────
if not st.session_state.docs_ready:
    st.markdown("""
    <div class="status-card">
        <div class="status-dot loading"></div>
        <div class="status-text">Üniversite belgeleri yükleniyor,
        <strong>lütfen bekleyin…</strong></div>
    </div>
    """, unsafe_allow_html=True)

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            st.error("GEMINI_API_KEY ortam değişkeni tanımlı değil.")
            st.stop()

        st.session_state.client = genai.Client(api_key=api_key)

        data_folder = "Data"
        uploaded_files = []
        for file_name in sorted(os.listdir(data_folder)):
            if file_name.endswith(".pdf"):
                file_path = os.path.join(data_folder, file_name)
                file_ref = st.session_state.client.files.upload(file=file_path)
                uploaded_files.append(file_ref)
                time.sleep(1)

        chat_session = st.session_state.client.chats.create(
            model="gemini-3-flash-preview",
            config={
                "system_instruction": (
                    "Sen Yeditepe Üniversitesi'nin resmi rehber asistanısın. "
                    "Sana sunulan yönetmelik, takvim, form ve burs dökümanlarına tam hakimsin.\n\n"
                    "KURALLAR:\n"
                    "1. TASLAK OLUŞTURMA: Öğrenci dilekçe veya form isterse dökümanlardaki "
                    "formata uygun, isim/numara/tarih/imza alanları içeren eksiksiz bir metin yaz. "
                    "Asla 'web sitesine gidin' deme.\n"
                    "2. SADECE SORULAN SORUYA CEVAP VER: Önceki cevapları tekrarlama.\n"
                    "3. DOĞRULUK: Bilgi dökümanlarda yoksa 'Üniversite dökümanlarında bu bilgiye "
                    "ulaşamadım.' de, uydurma.\n"
                    "4. DİL: Her zaman akıcı, samimi ve profesyonel Türkçe kullan.\n"
                    "5. KISALIK: Cevaplarını gereksiz uzatma, net ve öz ol."
                )
            },
        )

        st.session_state.chat = chat_session
        st.session_state.uploaded_files = uploaded_files
        st.session_state.docs_ready = True
        st.rerun()

    except Exception as e:
        st.error(f"Sistem başlatılırken hata oluştu: {e}")
        st.stop()

# ── Sistem Hazır Durum Kartı ──────────────────────────────────────────────────
else:
    doc_count = len(st.session_state.uploaded_files)
    st.markdown(f"""
    <div class="status-card">
        <div class="status-dot"></div>
        <div class="status-text">Sistem hazır —
        <strong>{doc_count} belge</strong> yüklendi</div>
    </div>
    """, unsafe_allow_html=True)

# ── Geçmiş Mesajları Göster ───────────────────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Hızlı Sorular (sadece sohbet henüz boşsa göster) ─────────────────────────
if st.session_state.docs_ready and len(st.session_state.messages) == 0:
    st.markdown('<div class="quick-label">Sık sorulan sorular</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, (icon, question) in enumerate(QUICK_QUESTIONS):
        with cols[i % 2]:
            if st.button(f"{icon}  {question}", key=f"quick_{i}"):
                st.session_state.pending_question = question
                st.rerun()

# ── Cevap Üretme Fonksiyonu ───────────────────────────────────────────────────
def handle_message(user_message: str):
    """Kullanıcı mesajını sohbete ekler, modelden cevap alır, ekrana yazar."""
    # Kullanıcı balonunu ekle
    st.session_state.messages.append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.markdown(user_message)

    # Asistan cevabı
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("⏳ _Dökümanlar taranıyor…_")
        try:
            # Sadece ilk gerçek mesajda PDF'leri bağlama ekle
            is_first = len(st.session_state.messages) == 1
            prompt = (st.session_state.uploaded_files + [user_message]) if is_first else user_message

            response = send_with_retry(st.session_state.chat, prompt)
            answer = response.text
            placeholder.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

        except Exception as e:
            placeholder.error(f"Hata: {e}")

# ── Bekleyen Hızlı Soruyu İşle ───────────────────────────────────────────────
if st.session_state.pending_question and st.session_state.docs_ready:
    q = st.session_state.pending_question
    st.session_state.pending_question = None
    handle_message(q)

# ── Serbest Soru (Chat Input) ─────────────────────────────────────────────────
if prompt := st.chat_input("Sorunuzu yazın…"):
    if st.session_state.docs_ready:
        handle_message(prompt)
    else:
        st.warning("Sistem henüz hazır değil, lütfen bekleyin.")

# ── Sohbeti Temizle ───────────────────────────────────────────────────────────
if len(st.session_state.messages) > 0:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    if st.button("🗑️  Sohbeti temizle", key="clear"):
        st.session_state.messages = []
        st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="footer-note">Yapay zeka hata yapabilir — önemli kararlar için '
    "öğrenci işleri ile teyit edin.</div>",
    unsafe_allow_html=True,
)