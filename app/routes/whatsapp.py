from fastapi import APIRouter, Request, Form
from fastapi.responses import PlainTextResponse
from agent import process_user_prompt
from app.routes.conversation import chat_sessions
from app.common.Conversation import Conversation
import uuid

router = APIRouter()

@router.post("/whatsapp/webhook", response_class=PlainTextResponse)
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(...),
    From: str = Form(...),
):

    session_id = From.replace("whatsapp:", "")
    if session_id not in chat_sessions:
        # Buat conversation baru
        conversation = Conversation(
            id=session_id,
            agent_model="gpt-4-turbo",
            database_ids=["mobil"],  # default
            database_uris={"mobil": "mssql+pyodbc://..."}  # default URI
        )
        chat_sessions[session_id] = conversation

    result = process_user_prompt(Body, session_id)
    return result
