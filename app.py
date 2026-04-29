import streamlit as st
import os
import time
import pickle
import re
import numpy as np
from google import genai


st.set_page_config(
    page_title="YU Student Assistant",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="expanded",
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
DATA_FOLDER = "data"


EMOTIONAL_KEYWORDS = [
    
    "kendimi kötü hissediyorum", "kötü hissediyorum", "çok kötüyüm",
    "mutsuzum", "çok üzgünüm", "ağlıyorum", "bunaldım", "bunalıyorum",
    "dayanamıyorum", "artık yapamıyorum", "bıkmak istiyorum",
    "kendime zarar", "intihar", "ölmek istiyorum", "yaşamak istemiyorum",
    "depresyon", "panik atak", "anksiyete", "kaygılanıyorum",
    "yalnız hissediyorum", "çaresizim", "umutsuzum",
    
    "feeling bad", "feel terrible", "i feel awful", "i'm not okay",
    "i am not okay", "feeling depressed", "want to hurt myself",
    "self harm", "suicide", "want to die", "can't go on",
    "feeling hopeless", "feeling alone", "anxiety attack", "panic attack",
]

EMOTIONAL_RESPONSE = """💙 Seni duyuyorum. Kendini kötü hissetmen çok önemli ve bunu paylaşman cesaret ister.

Ben bir akademik asistanım, bu konuda sana gerçekten yardımcı olacak kişiler değilim — ama seni doğru yere yönlendirebilirim:

---

**🧠 Yeditepe Üniversitesi Psikolojik Danışmanlık Merkezi**
Kampüs içinde, ücretsiz ve gizli destek alabilirsin.
📍 Rektörlük Binası — randevu veya yüz yüze başvuru

Lütfen bu adımlardan birini at. Yalnız değilsin. 🤍
"""


DOWNLOADABLE_DOCS = {
    "cap-yandal-kayit-formu.pdf",
    "ders_ekleme_birakma_cekilmeformu.pdf",
    "devlet-tesvik-formu.pdf",
    "erasmus-ogrenim-hareketliligi-basvuru-formu.pdf",
    "fazla_kredi_basvuru.pdf",
    "genel_dilekce.pdf",
    "isyeri_staj_degerlendirme_formu.pdf",
    "kayit_dondurma_dilekcesi.pdf",
    "lisans_mezuniyet_iliski_kesme_formu.pdf",
    "mali_onay_sebebiyle_gec_kayit_formu.pdf",
    "not_itiraz_formu.pdf",
    "ogrenci_belgesi_talep_formu.pdf",
    "ogrenci_staj_degerlendirme_formu.pdf",
    "sinirsiz_sinav_hakki_dilekcesi.pdf",
    "staj_basvuru_dilekcesi_2023.pdf",
    "stajyer_on_bilgi_formu_0.pdf",
    "tek_ders_sinavi_hakki_dilekcesi.pdf",
    "teslim_edilecek_evrak_listesi_1.pdf",
    "universitelerden_ders_alma_dilekcesi.pdf",
    "yaz_okulu_fazla_ders_basvuru_dilekcesi.pdf",
    "yaz_okulu_talep_formu.pdf",
    "yeni_kayit_sildirme_formu.pdf",
}

DISPLAY_NAMES = {
    "cap-yandal-kayit-formu.pdf":                     "ÇAP / Yandal Kayıt Formu",
    "ders_ekleme_birakma_cekilmeformu.pdf":            "Ders Ekleme / Bırakma / Çekilme Formu",
    "devlet-tesvik-formu.pdf":                         "Devlet Teşvik Formu",
    "erasmus-ogrenim-hareketliligi-basvuru-formu.pdf": "Erasmus Öğrenim Hareketliliği Başvuru Formu",
    "fazla_kredi_basvuru.pdf":                         "Fazla Kredi Başvuru Formu",
    "genel_dilekce.pdf":                               "Genel Dilekçe",
    "isyeri_staj_degerlendirme_formu.pdf":             "İşyeri Staj Değerlendirme Formu",
    "kayit_dondurma_dilekcesi.pdf":                    "Kayıt Dondurma Dilekçesi",
    "lisans_mezuniyet_iliski_kesme_formu.pdf":         "Mezuniyet / İlişik Kesme Formu",
    "mali_onay_sebebiyle_gec_kayit_formu.pdf":         "Mali Onay Geç Kayıt Formu",
    "not_itiraz_formu.pdf":                            "Not İtiraz Formu",
    "ogrenci_belgesi_talep_formu.pdf":                 "Öğrenci Belgesi Talep Formu",
    "ogrenci_staj_degerlendirme_formu.pdf":            "Öğrenci Staj Değerlendirme Formu",
    "sinirsiz_sinav_hakki_dilekcesi.pdf":              "Sınırsız Sınav Hakkı Dilekçesi",
    "staj_basvuru_dilekcesi_2023.pdf":                 "Staj Başvuru Dilekçesi",
    "stajyer_on_bilgi_formu_0.pdf":                    "Stajyer Ön Bilgi Formu",
    "tek_ders_sinavi_hakki_dilekcesi.pdf":             "Tek Ders Sınavı Hakkı Dilekçesi",
    "teslim_edilecek_evrak_listesi_1.pdf":             "Teslim Edilecek Evrak Listesi",
    "universitelerden_ders_alma_dilekcesi.pdf":        "Üniversitelerden Ders Alma Dilekçesi",
    "yaz_okulu_fazla_ders_basvuru_dilekcesi.pdf":      "Yaz Okulu Fazla Ders Başvuru Dilekçesi",
    "yaz_okulu_talep_formu.pdf":                       "Yaz Okulu Talep Formu",
    "yeni_kayit_sildirme_formu.pdf":                   "Yeni Kayıt Sildirme Formu",
}


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


with st.sidebar:
    st.image("https://yeditepe.edu.tr/themes/custom/yeditepe/logo.svg", width=180)
    st.markdown("### 🎓 Hızlı Erişim Portalı")
    st.info("Bu asistan, 32+ üniversite yönetmeliği ve belgesiyle eğitilmiştir.")

    st.markdown("#### 🔗 Önemli Bağlantılar")
    st.link_button("🌐 OBS (Öğrenci Bilgi Sistemi)", "https://obs.yeditepe.edu.tr", use_container_width=True)
    st.link_button("📚 Yulearn", "https://yulearn.yeditepe.edu.tr/login/index.php", use_container_width=True)
    st.link_button("🚌 Servis / Ring Saatleri", "https://yeditepe.edu.tr/tr/universitemiz-kampus-yeditepe/ulasim", use_container_width=True)
    st.link_button("📚 Akademik7", "https://a7.yeditepe.edu.tr/login?returnUrl=%2F", use_container_width=True)

    st.markdown("---")

    st.markdown("#### 💡 Popüler Aramalar")
    st.caption("- Erasmus başvuru şartları nedir?")
    st.caption("- Yaz okulunda kaç ders alabilirim?")
    st.caption("- Kayıt dondurma dilekçesi örneği.")
    st.caption("- Not itirazı nasıl yapılır?")

    st.markdown("---")
    if st.session_state.system_ready:
        st.success(f"✅ {len(st.session_state.rag_chunks)} Veri Bloğu Aktif")



def is_emotional(text: str) -> bool:
    """Return True if the message contains emotional distress signals."""
    lowered = text.lower()
    return any(kw in lowered for kw in EMOTIONAL_KEYWORDS)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-10)
    return b_norm @ a_norm


