import json, os

SESSION_FILE = "chat_sessions.json"

def save_sessions(chat_sessions):
    try:
        serializable = {}
        for sid, conv in chat_sessions.items():
            serializable[sid] = {
                "id": conv.id,
                "agent_model": conv.agent_model,
                "database_ids": conv.database_ids,
                "database_uris": conv.database_uris,
                "messages": conv.messages,
            }
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=2)
    except Exception as e:
        print(f"[Backup] Gagal menyimpan sesi: {e}")

def load_sessions():
    if not os.path.exists(SESSION_FILE):
        return {}

    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            from app.common.Conversation import Conversation
            return {
                sid: Conversation(**conv) for sid, conv in data.items()
            }
    except Exception as e:
        print(f"[Backup] Gagal memuat sesi: {e}")
        return {}
