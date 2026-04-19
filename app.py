import streamlit as st
import os
import time
import pickle
import numpy as np
from google import genai


st.set_page_config(
    page_title="YU Student Assistant",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)


def load_css(path: str):
    with open(path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("assets/style.css")


QUICK_QUESTIONS = [
    ("📅", "Akademik takvimde final sınavları ne zaman başlıyor?"),
    ("💰", "Burs için başvuru şartları nelerdir?"),
    ("📄", "Tek ders sınavı için nasıl dilekçe yazmalıyım?"),
    ("🔄", "Ders muafiyeti için hangi adımları izlemeliyim?"),
    ("📋", "Kayıt silme / çıkarma süreci nasıl işliyor?"),
    ("🎓", "Çift anadal veya yandal başvurusu nasıl yapılır?"),
]

TOP_K = 5  


defaults = {
    "chat": None,
    "messages": [],
    "system_ready": False,
    "client": None,
    "rag_chunks": None,
    "rag_vectors": None,
    "pending_question": None,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
    return b_norm @ a_norm

def retrieve(query: str, top_k: int = TOP_K) -> str:
    result = st.session_state.client.models.embed_content(
        model="gemini-embedding-001",
        contents=[query],
    )
    query_vec = np.array(result.embeddings[0].values, dtype="float32")
    scores    = cosine_similarity(query_vec, st.session_state.rag_vectors)
    top_idx   = np.argsort(scores)[::-1][:top_k]

    parts = []
    for idx in top_idx:
        chunk = st.session_state.rag_chunks[idx]
        parts.append(f"[Kaynak: {chunk['source']}]\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def send_with_retry(chat, prompt, max_retries=4, wait=25):
    for attempt in range(max_retries):
        try:
            return chat.send_message(prompt)
        except Exception as e:
            msg = str(e)
            if attempt < max_retries - 1 and any(
                c in msg for c in ["503", "429", "UNAVAILABLE", "EXHAUSTED"]
            ):
                time.sleep(wait)
            else:
                raise


st.markdown("""
            <div class="hero">
    <img src="https://yeditepe.edu.tr/themes/custom/yeditepe/logo.svg" alt="Yeditepe Logo" class="hero-logo">    
    <!--<div class="hero-badge">Yeditepe University</div>-->
    <h1 class="hero-title">Student <em>Assistant</em></h1>
    <p class="hero-sub">Get instant answers about regulations, schedules, and scholarships.</p></div>
    """, unsafe_allow_html=True)


if not st.session_state.system_ready:
    st.markdown("""
    <div class="status-card">
        <div class="status-dot loading"></div>
        <div class="status-text">The system is being prepared,
        <strong>Please wait…</strong></div>
    </div>
    """, unsafe_allow_html=True)

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            st.error("The GEMINI_API_KEY environment variable is not defined.")
            st.stop()

        client = genai.Client(api_key=api_key)
        st.session_state.client = client

        
        if not os.path.exists("embeddings.pkl"):
            st.error("embeddings.pkl not found.")
            st.stop()

        with open("embeddings.pkl", "rb") as f:
            data = pickle.load(f)

        st.session_state.rag_chunks  = data["chunks"]
        st.session_state.rag_vectors = data["vectors"]

        
        chat_session = client.chats.create(
            model="gemini-2.5-flash", #gemini-3-flash-preview gemini-3.1-flash-lite-preview gemini-2.5-flash
            config={
                "system_instruction": (
                    "Sen Yeditepe Üniversitesi'nin resmi rehber asistanısın.\n\n"
                    "Her mesajda sana [BAĞLAM] başlığı altında üniversite belgelerinden "
                    "ilgili parçalar verilecek. Belgeler Türkçe olsa bile, SADECE bu parçalardaki bilgileri kullan.\n\n"
                    "KURALLAR:\n"
                    "1. TASLAK OLUŞTURMA: Öğrenci dilekçe veya form isterse, "
                    "belgelerdeki formata uygun, isim/numara/tarih/imza alanları içeren "
                    "eksiksiz bir metin yaz. Asla 'web sitesine gidin' deme.\n"
                    "2. SADECE SORULAN SORUYA CEVAP VER: Önceki cevapları tekrarlama.\n"
                    "3. DOĞRULUK: Bilgi bağlamda yoksa uydurma. Kullanıcıya kendi dilinde 'Üniversite belgelerinde bu bilgiye ulaşamadım' anlamına gelen doğal bir cevap ver (Örn: I couldn't find this information in the university documents).\n"
                    "4. DİL (KESİN KURAL): Kullanıcı hangi dilde soru sorarsa sorsun (İngilizce, Türkçe vb.), belgeler Türkçe olsa dahi cevabını KESİNLİKLE kullanıcının soru sorduğu dilde ver.\n"
                    "5. KISALIK: Net ve öz ol, gereksiz uzatma."
                )
            },
        )

        st.session_state.chat = chat_session
        st.session_state.system_ready = True
        st.rerun()

    except Exception as e:
        st.error(f"An error occurred while starting the system: {e}")
        st.stop()


else:
    chunk_count = len(st.session_state.rag_chunks)
    st.markdown(f"""
    <div class="status-card">
        <div class="status-dot"></div>
        <div class="status-text">The system is ready —
        <strong>{chunk_count} The document fragment</strong> has been indexed.</div>
    </div>
    """, unsafe_allow_html=True)


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


prompt = st.chat_input("Write your question…")
if prompt:
    if st.session_state.system_ready:
        st.session_state.pending_question = prompt
    else:
        st.warning("The system is not yet ready, please wait.")


show_faq = (
    st.session_state.system_ready
    and len(st.session_state.messages) == 0
    and not st.session_state.pending_question
)

if show_faq:
    st.markdown('<div class="quick-label">FAQ</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, (icon, question) in enumerate(QUICK_QUESTIONS):
        with cols[i % 2]:
            if st.button(f"{icon}  {question}", key=f"quick_{i}"):
                st.session_state.pending_question = question
                st.rerun()


def handle_message(user_message: str):
    st.session_state.messages.append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.markdown(user_message)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("⏳ _The documents are being scanned…_")
        try:
            context = retrieve(user_message)
            prompt_text  = f"[BAĞLAM]\n{context}\n\n[SORU]\n{user_message}"
            response = send_with_retry(st.session_state.chat, prompt_text)
            answer   = response.text
            placeholder.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            placeholder.error(f"Error: {e}")


if st.session_state.pending_question and st.session_state.system_ready:
    q = st.session_state.pending_question
    st.session_state.pending_question = None  
    handle_message(q)


if len(st.session_state.messages) > 0:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    if st.button("🗑️  Clear the chat", key="clear"):
        st.session_state.messages = []
        st.rerun()

st.markdown(
    '<div class="footer-note">AI can make mistakes — confirm important decisions '
    "with student affairs.</div>",
    unsafe_allow_html=True,
)