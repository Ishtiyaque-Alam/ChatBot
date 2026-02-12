"""
Centralized configuration and environment variable management.

Loads API keys and shared settings from a .env file at the project root.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env from the project root ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ── API Keys ─────────────────────────────────────────────────────────────────
SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR: Path = PROJECT_ROOT / "data"
CHROMA_DB_DIR: Path = DATA_DIR / "chroma_db"

# Ensure data directories exist at import time
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

# ── Model Settings ───────────────────────────────────────────────────────────
ASR_MODEL_NAME: str = "ai4bharat/indicwav2vec-hindi"
EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL_NAME: str = "llama-3.3-70b-versatile"

# ── ASR Server ───────────────────────────────────────────────────────────────
ASR_SERVER_URL: str = os.getenv("ASR_SERVER_URL", "http://localhost:8081")

# ── Sarvam Translation API ───────────────────────────────────────────────────
SARVAM_TRANSLATE_URL: str = "https://api.sarvam.ai/translate"

# ── Vector DB ────────────────────────────────────────────────────────────────
CHROMA_COLLECTION_NAME: str = "wikipedia_chunks"
CHUNK_SIZE: int = 500
CHUNK_OVERLAP: int = 100
TOP_K_RETRIEVAL: int = 2

# ── MySQL Chat History ───────────────────────────────────────────────────────
MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "ai4bharat_chat")
SLIDING_WINDOW_SIZE: int = 10
