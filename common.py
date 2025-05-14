import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import openai
import streamlit as st


class DatabaseProps:
    """Representasi metadata koneksi database."""
    def __init__(self, id: str, uri: str) -> None:
        self.id = id
        self.uri = uri

    def get_uri_without_password(self) -> str:
        """
        Mengembalikan URI dengan password disamarkan (untuk ditampilkan).
        Contoh masking: 'mysql://user:********@host:port/db'
        """
        match = re.search(r"(:(?!//)[^@]+@)", self.uri)
        if not match:
            return self.uri
        return f"{self.uri[:match.start()+1]}{'*' * 8}{self.uri[match.end()-1:]}"


class Message:
    """Representasi satu pesan dalam percakapan."""
    def __init__(self, role: str, content: str, query_results: Optional[List[Tuple[str, list]]] = None) -> None:
        self.role = role
        self.content = content
        self.query_results = query_results or []


class Conversation:
    """
    Satu percakapan interaktif antara user dan agent,
    menyimpan pesan, hasil query, dan database yang digunakan.
    """
    def __init__(
        self,
        id: str,
        agent_model: str,
        database_ids: List[str],
        messages: Optional[List[Message]] = None,
    ) -> None:
        self.id = id
        self.agent_model = agent_model
        self.database_ids = list(database_ids)
        self.messages = list(messages) if messages else []
        self.query_results_queue: List[Tuple[str, str, list]] = []
        self.update_timestamp()

    def add_message(self, role: str, content: str, query_results: Optional[List[Tuple[str, list]]] = None):
        self.messages.append(Message(role, content, query_results))

    def update_timestamp(self):
        self.last_update_timestamp = datetime.now().timestamp()


def init_session_state():
    if "openai_key" not in st.session_state:
        st.session_state.openai_key = ""

    if "databases" not in st.session_state:
        st.session_state.databases = {}

    if "conversations" not in st.session_state:
        st.session_state.conversations = {}

    if "current_conversation" not in st.session_state:
        st.session_state.current_conversation = ""

    if "retry" not in st.session_state:
        st.session_state.retry = None


def set_openai_api_key(api_key: str):
    """Simpan OpenAI API Key ke dalam modul dan session state."""
    openai.api_key = api_key
    st.session_state.openai_key = api_key
