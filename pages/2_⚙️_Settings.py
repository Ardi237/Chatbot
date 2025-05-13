import json
import re

import streamlit as st
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from cryptography.fernet import InvalidToken as InvalidEncryptionKey

from backup import backup_settings, load_settings
from common import DatabaseProps, set_openai_api_key, init_session_state
from vector_indexer import index_structure
from file_indexer import index_uploaded_files

# ─────────────── Session Init ───────────────
init_session_state()
st.set_page_config(page_title="Settings", page_icon="⚙️")
st.title("⚙️ Settings")
st.divider()

# ─────────────── OpenAI API KEY ───────────────
st.markdown("## OpenAI API key")
with st.form("openai_key_form", clear_on_submit=True):
    api_key = st.text_input("API key", type="password")
    if st.form_submit_button():
        set_openai_api_key(api_key)

if st.session_state.openai_key:
    st.info("API key is set.", icon="ℹ️")
else:
    st.warning("API key is not set.", icon="⚠️")

st.divider()

# ─────────────── SQL Server Connection ───────────────
st.markdown("## SQL Server Connection")
with st.expander("Connect to SQL Server"):
    mssql_host = st.text_input("Host", placeholder="e.g. localhost")
    mssql_port = st.text_input("Port", value="1433")
    mssql_user = st.text_input("Username")
    mssql_pass = st.text_input("Password", type="password")

    if st.button("Connect to SQL Server"):
        if not mssql_host or not mssql_user or not mssql_pass:
            st.warning("Please fill in all fields (Host, Username, Password).", icon="⚠️")
        else:
            try:
                import urllib

                params = {
                    "DRIVER": "{ODBC Driver 17 for SQL Server}",
                    "SERVER": f"{mssql_host},{mssql_port}",
                    "UID": mssql_user,
                    "PWD": mssql_pass,
                    "Trusted_Connection": "no",
                }
                dsn = urllib.parse.quote_plus(";".join(f"{k}={v}" for k, v in params.items()))
                uri = f"mssql+pyodbc:///?odbc_connect={dsn}"

                engine = create_engine(uri)

                with engine.connect() as conn:
                    result = conn.execute(text(
                        "SELECT name FROM sys.databases WHERE name NOT IN ('master','tempdb','model','msdb')"
                    ))
                    db_names = [row[0] for row in result.fetchall()]

                    # ➕ Tambahkan ANALISIS STRUKTUR TABEL & RELASI
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
                    st.session_state["table_relations"] = rel_list

                st.session_state["available_databases"] = db_names
                st.session_state["base_uri"] = uri
                st.success("Connected! Databases retrieved.")
            except Exception as e:
                st.error(f"Connection failed: {e}", icon="🚨")

# ─────────────── Select and Save Database ───────────────
if "available_databases" in st.session_state:
    st.markdown("## Select Database")
    db_choice = st.selectbox("Available Databases", st.session_state["available_databases"])

    if st.button("Use This Database"):
        final_uri = st.session_state["base_uri"].replace("/?", f"/{db_choice}?")
        db_id = db_choice
        st.session_state.databases[db_id] = DatabaseProps(db_id, final_uri)
        st.success("Database saved!", icon="✔️")

# ─────────────── Show Saved Databases ───────────────
with st.expander("Saved Databases"):
    st.table({
        k: {"URI": st.session_state.databases[k].get_uri_without_password()}
        for k in st.session_state.databases
    })

st.divider()

# ─────────────── Index Structure to VectorStore ───────────────
if "table_relations" in st.session_state and st.button("➕ Index Structure to VectorStore"):
    with st.spinner("Indexing structure..."):
        index_structure(st.session_state["table_relations"])
        st.success("Structure indexed successfully to vectorstore!", icon="✅")

# ─────────────── Backup & Restore ───────────────
st.markdown("## Backup Settings")

# Backup
st.markdown("- ### Backup")
password = st.text_input(
    "Encryption password",
    help="Used to encrypt your API keys before backup. Leave empty to use common key.",
    type="password",
)

with st.empty():
    if st.button("Prepare backup"):
        backup_file = json.dumps(backup_settings(password), indent=2)
        if password:
            st.info("Encrypted with custom password.", icon="ℹ️")
        st.download_button("Download settings JSON", data=backup_file, file_name="chatdb_settings.json")

# Restore
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

# Restore
st.markdown("- ### Upload File")
uploaded_file = st.file_uploader("Upload PDF/Excel/Doc", type=["pdf", "xlsx", "csv", "docx"])
if uploaded_file:
    save_path = f"file/{uploaded_file.name}"
    with open(save_path, "wb") as f:
        f.write(uploaded_file.read())


    if st.button("🔄 Reindex File Vector"):
        index_uploaded_files("uploads")
        st.success("File vector reindexed!", icon="✅")
