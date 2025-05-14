# routes/indexing.py
from fastapi import APIRouter, HTTPException
from app.schemas.request_schema import StructureIndexRequest, FileIndexRequest
from vector_indexer import index_structure, index_uploaded_files

router = APIRouter()

@router.post("/index/structure")
def index_structure_endpoint(data: StructureIndexRequest):
    try:
        index_structure(data.structure_data, data.collection_name)
        return {"status": "success", "message": "Structure indexed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index structure: {e}")

@router.post("/index/files")
def index_files_endpoint(data: FileIndexRequest):
    try:
        index_uploaded_files(data.folder_path, data.collection_name)
        return {"status": "success", "message": "Files indexed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to index files: {e}")