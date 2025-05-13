from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Document
from llama_index.embeddings.openai import OpenAIEmbedding
# from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.schema import TextNode

from typing import List, Dict
import os

PERSIST_DIR = "chroma_db"

def build_documents_from_db_metadata(table_relations: List[Dict]) -> List[Document]:
    documents = []
    grouped = {}
    for r in table_relations:
        key = r["ParentTable"]
        grouped.setdefault(key, []).append(r)
    
    for table, rels in grouped.items():
        doc_text = f"Table `{table}` has columns:\n"
        columns = set()
        for rel in rels:
            columns.add(rel['ParentColumn'])
        doc_text += "- " + "\n- ".join(columns) + "\n\n"

        doc_text += "Relationships:\n"
        for rel in rels:
            doc_text += f"- `{table}`.{rel['ParentColumn']} → `{rel['RefTable']}`.{rel['RefColumn']}\n"
        
        documents.append(Document(text=doc_text))
    
    return documents

def index_structure(table_relations: List[Dict]):
    documents = build_documents_from_db_metadata(table_relations)

    vector_store = ChromaVectorStore(persist_dir=PERSIST_DIR)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=OpenAIEmbedding(),
        show_progress=True
    )

    index.storage_context.persist()
    return index