def retrieve(query: str, top_k: int = TOP_K) -> tuple[str, list[str]]:
    result = st.session_state.client.models.embed_content(
        model="gemini-embedding-001",
        contents=[query],
    )
    query_vec = np.array(result.embeddings[0].values, dtype="float32")
    scores    = cosine_similarity(query_vec, st.session_state.rag_vectors)
    top_idx   = np.argsort(scores)[::-1][:top_k]

    parts        = []
    seen_sources = []
    for idx in top_idx:
        chunk = st.session_state.rag_chunks[idx]
        parts.append(f"[Kaynak: {chunk['source']}]\n{chunk['text']}")

        source_name = chunk["source"]
        source_path = os.path.join(DATA_FOLDER, source_name)

        if (
            source_name not in seen_sources
            and source_name in DOWNLOADABLE_DOCS
            and os.path.exists(source_path)
        ):
            seen_sources.append(source_name)

    context = "\n\n---\n\n".join(parts)
    return context, seen_sources


def _display_name(filename: str) -> str:
    if filename in DISPLAY_NAMES:
        return DISPLAY_NAMES[filename]
    return os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()


def _render_source_buttons(sources: list[str]) -> None:
    if not sources:
        return
    st.markdown("---")
    st.caption("📎 **İlgili form / dilekçe — indirmek için tıklayın:**")
    for source in sources:
        path = os.path.join(DATA_FOLDER, source)
        try:
            with open(path, "rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                label=f"⬇️  {_display_name(source)}",
                data=pdf_bytes,
                file_name=source,
                mime="application/pdf",
                key=f"dl_{source}_{abs(hash(source + str(sources)))}",
            )
        except OSError:
            pass




