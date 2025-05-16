from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid

from app.utils.session_storage import save_sessions, load_sessions
from app.schemas.request_schema import StartSessionRequest
from app.routes.conversation import chat_sessions
from app.common.Conversation import Conversation
from app.routes.sync import latest_db_config

chat_sessions = load_sessions() 
router = APIRouter()
user_info = {}

@router.post("/public/start-session")
def start_public_session(data: StartSessionRequest):
    session_id = str(uuid.uuid4())

    if not latest_db_config["database_ids"]:
        raise HTTPException(status_code=400, detail="❌ Belum ada database yang disinkronkan dari Streamlit.")

    default_db_id = latest_db_config["database_ids"][0]
    default_uri = latest_db_config["database_uris"].get(default_db_id)

    if not default_uri:
        raise HTTPException(status_code=400, detail="❌ URI untuk database tidak ditemukan.")

    user_info[session_id] = {
        "name": data.name,
        "email": data.email,
        "phone": data.phone
    }

    conversation = Conversation(
        id=session_id,
        agent_model="gpt-4",
        database_ids=[default_db_id],
        database_uris={default_db_id: default_uri}
    )
    chat_sessions[session_id] = conversation
    save_sessions(chat_sessions)

    return {"session_id": session_id}
