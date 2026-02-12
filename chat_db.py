"""
chat_db — MySQL-backed chat history with SQLAlchemy ORM.

Provides session and message management for the sliding-window chatbot.

Tables:
    sessions  — one row per conversation session
    messages  — ordered messages within a session (user + assistant)

Usage:
    from chat_db import ChatDatabase

    db = ChatDatabase()
    db.init_db()
    sid = db.create_session()
    db.add_message(sid, "user", "Who is Gandhi?")
    db.add_message(sid, "assistant", "Gandhi was...")
    history = db.get_recent_messages(sid, limit=10)
"""

import json
import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from utils.config import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
)

logger = logging.getLogger(__name__)

Base = declarative_base()


# ── ORM Models ───────────────────────────────────────────────────────────────

class ChatSession(Base):
    """A conversation session."""

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    messages = relationship(
        "ChatMessage", back_populates="session", order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    """A single message (user or assistant) in a session."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(Enum("user", "assistant", name="message_role"), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("ChatSession", back_populates="messages")


# ── ChatDatabase Class ───────────────────────────────────────────────────────

class ChatDatabase:
    """
    MySQL-backed chat history manager.

    Handles session lifecycle and message CRUD with a sliding-window
    query for retrieving the most recent N messages.
    """

    def __init__(self) -> None:
        """Initialize the database engine and session factory."""
        db_url = (
            f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
            f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
            "?charset=utf8mb4"
        )
        self._engine = create_engine(db_url, echo=False, pool_pre_ping=True)
        self._SessionLocal = sessionmaker(bind=self._engine)

    # ── Setup ────────────────────────────────────────────────────────────

    def init_db(self) -> None:
        """Create all tables if they don't exist (idempotent)."""
        Base.metadata.create_all(self._engine)
        logger.info("Chat DB initialized (tables created if needed).")

    # ── Session Management ───────────────────────────────────────────────

    def create_session(self) -> str:
        """Create a new chat session and return its UUID."""
        db = self._SessionLocal()
        try:
            session = ChatSession()
            db.add(session)
            db.commit()
            logger.info(f"Created session: {session.id}")
            return session.id
        finally:
            db.close()

    # ── Message CRUD ─────────────────────────────────────────────────────

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> int:
        """
        Insert a message into a session.

        Args:
            session_id: UUID of the session.
            role:       'user' or 'assistant'.
            content:    Message text.
            metadata:   Optional dict (transcription, translation, etc.).

        Returns:
            The auto-incremented message ID.
        """
        db = self._SessionLocal()
        try:
            msg = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                metadata_json=(
                    json.dumps(metadata, ensure_ascii=False) if metadata else None
                ),
            )
            db.add(msg)

            # Touch the session's updated_at
            sess = db.query(ChatSession).filter_by(id=session_id).first()
            if sess:
                sess.updated_at = datetime.now(timezone.utc)

            db.commit()
            logger.info(f"Added {role} message (id={msg.id}) to session {session_id}")
            return msg.id
        finally:
            db.close()

    # ── Retrieval ────────────────────────────────────────────────────────

    def get_recent_messages(self, session_id: str, limit: int = 10) -> list[dict]:
        """
        Retrieve the most recent `limit` messages (sliding window).

        Returns newest messages in chronological order (oldest first).

        Returns:
            List of dicts: [{"role": "user", "content": "..."}, ...]
        """
        db = self._SessionLocal()
        try:
            msgs = (
                db.query(ChatMessage)
                .filter_by(session_id=session_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
                .all()
            )
            msgs.reverse()  # chronological order
            return [{"role": m.role, "content": m.content} for m in msgs]
        finally:
            db.close()

    def get_session_history(self, session_id: str) -> list[dict]:
        """
        Retrieve the full message history for a session.

        Returns:
            List of dicts with role, content, metadata, and timestamp.
        """
        db = self._SessionLocal()
        try:
            msgs = (
                db.query(ChatMessage)
                .filter_by(session_id=session_id)
                .order_by(ChatMessage.created_at.asc())
                .all()
            )
            return [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "metadata": (
                        json.loads(m.metadata_json) if m.metadata_json else None
                    ),
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in msgs
            ]
        finally:
            db.close()
