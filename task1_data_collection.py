"""
Task 1 — Data Collection: Wikipedia Article Scraping

Finds the closest Wikipedia article for a given search query, scrapes its
full text, and saves it to a .txt file.

Usage:
    python task1_data_collection.py --query "Artificial Intelligence"

Approach:
    1. Uses the `wikipedia` library (wraps MediaWiki API) to search for the
       closest article — no external API key required.
    2. Falls back to BeautifulSoup scraping if the library text is incomplete.
    3. Cleans the article text (removes references, extra whitespace).
    4. Saves output to  data/<sanitized_topic>.txt
"""

import argparse
import re
import sys
import logging
from pathlib import Path

import requests
import wikipedia
from bs4 import BeautifulSoup

# Project-level config
from utils.config import DATA_DIR

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Core Functions ───────────────────────────────────────────────────────────

def search_wikipedia(query: str) -> str:
    """
    Search Wikipedia and return the title of the closest matching article.

    Args:
        query: The search term / topic.

    Returns:
        Title of the best-matching Wikipedia page.

    Raises:
        ValueError: If no results are found for the query.
    """
    logger.info(f"Searching Wikipedia for: '{query}'")
    results = wikipedia.search(query, results=5)

    if not results:
        raise ValueError(f"No Wikipedia articles found for query: '{query}'")

    logger.info(f"Search results: {results}")
    return results[0]  # closest match


def fetch_article_text(title: str) -> tuple[str, str]:
    """
    Fetch the full text and URL for a Wikipedia article.

    Handles disambiguation pages by selecting the first suggestion.

    Args:
        title: The Wikipedia article title.

    Returns:
        Tuple of (article_text, article_url).

    Raises:
        wikipedia.exceptions.PageError: If the page does not exist.
    """
    try:
        page = wikipedia.page(title, auto_suggest=True)
        logger.info(f"Found article: {page.title}")
        logger.info(f"URL: {page.url}")
        return page.content, page.url

    except wikipedia.exceptions.DisambiguationError as e:
        # Pick the first option from the disambiguation page
        logger.warning(
            f"'{title}' is a disambiguation page. "
            f"Trying first option: '{e.options[0]}'"
        )
        page = wikipedia.page(e.options[0], auto_suggest=False)
        return page.content, page.url


def scrape_article_bs4(url: str) -> str:
    """
    Fallback scraper using BeautifulSoup for richer text extraction.

    Extracts paragraph text from the Wikipedia page HTML, stripping
    reference markers like [1], [2], etc.

    Args:
        url: Full URL of the Wikipedia article.

    Returns:
        Cleaned article text.
    """
    logger.info(f"Scraping article with BeautifulSoup: {url}")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # The main article content lives inside div#mw-content-text
    content_div = soup.find("div", {"id": "mw-content-text"})
    if not content_div:
        raise ValueError("Could not locate article content on the page.")

    paragraphs = content_div.find_all("p")
    text = "\n\n".join(p.get_text() for p in paragraphs)

    # Strip citation markers like [1], [2], [note 1], etc.
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\[note \d+\]", "", text)
    text = re.sub(r"\[citation needed\]", "", text, flags=re.IGNORECASE)

    return text.strip()


def clean_text(text: str) -> str:
    """
    Clean article text by removing excess whitespace and artifacts.

    Args:
        text: Raw article text.

    Returns:
        Cleaned text.
    """
    # Remove section markers like  == Heading ==
    text = re.sub(r"={2,}\s*.*?\s*={2,}", "", text)
    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def sanitize_filename(name: str) -> str:
    """
    Convert an article title into a safe, lowercase filename slug.

    Args:
        name: The article title.

    Returns:
        A filename-safe slug (e.g. "artificial_intelligence").
    """
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[\s-]+", "_", slug)
    return slug


def save_text(text: str, filepath: Path) -> None:
    """
    Save the article text to a file.

    Args:
        text:     The cleaned article text.
        filepath: Destination Path object.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(text, encoding="utf-8")
    logger.info(f"Saved article text to: {filepath}")
    logger.info(f"File size: {filepath.stat().st_size:,} bytes")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    """Entry-point: parse CLI args, fetch article, save to file."""
    parser = argparse.ArgumentParser(
        description="Find the closest Wikipedia article for a topic and save its text.",
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Search query / topic (e.g. 'Artificial Intelligence').",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DATA_DIR),
        help=f"Directory to save the text file (default: {DATA_DIR}).",
    )
    parser.add_argument(
        "--use-bs4",
        action="store_true",
        help="Use BeautifulSoup scraper instead of the wikipedia library.",
    )
    args = parser.parse_args()

    try:
        # Step 1 — Search for the closest article
        title = search_wikipedia(args.query)

        # Step 2 — Fetch article text
        text, url = fetch_article_text(title)

        # Optionally re-scrape with BS4 for richer content
        if args.use_bs4:
            text = scrape_article_bs4(url)

        # Step 3 — Clean the text
        text = clean_text(text)

        if not text:
            logger.error("Fetched article text is empty. Aborting.")
            sys.exit(1)

        # Step 4 — Save to file
        output_dir = Path(args.output_dir)
        filename = sanitize_filename(title) + ".txt"
        filepath = output_dir / filename
        save_text(text, filepath)

        # Summary
        print(f"\n{'─' * 60}")
        print(f"  Topic searched : {args.query}")
        print(f"  Article found  : {title}")
        print(f"  Wikipedia URL  : {url}")
        print(f"  Saved to       : {filepath}")
        print(f"  Text length    : {len(text):,} characters")
        print(f"{'─' * 60}\n")

    except wikipedia.exceptions.PageError:
        logger.error(f"Wikipedia page not found for query: '{args.query}'")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
