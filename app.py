import streamlit as st
import os
import time
from google import genai

# 1. Sayfa Ayarları
st.set_page_config(page_title="Üniversite Asistanı", page_icon="🎓", layout="centered")
st.title("🎓 Yeditepe Üniversitesi Öğrenci Asistanı")
st.caption("Üniversite yönetmelikleri, takvimleri ve bursları hakkında sorularınızı yanıtlayan yapay zeka.")

# 2. Hafıza (Session State) Başlatma
if "chat" not in st.session_state:
    st.session_state.chat = None
    st.session_state.messages = []       
    st.session_state.docs_ready = False  
    st.session_state.client = None 

# 3. Arka Planda Belgeleri Yükleme
if not st.session_state.docs_ready:
    with st.spinner("Sistem hazırlanıyor... Üniversite belgeleri yapay zekaya öğretiliyor (Bu işlem 30-40 saniye sürebilir)..."):
        try:
            st.session_state.client = genai.Client(api_key="AIzaSyAY_zlnp3BP50Y0BOFJOhX_y1yDmVN-uP8")
            
            data_folder = "Data"
            uploaded_files = []
            
            for file_name in os.listdir(data_folder):
                if file_name.endswith(".pdf"):
                    file_path = os.path.join(data_folder, file_name)
                    file_ref = st.session_state.client.files.upload(file=file_path)
                    uploaded_files.append(file_ref)
                    time.sleep(1)
            
            # MODELİ SENİN İSTEDİĞİN GİBİ YAPTIK AMA KURALLARI ÇOK SERTLEŞTİRDİK
            chat_session = st.session_state.client.chats.create(
                model='gemini-3-flash-preview',
                config={
                    'system_instruction': (
                        "Sen Yeditepe Üniversitesi'nin resmi rehber asistanısın. "
                        "Sana sunulan yönetmelik, takvim, form ve burs dökümanlarına tam hakimsin. "
                        "KURALLAR:\n"
                        "1. TASLAK OLUŞTURMA: Öğrenci bir dilekçe veya form örneği isterse ASLA 'web sitesine gidin' veya 'formu doldurun' deme. Dökümanlardaki formata bakarak öğrencinin direkt kopyalayıp boşlukları doldurabileceği (isim, numara, tarih, imza alanları olan) tam bir dilekçe metni yaz.\n"
                        "2. TEKRAR YASAĞI: SADECE KULLANICININ O AN SORDUĞU SORUYA CEVAP VER. Asla önceki sohbet geçmişini veya eski cevaplarını yeni cevabının içine kopyalama.\n"
                        "3. DOĞRULUK: İstenilen bilgi dökümanlarda yoksa uydurma, 'Üniversite dökümanlarında bu bilgiye ulaşamadım' de."
                    )
                }
            )
            
            st.session_state.chat = chat_session
            st.session_state.uploaded_files = uploaded_files
            st.session_state.docs_ready = True
            st.success("Tüm sistem hazır! Aşağıdan sorunuzu sorabilirsiniz.")
            
        except Exception as e:
            st.error(f"Sistem başlatılırken hata oluştu: {e}")

# 4. Geçmiş Mesajları Ekranda Gösterme
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Kullanıcıdan Soru Alma ve Cevaplama
if user_message := st.chat_input("Örn: Tek ders sınavı için dilekçe örneği yazar mısın?"):
    
    st.chat_message("user").markdown(user_message)
    st.session_state.messages.append({"role": "user", "content": user_message})

    with st.chat_message("assistant"):
        with st.spinner("Dökümanlar taranıyor..."):
            try:
                if len(st.session_state.messages) == 1:
                    prompt_content = st.session_state.uploaded_files + [user_message]
                else:
                    prompt_content = user_message
                    
                response = st.session_state.chat.send_message(prompt_content)
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                
            except Exception as e:
                st.error(f"Bağlantı hatası: {e}")