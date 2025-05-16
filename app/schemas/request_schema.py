# app/schemas/request_schema.py
from pydantic import BaseModel
from typing import List, Optional, Dict

# ────── ASK ──────
class AskRequest(BaseModel):
    prompt: str
    conversation_id: str
    rag_mode: str = "combine"

# ────── INDEXING ──────
class StructureIndexRequest(BaseModel):
    structure_data: List[str]
    collection_name: Optional[str] = "db_structure"

class FileIndexRequest(BaseModel):
    folder_path: Optional[str] = "uploads"
    collection_name: Optional[str] = "uploaded_files"

# ────── TEMPLATE ──────
class TemplateMatchRequest(BaseModel):
    prompt: str

class TemplateLoadRequest(BaseModel):
    path: str = "data/sql_templates.csv"

# ────── FAQ ──────
class FAQMatchRequest(BaseModel):
    prompt: str

class FAQLoadRequest(BaseModel):
    folder_path: str = "data/faq_docs/"

# ────── CONVERSATION ──────
class InitConversationRequest(BaseModel):
    conversation_id: str
    model: str = "gpt-4-turbo"
    database_ids: List[str]

class SyncRequest(BaseModel):
    conversation_id: str
    model: str
    database_ids: List[str]
    database_uris: Dict[str, str] 

# ────── PUBLIC SESSION ──────
class StartSessionRequest(BaseModel):
    name: str
    email: str
    phone: str
