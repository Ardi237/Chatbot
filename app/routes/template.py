# routes/template.py
from fastapi import APIRouter, HTTPException
from app.schemas.request_schema import TemplateMatchRequest, TemplateLoadRequest
from file_indexer import load_sql_templates, match_sql_template

router = APIRouter()

@router.post("/template/match")
def match_template(data: TemplateMatchRequest):
    try:
        query = match_sql_template(data.prompt)
        return {"sql_query": query or None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template match error: {e}")

@router.post("/template/load")
def load_template(data: TemplateLoadRequest):
    try:
        load_sql_templates(data.path)
        return {"status": "success", "message": f"Templates loaded from {data.path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load templates: {e}")
