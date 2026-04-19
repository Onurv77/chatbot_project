# .gitignore
import os
import time
from google import genai

# İstemci bağlantısı
client = genai.Client(api_key="AIzaSyAY_zlnp3BP50Y0BOFJOhX_y1yDmVN-uP8")

# 1. Belgeleri Otomatik Yükleme
data_folder = "data"
uploaded_files = []

print(f"'{data_folder}' klasöründeki belgeler taranıyor...")

# Klasördeki her dosyayı döngüyle yüklüyoruz
for file_name in os.listdir(data_folder):
    if file_name.endswith(".pdf"):
        file_path = os.path.join(data_folder, file_name)
        print(f"Yükleniyor: {file_name}...")
        
        # Dosyayı Google sunucusuna gönderiyoruz
        file_ref = client.files.upload(file=file_path)
        uploaded_files.append(file_ref)
        
        # API limitine (429 hatası) takılmamak için 1 saniye bekleyelim
        time.sleep(1)

print(f"\nToplam {len(uploaded_files)} belge 'bilinçaltına' işlendi.")

# 2. Sohbet Oturumunu Kurma
# Botun her zaman üniversite kurallarını bilen profesyonel bir asistan olduğunu söylüyoruz
chat = client.chats.create(
    model='gemini-3-flash-preview',
    config={
        'system_instruction': (
            "Sen kapsamlı bir üniversite rehber asistanısın. Sana sunulan akademik takvim, "
            "burs yönetmeliği ve ders muafiyeti gibi tüm dökümanlara tam hakimsin. "
            "Öğrencilere sadece bu dökümanlardaki resmi bilgileri kullanarak cevap ver. "
            "Bilgi dökümanlarda yoksa uydurma, 'Üniversite dökümanlarında bu bilgiye ulaşamadım' de."
        )
    }
)

print("\n--- Üniversite Uzman Botu Hazır! ---")

# 3. Sohbet Döngüsü
while True:
    user_message = input("\nSoru Sorun: ")
    
    if user_message.lower() in ["exit", "quit", "kapat"]:
        break
        
    try:
        # Mesajı gönderirken TÜM yüklü dosyaları içeriğe ekliyoruz
        # Gemini-2.0-flash aynı anda birçok dosyayı bağlam olarak kabul edebilir
        prompt_content = uploaded_files + [user_message]
        
        response = chat.send_message(prompt_content)
        
        print(f"\nBot: {response.text}")
        print("-" * 40)
        
    except Exception as e:
        print(f"Hata: {e}")
        # Hata durumunda 1 dakika beklemeyi unutma (Kota dolmuş olabilir)