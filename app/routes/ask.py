# routes/ask.py
from fastapi import APIRouter, HTTPException
from app.schemas.request_schema import AskRequest
from agent import process_user_prompt_with_session
from app.routes.conversation import chat_sessions

router = APIRouter()

@router.post("/ask")
def ask_endpoint(data: AskRequest):
    try:
        if data.conversation_id not in chat_sessions:
            return {"response": "⚠️ Sedang dalam perbaikan. Harap tunggu hingga konfigurasi selesai."}

        conversation = chat_sessions[data.conversation_id]
        print("✅ [ASK] Prompt:", data.prompt)
        print("✅ [ASK] DBs:", conversation.database_ids)
        print("✅ [ASK] URI Sample:", conversation.get_database_uri(conversation.database_ids[0]))

        result = process_user_prompt_with_session(
            prompt=data.prompt,
            conversation=conversation,
            rag_mode=data.rag_mode or "combine"
        )

        # Convert SQL result (list of lists) to HTML table if needed
        if isinstance(result, list) and all(isinstance(row, list) for row in result):
            html_table = "<table border='1'><thead><tr>"
            html_table += "".join([f"<th>Kolom {i+1}</th>" for i in range(len(result[0]))])
            html_table += "</tr></thead><tbody>"
            for row in result:
                html_table += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
            html_table += "</tbody></table>"
            return {"response": html_table}

        return {"response": result}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
