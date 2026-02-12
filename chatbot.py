"""
Chatbot — Smart RAG chatbot with sliding window history + conditional VectorDB.

Uses a single LLM call to try answering from conversation history.
If the LLM signals it needs more context, retrieves chunks from VectorDB
and makes a second LLM call.

Flow:
    Audio → ASR → Translate → Get last 10 msgs from MySQL
        → LLM (try answer from history, JSON output)
        → if success: save & return
        → if failure: VectorDB retrieve → LLM with chunks → save & return

Usage:
    from chatbot import VoiceChatbot
    from chat_db import ChatDatabase

    db = ChatDatabase()
    db.init_db()
    bot = VoiceChatbot(db)

    session_id = db.create_session()
    result = bot.run(audio_path, session_id, source_language="hi-IN")
"""

import json
import logging
from pathlib import Path

from groq import Groq

from chat_db import ChatDatabase
from task5_rag_pipeline import step1_transcribe, step2_translate, step3_retrieve
from utils.config import (
    GROQ_API_KEY,
    LLM_MODEL_NAME,
    SLIDING_WINDOW_SIZE,
    TOP_K_RETRIEVAL,
)

logger = logging.getLogger(__name__)


class VoiceChatbot:
    """
    Smart voice chatbot with sliding-window history and conditional VectorDB retrieval.

    Attempts to answer from recent conversation history first (1 API call).
    Falls back to VectorDB retrieval + LLM only when history is insufficient (2 API calls).
    All messages are persisted to MySQL automatically.
    """

    # ── LLM Prompts ──────────────────────────────────────────────────────

    HISTORY_PROMPT = """You are a helpful assistant that answers questions using conversation history.

You will be given the recent conversation history and a new user question.
Try to answer the question using ONLY the information available in the conversation history.

IMPORTANT: You MUST respond with a valid JSON object in one of these two formats:

If you CAN answer from the conversation history:
{"status": "success", "content": "<your answer here>"}

If you CANNOT answer because the history doesn't contain enough information:
{"status": "failure", "content": "Need more context"}

Rules:
- Only return the JSON object, nothing else.
- Do NOT make up information not present in the history.
- If the question is a follow-up that can be answered from prior messages, return success.
- If the question is about something not discussed before, return failure."""

    RETRIEVAL_PROMPT = """You are a helpful assistant that answers questions based on the provided context.

You will be given:
1. Recent conversation history (for follow-up context)
2. Retrieved information from a knowledge base

Use the retrieved information to answer the question. You may also use the
conversation history for understanding context. Keep your answer concise and accurate.
If the answer is not in the provided information, say so."""

    # ── Constructor ──────────────────────────────────────────────────────

    def __init__(self, db: ChatDatabase) -> None:
        """
        Initialize the chatbot.

        Args:
            db: A ChatDatabase instance for message persistence.
        """
        self._db = db
        self._client: Groq | None = None

    # ── Private Helpers ──────────────────────────────────────────────────

    def _get_client(self) -> Groq:
        """Return a configured Groq client (lazy-initialized)."""
        if self._client is None:
            if not GROQ_API_KEY:
                raise ValueError(
                    "GROQ_API_KEY not set. Add it to your .env file. "
                    "Sign up at https://console.groq.com/ for free."
                )
            self._client = Groq(api_key=GROQ_API_KEY)
        return self._client

    def _format_history(self, history: list[dict]) -> str:
        """Format message list into a readable string for the LLM."""
        return "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in history
        )

    # ── Phase 1: Try answering from history ──────────────────────────────

    def try_answer_from_history(self, question: str, history: list[dict]) -> dict:
        """
        Single LLM call that either answers from history or signals failure.

        Args:
            question: User's question in English.
            history:  Recent messages [{"role": "...", "content": "..."}].

        Returns:
            Dict with 'status' ("success"/"failure") and 'content'.
        """
        if not history:
            return {"status": "failure", "content": "Need more context"}

        user_prompt = (
            f"Conversation history:\n{self._format_history(history)}\n\n"
            f"New question: {question}\n\n"
            f"Respond with JSON:"
        )

        logger.info("[Chatbot] Phase 1: Trying to answer from history...")

        try:
            response = self._get_client().chat.completions.create(
                messages=[
                    {"role": "system", "content": self.HISTORY_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                model=LLM_MODEL_NAME,
                temperature=0.2,
                max_tokens=512,
            )
            raw = response.choices[0].message.content.strip()
            logger.info(f"[Chatbot] LLM raw response: {raw[:200]}")

            result = json.loads(raw)
            if "status" not in result or "content" not in result:
                logger.warning("[Chatbot] Invalid JSON structure, falling back")
                return {"status": "failure", "content": "Need more context"}

            logger.info(f"[Chatbot] Phase 1 result: status={result['status']}")
            return result

        except json.JSONDecodeError:
            logger.warning("[Chatbot] Failed to parse LLM JSON, falling back")
            return {"status": "failure", "content": "Need more context"}
        except Exception as e:
            logger.error(f"[Chatbot] LLM error in Phase 1: {e}")
            raise RuntimeError(f"LLM error: {e}") from e

    # ── Phase 2: Answer with VectorDB retrieval ──────────────────────────

    def answer_with_retrieval(
        self,
        question: str,
        history: list[dict],
        top_k: int = TOP_K_RETRIEVAL,
    ) -> tuple[str, list[dict]]:
        """
        Retrieve chunks from VectorDB and generate an answer.

        Args:
            question: User's question in English.
            history:  Recent chat history.
            top_k:    Number of chunks to retrieve.

        Returns:
            Tuple of (answer_text, retrieved_chunks).
        """
        logger.info("[Chatbot] Phase 2: Retrieving from VectorDB...")

        chunks = step3_retrieve(question, top_k=top_k)

        context = "\n\n---\n\n".join(
            f"[Chunk {i+1}]\n{chunk['text']}"
            for i, chunk in enumerate(chunks)
        )

        history_text = ""
        if history:
            history_text = (
                "Recent conversation:\n"
                + self._format_history(history[-6:])
                + "\n\n"
            )

        user_prompt = (
            f"{history_text}"
            f"Retrieved context:\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Answer:"
        )

        logger.info(f"[Chatbot] Querying LLM with {len(chunks)} retrieved chunks...")

        response = self._get_client().chat.completions.create(
            messages=[
                {"role": "system", "content": self.RETRIEVAL_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            model=LLM_MODEL_NAME,
            temperature=0.3,
            max_tokens=512,
        )

        answer = response.choices[0].message.content.strip()
        logger.info(f"[Chatbot] Phase 2 answer: {answer[:120]}...")
        return answer, chunks

    # ── Main Orchestration ───────────────────────────────────────────────

    def run(
        self,
        audio_path: Path,
        session_id: str,
        source_language: str = "hi-IN",
    ) -> dict:
        """
        Full chatbot pipeline: Audio → ASR → Translate → Smart answer → Save.

        Args:
            audio_path:       Path to the audio file.
            session_id:       MySQL session UUID.
            source_language:  BCP-47 language code (default: "hi-IN").

        Returns:
            {
                "transcription": str,
                "translation": str,
                "answer": str,
                "source": "history" | "vectordb",
                "retrieved_chunks": list[dict] | None,
            }
        """
        # Step 1 — Transcribe
        transcription = step1_transcribe(audio_path)

        # Step 2 — Translate
        translation = step2_translate(transcription, source_language)

        # Step 3 — Get sliding window
        history = self._db.get_recent_messages(
            session_id, limit=SLIDING_WINDOW_SIZE
        )
        logger.info(f"[Chatbot] Retrieved {len(history)} messages from history")

        # Step 4 — Try answering from history
        result = self.try_answer_from_history(translation, history)

        if result["status"] == "success":
            answer = result["content"]
            source = "history"
            chunks = None
            logger.info("[Chatbot] ✅ Answered from history (1 API call)")
        else:
            # Step 5 — Fall back to VectorDB
            answer, chunks = self.answer_with_retrieval(translation, history)
            source = "vectordb"
            logger.info("[Chatbot] 📚 Answered with VectorDB (2 API calls)")

        # Step 6 — Persist messages
        self._db.add_message(
            session_id, "user", translation,
            metadata={
                "transcription": transcription,
                "source_language": source_language,
            },
        )
        self._db.add_message(
            session_id, "assistant", answer,
            metadata={
                "source": source,
                "chunks_used": len(chunks) if chunks else 0,
            },
        )

        return {
            "transcription": transcription,
            "translation": translation,
            "answer": answer,
            "source": source,
            "retrieved_chunks": chunks,
        }

    def run_text(
        self,
        message: str,
        session_id: str,
    ) -> dict:
        """
        Text-only chatbot pipeline: Smart answer → Save.

        Same logic as run() but skips ASR transcription and translation
        since the input is already text.

        Args:
            message:     User's text message (in English).
            session_id:  MySQL session UUID.

        Returns:
            {
                "answer": str,
                "source": "history" | "vectordb",
                "retrieved_chunks": list[dict] | None,
            }
        """
        # Step 1 — Get sliding window
        history = self._db.get_recent_messages(
            session_id, limit=SLIDING_WINDOW_SIZE
        )
        logger.info(f"[Chatbot] Retrieved {len(history)} messages from history")

        # Step 2 — Try answering from history
        result = self.try_answer_from_history(message, history)

        if result["status"] == "success":
            answer = result["content"]
            source = "history"
            chunks = None
            logger.info("[Chatbot] ✅ Answered from history (1 API call)")
        else:
            # Step 3 — Fall back to VectorDB
            answer, chunks = self.answer_with_retrieval(message, history)
            source = "vectordb"
            logger.info("[Chatbot] 📚 Answered with VectorDB (2 API calls)")

        # Step 4 — Persist messages
        self._db.add_message(
            session_id, "user", message,
            metadata={"input_type": "text"},
        )
        self._db.add_message(
            session_id, "assistant", answer,
            metadata={
                "source": source,
                "chunks_used": len(chunks) if chunks else 0,
            },
        )

        return {
            "answer": answer,
            "source": source,
            "retrieved_chunks": chunks,
        }
