from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from qdrant_client import QdrantClient
from llama_index.core.schema import Document

import streamlit as st

def get_qdrant_client():
    host = st.session_state.get("qdrant_host", "localhost")
    port = int(st.session_state.get("qdrant_port", 6333))
    return QdrantClient(host=host, port=port)

def get_embed_model():
    return OpenAIEmbedding()

# ✅ Structure indexing
def index_structure(structure_data: list, collection_name="db_structure"):
    docs = [Document(text=str(item)) for item in structure_data]
    client = get_qdrant_client()
    vector_store = QdrantVectorStore(client=client, collection_name=collection_name)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_documents(
        docs,
        storage_context=storage_context,
        embed_model=get_embed_model(),
    )
    index.storage_context.persist(persist_dir=".qdrant")
    return index

# ✅ File indexing
def index_uploaded_files(directory: str, collection_name="uploaded_files"):
    documents = SimpleDirectoryReader(directory).load_data()
    client = get_qdrant_client()
    vector_store = QdrantVectorStore(client=client, collection_name=collection_name)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=get_embed_model(),
    )
    index.storage_context.persist(persist_dir=".qdrant")
    return index

# ✅ Retrieval
def get_structural_retriever(collection_name="db_structure"):
    client = get_qdrant_client()
    vector_store = QdrantVectorStore(client=client, collection_name=collection_name)
    return VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=get_embed_model()
    ).as_retriever()
