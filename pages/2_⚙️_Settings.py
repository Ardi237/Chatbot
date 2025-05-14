import json
import re
import urllib
import os
import streamlit as st
from sqlalchemy import create_engine, text
from cryptography.fernet import InvalidToken as InvalidEncryptionKey

from backup import backup_settings, load_settings
from common import DatabaseProps, set_openai_api_key, init_session_state
from vector_indexer import index_structure
from file_indexer import index_uploaded_files

import pandas as pd
import requests

os.makedirs("uploads", exist_ok=True)
os.makedirs("data/faq_docs", exist_ok=True)

def connect_to_sql_server(host, port, user, password):
    params = {
        "DRIVER": "{ODBC Driver 17 for SQL Server}",
        "SERVER": f"{host},{port}",
        "UID": user,
        "PWD": password,
        "Trusted_Connection": "no",
    }
    dsn = urllib.parse.quote_plus(";".join(f"{k}={v}" for k, v in params.items()))
    return create_engine(f"mssql+pyodbc:///?odbc_connect={dsn}")


def fetch_available_databases(engine):
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT name FROM sys.databases WHERE name NOT IN ('master','tempdb','model','msdb')"
        ))
        return [row[0] for row in result.fetchall()]


def fetch_table_relations_and_tables(engine):
    with engine.connect() as conn:
        rel_query = """
        SELECT 
            fk.name AS FK_Name,
            tp.name AS ParentTable,
            cp.name AS ParentColumn,
            tr.name AS RefTable,
            cr.name AS RefColumn
        FROM 
            sys.foreign_keys fk
        INNER JOIN 
            sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
        INNER JOIN 
            sys.tables tp ON fkc.parent_object_id = tp.object_id
        INNER JOIN 
            sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
        INNER JOIN 
            sys.tables tr ON fkc.referenced_object_id = tr.object_id
        INNER JOIN 
            sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
        """
        rel_result = conn.execute(text(rel_query)).fetchall()
        rel_list = [dict(row._mapping) for row in rel_result]

        table_result = conn.execute(text("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
        """)).fetchall()
        table_names = [row[0] for row in table_result]

        structure_result = conn.execute(text("""
            SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            ORDER BY TABLE_NAME, ORDINAL_POSITION
        """)).fetchall()

        structure_map = {}
        for row in structure_result:
            table = row[0]
            if table not in structure_map:
                structure_map[table] = []
            structure_map[table].append(f"{row[1]} ({row[2]})")

    return rel_list, table_names, structure_map

# ─────────────── REQUEST HTML ───────────────
def sync_to_backend(conversation_id: str, model: str, database_ids: list[str], database_uris: dict[str, str]):
    url = "http://localhost:8000/sync-databases"
    payload = {
        "conversation_id": conversation_id,
        "model": model,
        "database_ids": database_ids,
        "database_uris": database_uris
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            st.success("✅ Berhasil sinkron ke backend!")
        else:
            st.warning(f"⚠️ Gagal sync: {response.text}")
    except Exception as e:
        st.error(f"❌ Error: {e}")

# ─────────────── UI ───────────────
init_session_state()
st.set_page_config(page_title="Settings", page_icon="⚙️")
st.title("⚙️ Settings")
st.divider()

# API Key Section
st.markdown("## OpenAI API key")
with st.form("openai_key_form", clear_on_submit=True):
    api_key = st.text_input("API key", type="password")
    if st.form_submit_button():
        set_openai_api_key(api_key)

st.info("API key is set." if st.session_state.openai_key else "API key is not set.", icon="ℹ️" if st.session_state.openai_key else "⚠️")
st.divider()

# SQL Server Connection Section
st.markdown("## SQL Server Connection")
with st.expander("Connect to SQL Server"):
    mssql_host = st.text_input("Host", placeholder="e.g. localhost")
    mssql_port = st.text_input("Port", value="1433")
    mssql_user = st.text_input("Username")
    mssql_pass = st.text_input("Password", type="password")

    if st.button("Connect to SQL Server"):
        if not all([mssql_host, mssql_user, mssql_pass]):
            st.warning("Please fill in all fields.", icon="⚠️")
        else:
            try:
                engine = connect_to_sql_server(mssql_host, mssql_port, mssql_user, mssql_pass)
                st.session_state["available_databases"] = fetch_available_databases(engine)
                st.session_state["base_uri"] = engine.url.render_as_string(hide_password=False)
                st.success("Connected! Databases retrieved.")
            except Exception as e:
                st.error(f"Connection failed: {e}", icon="🚨")

# Database Selection
if "available_databases" in st.session_state:
    st.markdown("## Select Database")
    db_choice = st.selectbox("Available Databases", st.session_state["available_databases"])

    if st.button("Use This Database"):
        params = {
            "DRIVER": "{ODBC Driver 17 for SQL Server}",
            "SERVER": f"{mssql_host},{mssql_port}",
            "UID": mssql_user,
            "PWD": mssql_pass,
            "DATABASE": db_choice,
            "Trusted_Connection": "no",
        }
        dsn = urllib.parse.quote_plus(";".join(f"{k}={v}" for k, v in params.items()))
        final_uri = f"mssql+pyodbc:///?odbc_connect={dsn}"
        engine = create_engine(final_uri)
        st.session_state.databases[db_choice] = DatabaseProps(db_choice, final_uri)
        st.session_state["current_db_name"] = db_choice
        # st.write(f"[DEBUG] Final URI: {final_uri}")

        try:
            rel_list, table_names, table_structure = fetch_table_relations_and_tables(engine)
            st.session_state["table_relations"] = rel_list
            st.session_state["current_table_list"] = table_names
            st.session_state["table_column_map"] = table_structure
            st.success("Database saved!", icon="✔️")
        except Exception as e:
            st.error(f"Failed to analyze structure: {e}", icon="🚨")

# Show Saved Databases
with st.expander("Saved Databases"):
    st.table({
        k: {"URI": st.session_state.databases[k].get_uri_without_password()}
        for k in st.session_state.databases
    })

# Show Active Tables
if "current_db_name" in st.session_state and "current_table_list" in st.session_state:
    with st.expander(f"Tables in database: {st.session_state['current_db_name']}"):
        st.write(st.session_state["current_table_list"])

# Show Table Structures
if "table_column_map" in st.session_state:
    with st.expander("📘 Table Structures"):
        for table, columns in st.session_state["table_column_map"].items():
            st.markdown(f"**{table}**")
            st.write(columns)

# Structure Indexing
if "table_relations" in st.session_state and st.button("➕ Index Structure to VectorStore"):
    with st.spinner("Indexing structure..."):
        index_structure(st.session_state["table_relations"])
        st.success("Structure indexed successfully to vectorstore!", icon="✅")

selected_db_ids = list(st.session_state.databases.keys())
conversation_id = "html-session"
model_used = "gpt-4-turbo"

if st.button("🔄 Sinkronisasi ke Backend"):
    if st.session_state.databases:
        db_ids = list(st.session_state.databases.keys())
        db_uris = {
            dbid: st.session_state.databases[dbid].uri
            for dbid in db_ids
        }

        sync_to_backend(conversation_id="html-session", model="gpt-4-turbo", database_ids=db_ids, database_uris=db_uris)
    else:
        st.warning("⚠️ Tidak ada database yang dipilih.")


# Backup Section
st.markdown("## Backup Settings")
st.markdown("- ### Backup")
password = st.text_input("Encryption password", type="password", help="Used to encrypt your API keys before backup. Leave empty to use common key.")

with st.empty():
    if st.button("Prepare backup"):
        backup_file = json.dumps(backup_settings(password), indent=2)
        if password:
            st.info("Encrypted with custom password.", icon="ℹ️")
        st.download_button("Download settings JSON", data=backup_file, file_name="chatdb_settings.json")

# Restore Section
st.markdown("- ### Restore")
upload_file = st.file_uploader("Restore settings from JSON")
if upload_file:
    try:
        backup_file = json.load(upload_file)
        if "use_default_key" in backup_file and not backup_file["use_default_key"]:
            st.markdown("Backup is encrypted!")
            password = st.text_input("Decryption password", type="password")
            if st.button("Decrypt and restore"):
                load_settings(backup_file, password)
                st.success("Settings restored!", icon="✔️")
        else:
            load_settings(backup_file, None)
            st.success("Settings restored!", icon="✔️")
    except InvalidEncryptionKey:
        st.error("Invalid decryption key.", icon="🚨")
    except Exception as e:
        st.error(f"Failed to restore backup: {e}", icon="🚨")



st.markdown("- ### Upload File (.txt untuk FAQ, sql_templates.csv untuk SQL, atau .csv biasa untuk indexing)")

uploaded_file = st.file_uploader("Upload file", type=["csv", "txt"])

if uploaded_file:
    filename = uploaded_file.name.lower()

    # 🔷 Jika file adalah sql_templates.csv
    if filename == "sql_templates.csv":
        save_path = "data/sql_templates.csv"
        with open(save_path, "wb") as f:
            f.write(uploaded_file.read())
        st.success("✅ SQL Templates berhasil disimpan ke data/sql_templates.csv")

        # 🧪 Preview isi SQL Template
        try:
            df_preview = pd.read_csv(save_path)
            st.markdown("### 👀 Preview SQL Templates")
            st.dataframe(df_preview.head())
        except Exception as e:
            st.warning(f"Gagal membaca isi CSV: {e}")

    # 📘 Jika file FAQ .txt → simpan ke folder faq_docs
    elif filename.endswith(".txt"):
        save_path = f"data/faq_docs/{filename}"
        with open(save_path, "wb") as f:
            f.write(uploaded_file.read())
        st.success(f"✅ File FAQ '{filename}' berhasil disimpan ke data/faq_docs/")

    # 📂 Jika CSV lain → ke uploads/ untuk indexing ke vectorstore
    elif filename.endswith(".csv"):
        save_path = f"uploads/{filename}"
        with open(save_path, "wb") as f:
            f.write(uploaded_file.read())
        st.success(f"✅ File CSV '{filename}' berhasil disimpan ke uploads/")

        # ✅ Tombol reindex
        if st.button("🔄 Reindex File Vector (CSV)"):
            with st.spinner("Indexing ulang semua CSV dari uploads/..."):
                index_uploaded_files(folder_path="uploads")
                st.success("📚 Semua file CSV diindex ulang ke Qdrant!", icon="✅")



with st.expander("📂 File di uploads/"):
    st.write(os.listdir("uploads"))

with st.expander("📂 File di data/faq_docs/"):
    st.write(os.listdir("data/faq_docs"))
