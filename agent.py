import streamlit as st
import logging
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI
# from llama_index.storage.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.base.llms.types import ChatMessage

from common import Conversation, DatabaseProps
from multi_database import MultiDatabaseToolSpec, TrackingDatabaseToolSpec


@st.cache_resource(show_spinner="🔁 Loading LLM...")
def get_llm(model: str, api_key: str):
    """Load OpenAI LLM. Cache invalidates on API key change."""
    _ = api_key  # triggers cache invalidation
    return OpenAI(model=model)


@st.cache_resource(show_spinner="🔗 Connecting to database...")
def get_database_spec(database_id: str) -> TrackingDatabaseToolSpec:
    """Returns a tool spec object for a specific database."""
    database: DatabaseProps = st.session_state.databases[database_id]

    db_spec = TrackingDatabaseToolSpec(uri=database.uri)
    db_spec.set_database_name(database_id)

    return db_spec


def database_spec_handler(database: str, query: str, items: list):
    """Tracks the executed query + results into current conversation's history."""
    conversation = st.session_state.conversations[st.session_state.current_conversation]
    conversation.query_results_queue.append((database, query, items))


@st.cache_resource(show_spinner="🤖 Creating agent...")
def get_agent(conversation_id: str, last_update_timestamp: float):
    """
    Create a new ReActAgent instance based on selected databases.
    Cache automatically refreshes when database/tools change.
    """
    _ = last_update_timestamp  # used only to force cache refresh

    conversation: Conversation = st.session_state.conversations[conversation_id]

    # Create tools from databases
    database_tools = MultiDatabaseToolSpec(handler=database_spec_handler)
    for db_id in conversation.database_ids:
        db_spec = get_database_spec(db_id)
        database_tools.add_database_tool_spec(db_id, db_spec)

    tools = database_tools.to_tool_list()

    # Load previous chat history
    chat_history = [
        ChatMessage(role=msg.role, content=msg.content)
        for msg in conversation.messages
    ]

    # context_str = load_structural_context()
    # chat_history.insert(0, ChatMessage(role="system", content=f"Berikut ini struktur database dan relasi antar tabel:\n\n{context_str}"))

    llm = get_llm(conversation.agent_model, st.session_state.openai_key)

    return ReActAgent.from_tools(
        tools=tools,
        llm=llm,
        chat_history=chat_history,
        verbose=True,
        max_iterations=10,
    )

# def load_structural_context(query: str = "struktur tabel dan relasi"):
#     vector_store = ChromaVectorStore(persist_dir="chroma_db")
#     storage_context = StorageContext.from_defaults(vector_store=vector_store)
#     index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)

#     retrieved_nodes = index.as_retriever().retrieve(query)
#     result = "\n\n".join([n.text for n in retrieved_nodes])
#     return result


logging.basicConfig(level=logging.DEBUG)