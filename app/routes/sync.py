# routes/sync.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.common.Conversation import Conversation  
from app.routes.conversation import chat_sessions
from app.schemas.request_schema import SyncRequest

router = APIRouter()

@router.post("/sync-databases")
def sync_databases(data: SyncRequest):
    try:
        if not data.database_ids or not data.database_uris:
            raise HTTPException(status_code=400, detail="Database kosong atau URI hilang")

        conversation = Conversation(
            id=data.conversation_id,
            agent_model=data.model,
            database_ids=data.database_ids,
            database_uris=data.database_uris  # 🆕 simpan uri
        )
        chat_sessions[data.conversation_id] = conversation
        return { "status": "ok", "message": "✅ Sinkronisasi berhasil!" }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
