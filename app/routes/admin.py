from fastapi import APIRouter
from app.routes.conversation import chat_sessions

router = APIRouter()

@router.get("/admin/sessions")
def list_sessions():
    return [
        {
            "session_id": sid,
            "agent_model": conv.agent_model,
            "database_ids": conv.database_ids,
            "total_messages": len(conv.messages),
        }
        for sid, conv in chat_sessions.items()
    ]
