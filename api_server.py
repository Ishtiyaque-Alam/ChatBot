"""
API Server — Unified FastAPI backend for the React frontend.

Serves the chat API endpoints that the frontend calls, plus the
existing ASR transcription endpoint.

Endpoints:
    POST /api/session              — Create a new chat session
    GET  /api/sessions             — List all sessions
    GET  /api/session/{id}/history — Get message history for a session
    POST /api/chat                 — Send a text message (history→VectorDB pipeline)
    POST /api/chat/audio           — Send audio (ASR→Translate→history→VectorDB)
    GET  /health                   — Health check

Run:
    uvicorn api_server:app --host 0.0.0.0 --port 8000
"""

import json
import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from chat_db import ChatDatabase
from chatbot import VoiceChatbot

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Chatbot API",
    description="Backend API for the AI Chatbot Assistant frontend.",
    version="2.0.0",
)

# CORS — allow the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global instances (initialized at startup) ───────────────────────────────
db: ChatDatabase | None = None
bot: VoiceChatbot | None = None


@app.on_event("startup")
async def startup():
    """Initialize DB and chatbot on server start."""
    global db, bot
    db = ChatDatabase()
    db.init_db()
    bot = VoiceChatbot(db)
    logger.info("✅ API server ready — DB initialized, chatbot loaded.")


# ── Session Endpoints ────────────────────────────────────────────────────────

@app.post("/api/session", summary="Create a new chat session")
async def create_session():
    """Create a new chat session and return its UUID."""
    try:
        session_id = db.create_session()
        return {"session_id": session_id}
    except Exception as e:
        logger.exception("Failed to create session")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions", summary="List all chat sessions")
async def list_sessions():
    """Return all sessions ordered by most recently updated."""
    try:
        from sqlalchemy import desc
        from chat_db import ChatSession, ChatMessage

        session = db._SessionLocal()
        try:
            sessions = (
                session.query(ChatSession)
                .order_by(desc(ChatSession.updated_at))
                .all()
            )
            result = []
            for s in sessions:
                # Get the last message for preview
                last_msg = (
                    session.query(ChatMessage)
                    .filter_by(session_id=s.id)
                    .order_by(desc(ChatMessage.created_at))
                    .first()
                )
                result.append({
                    "id": s.id,
                    "title": "",  # Could be set from first user message
                    "lastMessage": last_msg.content[:60] if last_msg else "",
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                })
            return {"sessions": result}
        finally:
            session.close()
    except Exception as e:
        logger.exception("Failed to list sessions")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}/history", summary="Get session history")
async def get_session_history(session_id: str):
    """Return the full message history for a session."""
    try:
        messages = db.get_session_history(session_id)
        return {"messages": messages}
    except Exception as e:
        logger.exception("Failed to fetch history")
        raise HTTPException(status_code=500, detail=str(e))


# ── Chat Endpoints ───────────────────────────────────────────────────────────

@app.post("/api/chat", summary="Send a text message")
async def chat_text(payload: dict):
    """
    Send a text message through the chatbot pipeline.

    Follows: History check → VectorDB fallback → Persist to MySQL.

    Request body:
        {"session_id": "...", "message": "..."}

    Response:
        {"answer": "...", "source": "history"|"vectordb"}
    """
    session_id = payload.get("session_id")
    message = payload.get("message", "").strip()

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    try:
        result = bot.run_text(message=message, session_id=session_id)
        return {
            "answer": result["answer"],
            "source": result["source"],
        }
    except Exception as e:
        logger.exception("Chat text error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/audio", summary="Send an audio message")
async def chat_audio(
    file: UploadFile = File(..., description="Audio file (WAV, WebM, etc.)"),
    session_id: str = Form(..., description="Chat session UUID"),
    language: str = Form("hi-IN", description="Source language BCP-47 code"),
):
    """
    Send an audio file through the full chatbot pipeline.

    Follows: ASR → Translate → History check → VectorDB fallback → Persist.

    Response:
        {
            "transcription": "...",
            "translation": "...",
            "answer": "...",
            "source": "history"|"vectordb"
        }
    """
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    try:
        # Save uploaded audio to a temp file
        audio_bytes = await file.read()
        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Audio file is empty")

        suffix = Path(file.filename).suffix if file.filename else ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = Path(tmp.name)

        logger.info(
            f"Received audio: filename={file.filename}, "
            f"size={len(audio_bytes):,} bytes, language={language}"
        )

        try:
            result = bot.run(
                audio_path=tmp_path,
                session_id=session_id,
                source_language=language,
            )
            return {
                "transcription": result["transcription"],
                "translation": result["translation"],
                "answer": result["answer"],
                "source": result["source"],
            }
        finally:
            tmp_path.unlink(missing_ok=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Chat audio error")
        raise HTTPException(status_code=500, detail=str(e))


# ── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health", summary="Health check")
async def health_check():
    return {
        "status": "healthy",
        "db_initialized": db is not None,
        "bot_initialized": bot is not None,
    }