st.markdown("""
<div class="hero">
    <img src="https://yeditepe.edu.tr/themes/custom/yeditepe/logo.svg" alt="Yeditepe Logo" class="hero-logo">
    <h1 class="hero-title">Student <em>Assistant</em></h1>
    <p class="hero-sub">Get instant answers about regulations, schedules, and scholarships.</p>
</div>
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
            model=os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview"),
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
                    "3. DOĞRULUK: Bilgi bağlamda yoksa uydurma. Kullanıcıya kendi dilinde "
                    "'Üniversite belgelerinde bu bilgiye ulaşamadım' anlamına gelen doğal bir cevap ver "
                    "(Örn: I couldn't find this information in the university documents).\n"
                    "4. DİL (KESİN KURAL): Kullanıcı hangi dilde soru sorarsa sorsun (İngilizce, Türkçe vb.), "
                    "belgeler Türkçe olsa dahi cevabını KESİNLİKLE kullanıcının soru sorduğu dilde ver.\n"
                    "5. KISALIK: Net ve öz ol, gereksiz uzatma.\n"
                    "6. DUYGUSAL MESAJLAR (KESİN KURAL): Kullanıcı kendini kötü, üzgün, bunalmış, "
                    "umutsuz hissettğini veya zarar verme/intihar gibi düşünceler yaşadığını belirtirse, "
                    "akademik bilgiye BAŞVURMA. Hiçbir form, yönetmelik veya prosedür bilgisi verme. "
                    "Sadece empatiyle yanıt ver ve Yeditepe Psikolojik Danışmanlık Merkezi ile "
                    "182 ruh sağlığı hattını yönlendir."
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
        <strong>{chunk_count} document chunks</strong> indexed.</div>
    </div>
    """, unsafe_allow_html=True)




for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("sources"):
            _render_source_buttons(message["sources"])




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


def handle_message(user_message: str) -> None:
    st.session_state.messages.append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.markdown(user_message)

    with st.chat_message("assistant"):
        
        if is_emotional(user_message):
            st.markdown(EMOTIONAL_RESPONSE)
            st.session_state.messages.append({
                "role":    "assistant",
                "content": EMOTIONAL_RESPONSE,
                "sources": [],
            })
            return

        
        placeholder = st.empty()
        placeholder.markdown("💭 _Thinking…_")
        try:
            context, sources = retrieve(user_message)
            prompt_text = f"[BAĞLAM]\n{context}\n\n[SORU]\n{user_message}"
            response    = st.session_state.chat.send_message(prompt_text)
            answer      = response.text

            placeholder.markdown(answer)
            _render_source_buttons(sources)

            st.session_state.messages.append({
                "role":    "assistant",
                "content": answer,
                "sources": sources,
            })
        except Exception as e:
            placeholder.error(f"Error: {e}")




if st.session_state.pending_question and st.session_state.system_ready:
    q = st.session_state.pending_question
    st.session_state.pending_question = None
    handle_message(q)




if len(st.session_state.messages) > 0:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️  Sohbeti Temizle", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # with col2:
    #     full_text = "YEDİTEPE ASİSTAN ÇIKTISI\n" + "="*30 + "\n\n"
    #     for msg in st.session_state.messages:
    #         full_text += f"{msg['role'].upper()}: {msg['content']}\n\n"
    #     st.download_button(
    #         label="📥 Dilekçeyi / Yanıtı İndir",
    #         data=full_text,
    #         file_name="yeditepe_asistan_cikti.txt",
    #         mime="text/plain",
    #         use_container_width=True
    #     )

st.markdown(
    '<div class="footer-note">AI can make mistakes — confirm important decisions '
    "with student affairs.</div>",
    unsafe_allow_html=True,
)