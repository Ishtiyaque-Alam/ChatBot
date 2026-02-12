"""
Task 3 — ASR Deployment: FastAPI server for Automatic Speech Recognition

Deploys an ASR model using FastAPI that accepts audio input and returns
the transcribed text.

Model:  ai4bharat/indicwav2vec-hindi  (Hindi ASR)

Endpoints:
    POST /transcribe  — accepts audio file, returns {"text": "...", "language": "hi"}
    GET  /health      — health-check

Run:
    uvicorn task3_asr_server:app --host 0.0.0.0 --port 8080

Swagger docs:
    http://localhost:8000/docs
"""

import io
import logging
import subprocess
import tempfile
from pathlib import Path

import librosa
import os
import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from transformers import AutoModelForCTC, AutoProcessor
from moviepy.editor import AudioFileClip
from utils.config import ASR_MODEL_NAME

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="ASR Service — AI4Bharat",
    description=(
        "Automatic Speech Recognition endpoint using the "
        f"`{ASR_MODEL_NAME}` model. Upload an audio file and get "
        "the transcribed Hindi text."
    ),
    version="1.0.0",
)

# ── Global model references (loaded at startup) ─────────────────────────────
processor = None
model = None
device = None


@app.on_event("startup")
async def load_model() -> None:
    """Load the ASR model and processor into GPU/CPU memory at server start."""
    global processor, model, device

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Loading ASR model: {ASR_MODEL_NAME}  (device={device})")

    processor = AutoProcessor.from_pretrained(ASR_MODEL_NAME)
    model = AutoModelForCTC.from_pretrained(ASR_MODEL_NAME).to(device)
    model.eval()

    logger.info("ASR model loaded successfully.")


# ── Helper ───────────────────────────────────────────────────────────────────

def convert_to_wav(audio_bytes, original_filename="audio.webm"):
    """Convert any audio format to 16kHz mono WAV using imageio-ffmpeg (bundled with moviepy)."""
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    suffix = os.path.splitext(original_filename)[1] or ".webm"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        input_path = tmp.name

    wav_path = input_path + ".wav"

    try:
        result = subprocess.run(
            [ffmpeg_exe, "-y", "-i", input_path, "-ar", "16000", "-ac", "1",
             "-f", "wav", wav_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr[:300]}")
        logger.info(f"Converted {suffix} → WAV via imageio-ffmpeg")
    finally:
        Path(input_path).unlink(missing_ok=True)

    return wav_path


def transcribe_audio(audio_bytes, original_filename="audio.webm"):
    """Convert to WAV, then transcribe with Wav2Vec2 model."""
    wav_path = convert_to_wav(audio_bytes, original_filename)

    try:
        # Load audio
        speech, sr = librosa.load(wav_path, sr=16000, mono=True)
        logger.info(
            f"Audio loaded: duration={len(speech)/sr:.2f}s, "
            f"sample_rate={sr}, samples={len(speech)}"
        )

        # Preprocess + inference
        inputs = processor(
            speech, sampling_rate=16000,
            return_tensors="pt", padding=True,
        )
        input_values = inputs.input_values.to(device)

        with torch.no_grad():
            logits = model(input_values).logits

        # Decode
        logits_np = logits[0].cpu().numpy()
        transcription = processor.decode(logits_np).text
        logger.info(f"Transcription: {transcription}")
        return transcription.strip()

    finally:
        Path(wav_path).unlink(missing_ok=True)

# ── Endpoints ────────────────────────────────────────────────────────────────

@app.post(
    "/transcribe",
    summary="Transcribe audio to text",
    response_description="JSON with transcribed text and language code",
)
async def transcribe_endpoint(
    file: UploadFile = File(
        ...,
        description="Audio file (WAV, MP3, FLAC, OGG, etc.)",
    ),
) -> JSONResponse:
    """
    Accept an audio file upload and return the transcribed text.

    **Supported formats:** WAV, MP3, FLAC, OGG, and any format
    supported by `librosa` / `soundfile`.

    **Returns:**
    ```json
    {
        "text": "transcribed text here",
        "language": "hi",
        "model": "ai4bharat/indicwav2vec-hindi"
    }
    ```
    """
    if not file:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    try:
        audio_bytes = await file.read()
        if len(audio_bytes) == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        logger.info(
            f"Received audio: filename={file.filename}, "
            f"size={len(audio_bytes):,} bytes"
        )

        text = transcribe_audio(audio_bytes, original_filename=file.filename or "audio.wav")

        return JSONResponse(
            content={
                "text": text,
                "language": "hi",
                "model": ASR_MODEL_NAME,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Transcription failed")
        err_msg = str(e) or f"{type(e).__name__}: (no message)"
        raise HTTPException(
            status_code=500,
            detail=f"Transcription error: {err_msg}",
        )


@app.get(
    "/health",
    summary="Health check",
    response_description="Service health status",
)
async def health_check() -> JSONResponse:
    """
    Returns the health status of the ASR service, including
    whether the model is loaded and the device being used.
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "model": ASR_MODEL_NAME,
            "model_loaded": model is not None,
            "device": str(device) if device else "not initialized",
        }
    )
