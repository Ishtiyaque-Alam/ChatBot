"""
Task 5 — RAG Pipeline: End-to-End Voice-Enabled Question Answering

Integrates all components into a single pipeline:
    Audio → ASR (Task 3) → Translate (Task 4) → Retrieve (Task 2) → LLM → Answer

Usage:
    1. Make sure the ASR server is running:
       uvicorn task3_asr_server:app --host 0.0.0.0 --port 8000

    2. Make sure the vector DB has been populated:
       python task2_vector_db.py --input data/<article>.txt

    3. Run the pipeline:
       python task5_rag_pipeline.py --audio question.wav

    4. (Optional) Specify source language if not Hindi:
       python task5_rag_pipeline.py --audio question.wav --source ta-IN
"""

import argparse
import logging
import sys
from pathlib import Path

import requests
from groq import Groq

from task2_vector_db import query_vector_db
from task4_translation import translate_to_english
from utils.config import (
    ASR_SERVER_URL,
    GROQ_API_KEY,
    LLM_MODEL_NAME,
    TOP_K_RETRIEVAL,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Pipeline Steps ───────────────────────────────────────────────────────────

def step1_transcribe(audio_path: Path) -> str:
    """
    Step 1: Send audio to the ASR FastAPI endpoint for transcription.

    Args:
        audio_path: Path to the audio file.

    Returns:
        Transcribed text (in the original language).

    Raises:
        FileNotFoundError: If the audio file does not exist.
        RuntimeError:      If the ASR server is unreachable or returns an error.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    url = f"{ASR_SERVER_URL}/transcribe"
    logger.info(f"[Step 1] Transcribing audio: {audio_path}")

    try:
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/wav")}
            response = requests.post(url, files=files, timeout=120)

        response.raise_for_status()
        result = response.json()
        transcription = result.get("text", "")

        if not transcription:
            raise RuntimeError("ASR returned empty transcription.")

        logger.info(f"[Step 1] Transcription: {transcription}")
        return transcription

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot connect to ASR server at {ASR_SERVER_URL}. "
            "Make sure it is running: "
            "uvicorn task3_asr_server:app --host 0.0.0.0 --port 8000"
        )
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"ASR server error: {e.response.text}") from e


def step2_translate(text: str, source_language: str = "hi-IN") -> str:
    """
    Step 2: Translate the transcribed text to English using Sarvam API.

    If the source language is already English, the text is returned as-is.

    Args:
        text:             Text in the source language.
        source_language:  BCP-47 language code (e.g. "hi-IN").

    Returns:
        English translation.
    """
    if source_language.startswith("en"):
        logger.info("[Step 2] Source is English — skipping translation.")
        return text

    logger.info(f"[Step 2] Translating from {source_language} to English...")
    translated = translate_to_english(text, source_language_code=source_language)
    logger.info(f"[Step 2] Translated: {translated}")
    return translated


def step3_retrieve(query: str, top_k: int = TOP_K_RETRIEVAL) -> list[dict]:
    """
    Step 3: Retrieve the top-k most relevant chunks from the Vector DB.

    Args:
        query: The English question text.
        top_k: Number of chunks to retrieve (default 2).

    Returns:
        List of dicts with 'text', 'metadata', and 'distance'.
    """
    logger.info(f"[Step 3] Retrieving top-{top_k} chunks for: '{query}'")
    results = query_vector_db(query, n_results=top_k)

    for i, r in enumerate(results, 1):
        logger.info(
            f"  Chunk {i} (dist={r['distance']:.4f}): "
            f"{r['text'][:80]}..."
        )
    return results


def step4_generate_answer(question: str, context_chunks: list[dict]) -> str:
    """
    Step 4: Use an LLM (Groq API with Llama 3) to generate an answer
    from the retrieved context.

    Args:
        question:        The user's question in English.
        context_chunks:  List of retrieved chunk dicts from the vector DB.

    Returns:
        The LLM-generated answer string.

    Raises:
        ValueError:  If the Groq API key is not configured.
        RuntimeError: If the LLM API call fails.
    """
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY not set. "
            "Please add it to your .env file. "
            "Sign up at https://console.groq.com/ for free."
        )

    # Build context from retrieved chunks
    context = "\n\n---\n\n".join(
        f"[Chunk {i+1}]\n{chunk['text']}"
        for i, chunk in enumerate(context_chunks)
    )

    system_prompt = (
        "You are a helpful assistant that answers questions based on the "
        "provided context from a Wikipedia article. Use ONLY the context "
        "below to answer. If the answer is not in the context, say so. "
        "Keep your answer concise and accurate."
    )

    user_prompt = (
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer:"
    )

    logger.info(f"[Step 4] Querying LLM ({LLM_MODEL_NAME})...")

    try:
        client = Groq(api_key=GROQ_API_KEY)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=LLM_MODEL_NAME,
            temperature=0.3,
            max_tokens=512,
        )
        answer = chat_completion.choices[0].message.content.strip()
        logger.info(f"[Step 4] Answer: {answer[:120]}...")
        return answer

    except Exception as e:
        raise RuntimeError(f"LLM API error: {e}") from e


# ── Full Pipeline ────────────────────────────────────────────────────────────

def run_pipeline(
    audio_path: Path,
    source_language: str = "hi-IN",
) -> dict:
    """
    Execute the full RAG pipeline: Audio → ASR → Translate → Retrieve → LLM.

    Args:
        audio_path:       Path to the input audio file.
        source_language:  BCP-47 language code of the spoken language.

    Returns:
        Dictionary with all intermediate and final results:
        {
            "transcription": str,
            "translation": str,
            "retrieved_chunks": list[dict],
            "answer": str,
        }
    """
    # Step 1 — Transcribe audio
    transcription = step1_transcribe(audio_path)

    # Step 2 — Translate to English
    translation = step2_translate(transcription, source_language)

    # Step 3 — Retrieve relevant chunks
    chunks = step3_retrieve(translation, top_k=TOP_K_RETRIEVAL)

    # Step 4 — Generate answer with LLM
    answer = step4_generate_answer(translation, chunks)

    return {
        "transcription": transcription,
        "translation": translation,
        "retrieved_chunks": chunks,
        "answer": answer,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    """Entry-point: parse CLI args and run the full RAG pipeline."""
    parser = argparse.ArgumentParser(
        description="End-to-end voice-enabled RAG pipeline.",
    )
    parser.add_argument(
        "--audio",
        type=str,
        required=True,
        help="Path to the audio file containing the question.",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="hi-IN",
        help="Source language code (default: hi-IN). E.g. ta-IN, bn-IN.",
    )
    args = parser.parse_args()

    audio_path = Path(args.audio)

    try:
        result = run_pipeline(audio_path, source_language=args.source)

        print(f"\n{'═' * 60}")
        print(f"  🎤 Transcription  : {result['transcription']}")
        print(f"  🌐 Translation    : {result['translation']}")
        print(f"  📚 Retrieved {len(result['retrieved_chunks'])} chunks")
        for i, c in enumerate(result["retrieved_chunks"], 1):
            preview = c["text"][:100].replace("\n", " ")
            print(f"       {i}. {preview}...")
        print(f"  💡 Answer         : {result['answer']}")
        print(f"{'═' * 60}\n")

    except (FileNotFoundError, ValueError, RuntimeError) as e:
        logger.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
