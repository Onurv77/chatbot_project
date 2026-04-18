"""
setup_rag.py — Tek seferlik çalıştır.
PDF'leri parçalar, Gemini embedding ile vektöre çevirir, embeddings.pkl olarak kaydeder.
Bu dosyayı GitHub'a commit etmeyi unutma!
"""

import os
import time
import pickle
import numpy as np
from pathlib import Path
from pypdf import PdfReader
from google import genai

# ── Ayarlar ──────────────────────────────────────────────────────────────────
DATA_FOLDER   = "Data"
OUTPUT_FILE   = "embeddings.pkl"
CHUNK_SIZE    = 800    # karakter — çok büyük olursa embedding kalitesi düşer
CHUNK_OVERLAP = 150    # parçalar arası örtüşme — bağlam sürekliliği için

# ── İstemci ──────────────────────────────────────────────────────────────────
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("❌ GEMINI_API_KEY ortam değişkeni tanımlı değil.")

client = genai.Client(api_key=api_key)

# ── Yardımcılar ───────────────────────────────────────────────────────────────
def extract_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join(
        page.extract_text() or "" for page in reader.pages
    )

def chunk_text(text: str, source: str) -> list[dict]:
    chunks = []
    start  = 0
    while start < len(text):
        end  = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if chunk:
            chunks.append({"text": chunk, "source": source})
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

def embed_batch(texts: list[str], retries=4, wait=20) -> list[list[float]]:
    """Gemini embedding-004 ile toplu embedding üret."""
    for attempt in range(retries):
        try:
            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=texts,
            )
            return [e.values for e in result.embeddings]
        except Exception as e:
            msg = str(e)
            if attempt < retries - 1 and any(
                c in msg for c in ["429", "503", "EXHAUSTED", "UNAVAILABLE"]
            ):
                print(f"   ⏳ Rate limit, {wait}s bekleniyor...")
                time.sleep(wait)
            else:
                raise

# ── Ana Akış ─────────────────────────────────────────────────────────────────
pdf_files = sorted(Path(DATA_FOLDER).glob("*.pdf"))
print(f"📁 {len(pdf_files)} PDF bulundu.\n")

all_chunks: list[dict] = []

# 1. PDF → metin → parça
for pdf_path in pdf_files:
    print(f"  📄 Parçalanıyor: {pdf_path.name}")
    text   = extract_text(str(pdf_path))
    chunks = chunk_text(text, source=pdf_path.name)
    all_chunks.extend(chunks)

print(f"\n✅ Toplam {len(all_chunks)} parça oluşturuldu.")
print("🔢 Embedding oluşturuluyor...\n")

# 2. Parçalar → embedding (20'li batch'ler)
BATCH = 20
vectors: list[list[float]] = []

for i in range(0, len(all_chunks), BATCH):
    batch_texts = [c["text"] for c in all_chunks[i : i + BATCH]]
    batch_vecs  = embed_batch(batch_texts)
    vectors.extend(batch_vecs)
    print(f"   {min(i + BATCH, len(all_chunks))}/{len(all_chunks)} parça işlendi...", end="\r")
    time.sleep(1)  # rate limit için

print(f"\n✅ {len(vectors)} embedding oluşturuldu.")

# 3. Kaydet
data = {
    "chunks":  all_chunks,                      # [{"text": ..., "source": ...}]
    "vectors": np.array(vectors, dtype="float32"),  # (N, 768)
}

with open(OUTPUT_FILE, "wb") as f:
    pickle.dump(data, f)

print(f"\n🎉 Kaydedildi: {OUTPUT_FILE}  ({Path(OUTPUT_FILE).stat().st_size // 1024} KB)")
print("\n⚠️  Bu dosyayı GitHub'a commit etmeyi unutma:")
print("   git add embeddings.pkl")
print("   git commit -m 'RAG embeddings eklendi'")
print("   git push")