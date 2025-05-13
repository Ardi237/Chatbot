# agent.py (lanjutan dengan hybrid context)
import streamlit as st
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.retrievers import RouterRetriever, QueryFusionRetriever

from llama_index.core.query_engine import RetrieverQueryEngine


from common import Conversation, DatabaseProps
from multi_database import MultiDatabaseToolSpec, TrackingDatabaseToolSpec
from qdrant_client import QdrantClient


@st.cache_resource(show_spinner="🔁 Loading LLM...")
def get_llm(model: str, api_key: str):
    _ = api_key
    return OpenAI(model=model)


@st.cache_resource(show_spinner="🔗 Connecting to database...")
def get_database_spec(database_id: str) -> TrackingDatabaseToolSpec:
    database: DatabaseProps = st.session_state.databases[database_id]
    db_spec = TrackingDatabaseToolSpec(uri=database.uri)
    db_spec.set_database_name(database_id)
    return db_spec

def database_spec_handler(database: str, query: str, items: list):
    conversation = st.session_state.conversations[st.session_state.current_conversation]
    conversation.query_results_queue.append((database, query, items))


def load_structural_context_retriever():
    client = QdrantClient(url="http://localhost:6333")
    vector_store = QdrantVectorStore(client=client, collection_name="db_structure")
    index = VectorStoreIndex.from_vector_store(vector_store)
    return index.as_retriever(similarity_top_k=3)


def load_uploaded_file_retriever():
    client = QdrantClient(url="http://localhost:6333")
    vector_store = QdrantVectorStore(client=client, collection_name="uploaded_files")
    index = VectorStoreIndex.from_vector_store(vector_store)
    return index.as_retriever(similarity_top_k=3)


def get_hybrid_retriever():
    retriever1 = load_structural_context_retriever()
    retriever2 = load_uploaded_file_retriever()

    router = RouterRetriever(retrievers=[retriever1, retriever2])
    fusion = QueryFusionRetriever(retrievers=[retriever1, retriever2])
    return fusion

@st.cache_resource(show_spinner="🧠 Creating hybrid agent...")
def get_agent(conversation_id: str, last_update_timestamp: float, rag_mode: str = "combine"):
    _ = last_update_timestamp
    conversation: Conversation = st.session_state.conversations[conversation_id]

    # 🔧 Load DB tools
    database_tools = MultiDatabaseToolSpec(handler=database_spec_handler)
    for db_id in conversation.database_ids:
        db_spec = get_database_spec(db_id)
        database_tools.add_database_tool_spec(db_id, db_spec)

    tools = database_tools.to_tool_list()

    # 💬 History
    chat_history = [
        ChatMessage(role=m.role, content=m.content)
        for m in conversation.messages
    ]

    # ⚙️ LLM
    llm = get_llm(conversation.agent_model, st.session_state.openai_key)

    # 🔄 Load retriever by mode (combine, only-db, only-file)
    retriever_engine = get_retriever_by_mode(rag_mode)

    # 🤖 Build Agent
    return ReActAgent.from_tools(
        tools=tools,
        llm=llm,
        retriever=retriever_engine.retriever,
        chat_history=chat_history,
        verbose=True,
        max_iterations=10,
    )



def get_retriever_by_mode(rag_mode: str) -> RetrieverQueryEngine:
    client = QdrantClient(url="http://localhost:6333")

    if rag_mode == "only-db":
        vector_store = QdrantVectorStore(client=client, collection_name="db_structure")
        index = VectorStoreIndex.from_vector_store(vector_store)
        return index.as_query_engine()

    elif rag_mode == "only-file":
        vector_store = QdrantVectorStore(client=client, collection_name="uploaded_files")
        index = VectorStoreIndex.from_vector_store(vector_store)
        return index.as_query_engine()

    elif rag_mode == "combine":
        db_retriever = VectorStoreIndex.from_vector_store(
            QdrantVectorStore(client=client, collection_name="db_structure")
        ).as_retriever(similarity_top_k=3)

        file_retriever = VectorStoreIndex.from_vector_store(
            QdrantVectorStore(client=client, collection_name="uploaded_files")
        ).as_retriever(similarity_top_k=3)

        fusion = QueryFusionRetriever(retrievers=[db_retriever, file_retriever], mode="reciprocal_rerank")
        return RetrieverQueryEngine.from_args(fusion)

    else:
        raise ValueError(f"Unsupported RAG mode: {rag_mode}")