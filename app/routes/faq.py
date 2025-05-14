# routes/faq.py
from fastapi import APIRouter, HTTPException
from app.schemas.request_schema import FAQMatchRequest, FAQLoadRequest
from file_indexer import load_faq_txt, match_faq_answer

router = APIRouter()

@router.post("/faq/match")
def match_faq(data: FAQMatchRequest):
    try:
        answer = match_faq_answer(data.prompt)
        return {"answer": answer or None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FAQ match error: {e}")

@router.post("/faq/load")
def load_faq(data: FAQLoadRequest):
    try:
        load_faq_txt(data.folder_path)
        return {"status": "success", "message": f"FAQ loaded from {data.folder_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load FAQ: {e}")