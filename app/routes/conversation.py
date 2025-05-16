# routes/conversation.py
from fastapi import APIRouter, HTTPException
from app.schemas.request_schema import InitConversationRequest
from app.utils.session_storage import save_sessions, load_sessions
from common import Conversation

chat_sessions = load_sessions()  
# Global memory store sementara (bisa diganti Redis / DB nantinya)
chat_sessions = {}

router = APIRouter()

@router.post("/conversation/init")
def init_conversation(data: InitConversationRequest):
    try:
        if data.conversation_id in chat_sessions:
            return {"status": "exists", "message": "Conversation already exists."}

        # routes/conversation.py
        if not data.database_ids or not data.database_uris:
            return { "status": "error", "message": "Database belum dikonfigurasi. Harap gunakan dashboard Streamlit." }

        # Validasi ID, misalnya harus mengandung kata "db_" atau panjang min.
        for dbid in data.database_ids:
            if len(dbid) < 2:  # bebas kriteria
                return { "status": "error", "message": f"❌ Database ID tidak valid: {dbid}" }

        conversation = Conversation(
            id=data.conversation_id,
            agent_model=data.model,
            database_ids=data.database_ids,
        )
        chat_sessions[data.conversation_id] = conversation
        save_sessions(chat_sessions)

        return {"status": "ok", "message": "Conversation initialized."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
