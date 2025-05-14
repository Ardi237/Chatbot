# app/common/Conversation.py
from typing import List, Optional, Dict
class Conversation:
    def __init__(self, id: str, agent_model: str = "gpt-4-turbo", database_ids: Optional[List[str]] = None, database_uris: Optional[Dict[str, str]] = None):
        self.id = id
        self.agent_model = agent_model
        self.database_ids = database_ids or []
        self.database_uris = database_uris or {}
        self.messages = []
        self.query_results_queue = []
        print("✅ CONVERSATION INIT:", database_ids, database_uris)


    def add_message(self, role: str, content: str, query_results=None):
        self.messages.append({"role": role, "content": content, "query_results": query_results or []})

    def get_database_uri(self, db_id: str):
        uri = self.database_uris.get(db_id)
        if not uri:
            raise ValueError(f"❌ URI untuk database '{db_id}' tidak ditemukan.")
        return uri
        
    @property
    def last_update_timestamp(self):
        import time
        return int(time.time())
