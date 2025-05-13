# ✅ Refactor vectorstore to Qdrant-based usage (DYNAMIC from settings)

import os
import streamlit as st
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from qdrant_client import QdrantClient
from llama_index.core.schema import Document

# ⚙️ Load Qdrant settings from session_state
QDRANT_HOST = st.session_state.get("qdrant_host", "localhost")
QDRANT_PORT = int(st.session_state.get("qdrant_port", 6333))
QDRANT_COLLECTION = st.session_state.get("qdrant_collection", "chatdb-index")

qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=QDRANT_COLLECTION,
)

embed_model = OpenAIEmbedding()

# 👉 Structure indexing
def index_structure(structure_data: list, collection_name="db_structure"):
    docs = [Document(text=str(item)) for item in structure_data]

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    vector_store = QdrantVectorStore(client=client, collection_name=collection_name)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_documents(
        docs,
        storage_context=storage_context,
        embed_model=embed_model,
    )
    index.storage_context.persist(persist_dir=".qdrant")
    return index

# 👉 File indexing
def index_uploaded_files(directory: str):
    documents = SimpleDirectoryReader(directory).load_data()
    index = VectorStoreIndex.from_documents(documents, vector_store=vector_store, embed_model=embed_model)
    index.storage_context.persist(persist_dir=".qdrant")

# 👉 Retrieval
def get_structural_retriever():
    return VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model).as_retriever()
