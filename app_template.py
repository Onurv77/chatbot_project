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
    # ÇÖZÜM BURADA: Client (Bağlantı) objesini de hafızaya alıyoruz ki kapanmasın
    st.session_state.client = None 

# 3. Arka Planda Belgeleri Yükleme
if not st.session_state.docs_ready:
    with st.spinner("Sistem hazırlanıyor... Üniversite belgeleri yapay zekaya öğretiliyor (Bu işlem 30-40 saniye sürebilir)..."):
        try:
            # Client'ı doğrudan hafızanın içine kuruyoruz
            st.session_state.client = genai.Client(api_key="AIzaSyAY_zlnp3BP50Y0BOFJOhX_y1yDmVN-uP8")
            
            data_folder = "Data"
            uploaded_files = []
            
            # Belgeleri okutma
            for file_name in os.listdir(data_folder):
                if file_name.endswith(".pdf"):
                    file_path = os.path.join(data_folder, file_name)
                    # Dosya yüklerken hafızadaki client'ı kullanıyoruz
                    file_ref = st.session_state.client.files.upload(file=file_path)
                    uploaded_files.append(file_ref)
                    time.sleep(1)
            
            # Sohbet oturumunu başlatma
            chat_session = st.session_state.client.chats.create(
                model='gemini-3-flash-preview',
                config={
                    'system_instruction': (
                        "Sen Yeditepe Üniversitesi'nin resmi rehber asistanısın. "
                        "Sana sunulan yönetmelik, takvim, form ve burs dökümanlarına tam hakimsin. "
                        "Öğrencilere sadece bu dökümanlardaki resmi bilgileri kullanarak cevap ver. "
                        "Eğer istenilen bilgi sana verdiğim dökümanlarda yoksa 'Üniversite dökümanlarında bu bilgiye ulaşamadım' de."
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
if user_message := st.chat_input("Örn: Kaydımı sildirmek için ne yapmalıyım?"):
    
    st.chat_message("user").markdown(user_message)
    st.session_state.messages.append({"role": "user", "content": user_message})

    with st.chat_message("assistant"):
        with st.spinner("Dökümanlar taranıyor..."):
            try:
                if len(st.session_state.messages) == 1:
                    prompt_content = st.session_state.uploaded_files + [user_message]
                else:
                    prompt_content = user_message
                    
                # Hafızadaki chat üzerinden mesaj gönderiyoruz
                response = st.session_state.chat.send_message(prompt_content)
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                
            except Exception as e:
                st.error(f"Bağlantı hatası: {e}")