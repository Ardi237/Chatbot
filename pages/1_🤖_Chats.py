import json
import re

import streamlit as st
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.base.llms.types import MessageRole as LLMMessageRole
from sqlalchemy.exc import DBAPIError, NoSuchColumnError, NoSuchTableError

import pandas as pd
import matplotlib.pyplot as plt

from agent import get_agent, process_user_prompt  # 🆕 Gunakan pipeline 3-lapis
from backup import backup_conversation, load_conversation
from common import Conversation, init_session_state
from multi_database import NoSuchDatabaseError

# ──────────────── Init ────────────────
st.set_page_config(page_title="Chats", page_icon="🤖")
init_session_state()

# 🔒 MOCK SESSION PENGGUNA
if "mock_user_id" not in st.session_state:
    st.session_state["mock_user_id"] = 2
    st.session_state["mock_username"] = "agentbudi"
    st.session_state["mock_role"] = "agent"
    st.session_state["mock_status"] = "active"

# ──────────────── Helpers ────────────────
def new_chat_button_on_click():
    st.session_state.current_conversation = ""

def set_conversation(conversation_id):
    st.session_state.current_conversation = conversation_id

def retry_chat(prompt: str, stream: bool):
    st.session_state.retry = {"stream": stream, "prompt": prompt}

def conversation_exists(cid: str) -> bool:
    return cid != "" and cid in st.session_state.conversations

def conversation_valid(cid: str) -> bool:
    if conversation_exists(cid):
        conv = st.session_state.conversations[cid]
        return all(x in st.session_state.databases for x in conv.database_ids)
    return False

def display_query(database, query, results):
    with st.expander("View SQL query..."):
        st.markdown(f"Database: `{database}`")
        st.markdown(f"`{query}`")
        st.table(results)

# ──────────────── Sidebar ────────────────
with st.sidebar:
    st.markdown("## Chats")
    st.button("➕ New chat", on_click=new_chat_button_on_click)

    upload_file = st.file_uploader("Restore conversation from JSON")
    if upload_file:
        conversation = load_conversation(json.load(upload_file))
        st.session_state.conversations[conversation.id] = conversation
        st.toast("Conversation restored!", icon="✔️")

    st.divider()

    if conversation_exists(st.session_state.current_conversation):
        cid = st.session_state.current_conversation
        st.markdown("## Current conversation")
        with st.expander(cid):
            if st.button("Backup conversation"):
                backup_file = json.dumps(backup_conversation(cid))
                name = re.sub(r"\s+", "_", cid)
                if st.download_button("Download backup JSON", data=backup_file, file_name=f"chatdb_{name}.json"):
                    st.toast("Download started.", icon="✔️")
        st.divider()

    st.markdown("## Select conversation")
    for cid in st.session_state.conversations:
        st.button(cid, on_click=set_conversation, args=[cid])

# ──────────────── Main View ────────────────
if not conversation_exists(st.session_state.current_conversation):
    st.title("New conversation")
    with st.form("new_conversation_form"):
        cid = st.text_input("Conversation title")
        model = st.text_input("Agent model", value="gpt-4-turbo")
        db_ids = st.multiselect("Select databases", list(st.session_state.databases.keys()))
        if st.form_submit_button():
            if cid in st.session_state.conversations:
                st.error("Conversation title must be unique!", icon="⚠️")
            else:
                st.session_state.conversations[cid] = Conversation(cid, model, db_ids)
                set_conversation(cid)

elif not conversation_valid(st.session_state.current_conversation):
    st.title(st.session_state.current_conversation)
    st.markdown("### Could not load conversation: missing database.\nRestore your settings first!")

elif not st.session_state.openai_key:
    st.error("OpenAI API key not set. Go to ⚙️ Settings page!", "⚠️")

else:
    cid = st.session_state.current_conversation
    conversation: Conversation = st.session_state.conversations[cid]
    st.title(cid)

    for msg in conversation.messages:
        with st.chat_message(msg.role):
            st.markdown(msg.content)
            for db, q, r in msg.query_results:
                display_query(db, q, r)

    get_agent(cid, conversation.last_update_timestamp)

    if not conversation.messages:
        conversation.add_message("assistant", "How can I help you today?")
        with st.chat_message("assistant"):
            st.markdown("How can I help you today?")

    prompt = st.chat_input("Your query")
    use_streaming = True

    if not prompt and st.session_state.retry:
        use_streaming = st.session_state.retry["stream"]
        prompt = st.session_state.retry["prompt"]
        st.session_state.retry = None

    if prompt:
        # Inject user context
        user_id = st.session_state.get("mock_user_id")
        username = st.session_state.get("mock_username")
        role = st.session_state.get("mock_role")
        status = st.session_state.get("mock_status")

        enriched_prompt = f"""
            [User Info]
            ID: {user_id}
            Username: {username}
            Role: {role}
            Status: {status}

            [Question]
            {prompt.strip()}
        """

        with st.chat_message("user"):
            st.markdown(prompt)
        conversation.add_message("user", prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            response_text = ""
            show_retry = False

            try:
                # 🧠 Jalankan pipeline 3-lapis
                response_text = process_user_prompt(prompt.strip(), cid, rag_mode="combine")
                placeholder.markdown(response_text)

            except Exception as e:
                response_text = "[System] An error has occurred:\n\n```" + str(e).replace("\n", "\n\n") + "```"
                placeholder.markdown(response_text)
                show_retry = True

            if show_retry:
                st.button("Retry", on_click=retry_chat, args=[prompt, True])
                st.button("Retry without streaming", on_click=retry_chat, args=[prompt, False])

            query_results = []
            for db, q, r in conversation.query_results_queue:
                query_results.append((db, q, r))
                display_query(db, q, r)

            def try_plot(df: pd.DataFrame):
                st.markdown("### 📊 Visualisasi")
                try:
                    if len(df.columns) >= 2:
                        x = df.columns[0]
                        y = df.columns[1]
                        st.bar_chart(df.set_index(x)[y])
                    else:
                        st.info("Data terlalu sedikit untuk divisualisasikan.")
                except Exception as e:
                    st.error(f"Gagal buat grafik: {e}")

            for db, q, rows in conversation.query_results_queue:
                df = pd.DataFrame(rows)
                st.dataframe(df)
                try_plot(df)

            conversation.query_results_queue = []
            conversation.add_message("assistant", response_text, query_results)
