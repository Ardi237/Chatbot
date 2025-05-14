# 🤖 ChatDB – GPT-Powered SQL Assistant with Natural Language Interface

ChatDB adalah chatbot SQL cerdas berbasis GPT-4 Turbo yang dapat menjawab pertanyaan natural language terkait database Anda, mencari template SQL, menjalankan query ke banyak SQL Server, serta mendukung fitur Retrieval-Augmented Generation (RAG) untuk dokumentasi dan FAQ berbasis Qdrant Vector Store.

---

## 🚀 Kenapa Dibuat?

Proyek ini dibuat untuk menjawab kebutuhan:

- Membuat chatbot internal tim data tanpa perlu pelatihan model sendiri
- Mengubah pertanyaan manusia menjadi query SQL yang relevan
- Menyediakan jawaban dari dokumentasi, FAQ, dan tabel SQL aktual
- Mendukung banyak koneksi database dan user session

---

## 🛠️ Fitur Utama

- ✅ GPT-4 Turbo sebagai otak pengolahan bahasa
- ✅ Qdrant untuk pencarian dokumen vektor (RAG)
- ✅ Streamlit untuk antarmuka frontend yang interaktif
- ✅ Chatbot berbasis HTML juga tersedia
- ✅ Multi-Database SQL Execution
- ✅ Template SQL yang bisa dipakai ulang
- ✅ Dukungan FAQ untuk RAG berbasis teks
- ✅ Session-aware conversation dan filtering by user/table

---

## 📁 Struktur Proyek

├── 🏠_Home.py # Entry point Streamlit
├── app/
│ ├── main.py # FastAPI app entry (jika digunakan)
│ ├── routes/ # Endpoint modular (ask, index, faq)
│ ├── common/ # Session & conversation utils
│ └── schemas/ # Pydantic request schema
├── pages/ # Streamlit multipage (Chats, Settings)
├── data/ # Template & FAQ documents
├── templates/chat_ui.html # HTML chatbot UI
├── uploads/ # Upload user template CSV
├── sql_executor.py # Koneksi & eksekusi ke SQL
├── vector_indexer.py # Indexing ke Qdrant
├── file_indexer.py # File management untuk indexing
├── agent.py # Logic GPT: prompt + retrieval



---

## 🔁 Alur Kerja Pengguna

### 1. 🧾 Input Template (via `sql_templates.csv`)
| Kolom Wajib | Fungsi |
|-------------|--------|
| `label`     | Nama/nama intent |
| `template`  | SQL template dengan placeholder |
---

### 2. 💬 Pertanyaan Masuk

- User mengisi prompt di Streamlit Chat UI.
- Input dikirim ke router: `app/routes/ask.py`

### 3. 📚 Retrieval via Qdrant
Dokumen FAQ dan template di-index ke Qdrant

Hasil pencarian (relevant docs) digabung ke prompt GPT

Qdrant memungkinkan filtering metadata (db_target, label, dll)

### 4. 🧠 GPT Engine
Prompt dikirim ke GPT-4 Turbo

Bisa menghasilkan jawaban langsung atau query SQL

Jika query dihasilkan, langsung dieksekusi ke server SQL

### 5. 💡 Hasil
Dikirim ke frontend sebagai jawaban, hasil tabel, grafik, dsb.


⚙️ Cara Menjalankan
Karena koneksi DB dan API Key dilakukan via Streamlit input, tidak perlu .env.

1. Install docker untuk penggunaan Qdrant
install docker dekstop -> Login -> sudo docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
2. Instalasi
pip install -r requirements.txt
3. Jalankan Streamlit
streamlit run 🏠_Home.py



```python
@router.post("/ask")
def ask_router(request: AskRequest):
    # a) Ambil embeddings dari pertanyaan
    # b) Cari dokumen terkait (FAQ, template)
    # c) Generate prompt → kirim ke OpenAI
    # d) Eksekusi SQL jika relevan
    # e) Kirim jawaban

