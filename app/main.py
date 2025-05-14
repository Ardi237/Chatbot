# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import ask, indexing, faq, template, conversation, sync 
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request

app = FastAPI(title="ChatDB API", version="1.0.0")

# ─────────────── Middleware ───────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ganti dengan domain frontend kamu di production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────── Register Routes ───────────────
app.include_router(ask.router, tags=["Chat"])
app.include_router(indexing.router, tags=["Indexing"])
app.include_router(faq.router, tags=["FAQ"])
app.include_router(template.router, tags=["SQL Template"])
app.include_router(conversation.router, tags=["Conversation"])
app.include_router(sync.router, tags=["Sync"])

# ─────────────── Root ───────────────
@app.get("/")
def read_root():
    return {"message": "Welcome to ChatDB API", "status": "online"}

templates = Jinja2Templates(directory="templates")

@app.get("/chat-ui", response_class=HTMLResponse)
def chat_ui(request: Request):
    return templates.TemplateResponse("chat_ui.html", {"request": request})