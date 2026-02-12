"""
Task 4 — Translation: Sarvam AI Text-to-English Translation

Translates text from any supported Indian language to English using the
Sarvam AI Translation API (https://api.sarvam.ai/translate).

Usage (standalone):
    python task4_translation.py --text "नमस्ते दुनिया" --source hi-IN

Supported source languages:
    hi-IN, bn-IN, ta-IN, te-IN, mr-IN, gu-IN, kn-IN, ml-IN, pa-IN,
    od-IN, as-IN, ur-IN, and more. See Sarvam docs for the full list.

Note:
    This task makes an API call — no model is deployed locally.
    You need a SARVAM_API_KEY in your .env file.
"""

import argparse
import logging
import sys

import requests

from utils.config import SARVAM_API_KEY, SARVAM_TRANSLATE_URL

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Core Function ────────────────────────────────────────────────────────────

def translate_to_english(
    text: str,
    source_language_code: str = "hi-IN",
    model: str = "mayura:v1",
) -> str:
    """
    Translate text from an Indian language to English using Sarvam's API.

    Args:
        text:                  The text to translate (max 1000 chars for mayura:v1).
        source_language_code:  BCP-47 language code of the source text
                               (e.g. "hi-IN" for Hindi, "ta-IN" for Tamil).
        model:                 Translation model to use. Options:
                               "mayura:v1" (12 languages, multiple modes)
                               "sarvam-translate:v1" (22 languages, formal only)

    Returns:
        The translated English text.

    Raises:
        ValueError:  If the API key is not configured.
        RuntimeError: If the API call fails.
    """
    if not SARVAM_API_KEY:
        raise ValueError(
            "SARVAM_API_KEY not set. "
            "Please add it to your .env file. "
            "Sign up at https://www.sarvam.ai/ for free credits."
        )

    headers = {
        "Content-Type": "application/json",
        "api-subscription-key": SARVAM_API_KEY,
    }

    payload = {
        "input": text,
        "source_language_code": source_language_code,
        "target_language_code": "en-IN",
        "model": model,
        "mode": "formal",
        "enable_preprocessing": True,
    }

    logger.info(
        f"Translating ({source_language_code} → en-IN): "
        f"'{text[:80]}{'...' if len(text) > 80 else ''}'"
    )

    try:
        response = requests.post(
            SARVAM_TRANSLATE_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()
        translated_text = result.get("translated_text", "")

        if not translated_text:
            raise RuntimeError(
                f"Empty translation response. Full response: {result}"
            )

        logger.info(f"Translated: '{translated_text[:80]}...'")
        return translated_text

    except requests.exceptions.HTTPError as e:
        error_detail = ""
        try:
            error_detail = e.response.json()
        except Exception:
            error_detail = e.response.text
        raise RuntimeError(
            f"Sarvam API error ({e.response.status_code}): {error_detail}"
        ) from e
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error calling Sarvam API: {e}") from e


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    """Entry-point: parse CLI args and translate text."""
    parser = argparse.ArgumentParser(
        description="Translate Indian-language text to English using Sarvam AI.",
    )
    parser.add_argument(
        "--text",
        type=str,
        required=True,
        help="Text to translate.",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="hi-IN",
        help="Source language code (default: hi-IN). E.g. ta-IN, bn-IN, te-IN.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="mayura:v1",
        choices=["mayura:v1", "sarvam-translate:v1"],
        help="Translation model (default: mayura:v1).",
    )
    args = parser.parse_args()

    try:
        translated = translate_to_english(
            text=args.text,
            source_language_code=args.source,
            model=args.model,
        )
        print(f"\n{'─' * 60}")
        print(f"  Source ({args.source}): {args.text}")
        print(f"  English          : {translated}")
        print(f"{'─' * 60}\n")

    except (ValueError, RuntimeError) as e:
        logger.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
