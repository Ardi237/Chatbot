from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

import os
import re
import difflib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ────────────────────────────────────────────────
# Vector Store Indexing
# ────────────────────────────────────────────────
def index_uploaded_files(folder_path="uploads", collection_name="uploaded_files"):
    documents = SimpleDirectoryReader(folder_path).load_data()
    client = QdrantClient(url="http://localhost:6333")
    vector_store = QdrantVectorStore(client=client, collection_name=collection_name)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=OpenAIEmbedding(),
    )
    return index

# ────────────────────────────────────────────────
# Normalization
# ────────────────────────────────────────────────
def clean_question(q: str) -> str:
    q = q.lower().strip()
    q = re.sub(r"[^\w\s]", "", q)  # hapus tanda baca
    q = re.sub(r"\s+", " ", q)     # hapus spasi berlebih
    return q

# ────────────────────────────────────────────────
# FAQ Matching (TF-IDF)
# ────────────────────────────────────────────────
faq_list = []
faq_vectorizer = None
faq_vectors = None

def load_faq_txt(folder_path="data/faq_docs/"):
    global faq_list, faq_vectorizer, faq_vectors
    faq_list = []

    if not os.path.exists(folder_path):
        print(f"[FAQ Loader] Folder tidak ditemukan: {folder_path}")
        return

    for filename in os.listdir(folder_path):
        if not filename.endswith(".txt"):
            continue

        filepath = os.path.join(folder_path, filename)
        try:
            with open(filepath, encoding="utf-8") as f:
                entries = f.read().strip().split("\n\n")
                for i, entry in enumerate(entries):
                    if not entry.strip():
                        continue
                    match = re.match(r"Q:\s*(.+?)\nA:\s*(.+)", entry.strip(), re.DOTALL)
                    if match:
                        question, answer = match.groups()
                        cleaned = clean_question(question)
                        faq_list.append((cleaned, answer.strip()))
                    else:
                        print(f"[FAQ Parser] ⚠️ Format salah di '{filename}' blok #{i+1}")
        except Exception as e:
            print(f"[FAQ Parser] ❌ Error membaca '{filename}': {e}")

    if not faq_list:
        print("[FAQ Parser] ⚠️ Tidak ada QA valid ditemukan.")
        return

    questions = [q for q, _ in faq_list]
    faq_vectorizer = TfidfVectorizer()
    faq_vectors = faq_vectorizer.fit_transform(questions)
    print(f"[FAQ Loader] ✅ {len(faq_list)} QA dimuat dari {folder_path}")

def match_faq_answer(user_input: str, threshold: float = 0.7) -> str | None:
    global faq_list, faq_vectorizer, faq_vectors

    if not faq_list or faq_vectorizer is None or faq_vectors is None or faq_vectors.shape[0] == 0:
        load_faq_txt()

    if not faq_list or faq_vectors.shape[0] == 0:
        return None

    user_input_cleaned = clean_question(user_input)
    user_vec = faq_vectorizer.transform([user_input_cleaned])
    similarities = cosine_similarity(user_vec, faq_vectors).flatten()

    best_idx = similarities.argmax()
    if similarities[best_idx] >= threshold:
        return faq_list[best_idx][1]

    return None

# ────────────────────────────────────────────────
# SQL Template Matching (.csv + similarity)
# ────────────────────────────────────────────────
sql_templates = {}

def load_sql_templates(path="data/sql_templates.csv"):
    global sql_templates
    sql_templates = {}

    try:
        df = pd.read_csv(path)

        if "question" in df.columns and "sql_query" in df.columns:
            print("[SQL Templates] ✅ Menggunakan header")
            questions = df["question"]
            queries = df["sql_query"]
        else:
            print("[SQL Templates] ⚠️ Header tidak ditemukan, pakai kolom 0 & 1")
            df = pd.read_csv(path, header=None)
            if df.shape[1] < 2:
                raise ValueError("CSV minimal harus punya 2 kolom.")
            questions = df[0]
            queries = df[1]

        for q, sql in zip(questions, queries):
            cleaned = clean_question(str(q))
            sql_templates[cleaned] = str(sql).strip()

        print(f"[SQL Templates] ✅ Total template dimuat: {len(sql_templates)}")

    except FileNotFoundError:
        print("[SQL Templates] ❌ File tidak ditemukan.")
    except Exception as e:
        print(f"[SQL Templates] ❌ Error: {e}")
        sql_templates = {}

def match_sql_template(user_input: str, threshold: float = 0.8) -> str | None:
    global sql_templates
    if not sql_templates:
        load_sql_templates()

    if not sql_templates:
        return None

    user_input_cleaned = clean_question(user_input)
    best_match = difflib.get_close_matches(user_input_cleaned, sql_templates.keys(), n=1, cutoff=threshold)

    if best_match:
        template_key = best_match[0]
        raw_sql = sql_templates[template_key]

        # Substitusi parameter dinamis
        if "{policy_number}" in raw_sql:
            policy_number = extract_policy_number(user_input)
            if policy_number:
                return raw_sql.replace("{policy_number}", policy_number)
            else:
                return None  # gagal ekstrak ID

        return raw_sql

    return None


def extract_policy_number(prompt: str) -> str | None:
    match = re.search(r"(polis|policy)(\s+no\.?|\s+number)?\s*([A-Za-z0-9\-]+)", prompt, re.IGNORECASE)
    if match:
        return match.group(3).upper()
    return None
