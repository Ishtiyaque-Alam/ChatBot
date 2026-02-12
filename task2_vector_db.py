"""
Task 2 — Vector Database: Chunking, Embedding & Storage

Chunks a scraped Wikipedia article, generates embeddings with
sentence-transformers, and stores them in a persistent ChromaDB collection.

Usage:
    python task2_vector_db.py --input data/artificial_intelligence.txt

Design Decisions:
    Chunk Size (500 chars, 100-char overlap):
        - 500 characters ≈ 80–120 tokens, comfortably fits within the 256-token
          context of all-MiniLM-L6-v2 while preserving paragraph-level semantics.
        - Overlapping chunks (100 chars) prevent information loss at boundaries
          — sentences that span two chunks are captured in both.

    Embedding Model (all-MiniLM-L6-v2):
        - Free, fast, 384-dimensional vectors.  Runs entirely on-device.
        - Excellent quality-to-speed ratio for semantic search.

    Vector DB (ChromaDB):
        Benefits:
            • Zero-config, pip-installable, persistent on-disk storage.
            • Built-in embedding function support (can wrap sentence-transformers).
            • Metadata filtering and simple Python API.
        Drawbacks:
            • Single-process only — not suited for multi-server deployments.
            • Not designed for billion-scale datasets.
        For a single-article knowledge base this is the ideal lightweight choice.
"""

import argparse
import logging
import sys
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils.config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_DB_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL_NAME,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Core Functions ───────────────────────────────────────────────────────────

def load_text(filepath: Path) -> str:
    """
    Read the scraped article text from a file.

    Args:
        filepath: Path to the .txt file.

    Returns:
        The file contents as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError:        If the file is empty.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Input file not found: {filepath}")

    text = filepath.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"Input file is empty: {filepath}")

    logger.info(f"Loaded {len(text):,} characters from {filepath}")
    return text


def chunk_text(text: str) -> list[str]:
    """
    Split text into overlapping chunks using LangChain's
    RecursiveCharacterTextSplitter.

    Why overlapping chunks?
        Sentences that span a chunk boundary are fully captured in at
        least one chunk, preventing information loss during retrieval.

    Args:
        text: The full article text.

    Returns:
        List of text chunks.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    logger.info(
        f"Split text into {len(chunks)} chunks "
        f"(size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})"
    )
    return chunks


def create_vector_db(chunks: list[str], source_file: str) -> None:
    """
    Generate embeddings and store chunks in a persistent ChromaDB collection.

    Each chunk is stored with an ID and metadata containing the source
    filename and chunk index.

    Args:
        chunks:      List of text chunks.
        source_file: Name of the source file (for metadata).
    """
    # Initialize the embedding function (downloads model on first run)
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME,
    )

    # Persistent ChromaDB client
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

    # Delete existing collection if it exists (fresh build per article)
    try:
        client.delete_collection(name=CHROMA_COLLECTION_NAME)
        logger.info(f"Deleted existing collection: '{CHROMA_COLLECTION_NAME}'")
    except (ValueError, Exception) as e:
        if "not found" in str(e).lower() or "does not exist" in str(e).lower():
            pass  # Collection didn't exist
        else:
            raise

    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},  # cosine similarity
    )

    # Prepare documents, IDs, and metadata
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {"source": source_file, "chunk_index": i}
        for i in range(len(chunks))
    ]

    # Add to collection (embeddings are generated automatically)
    logger.info(f"Adding {len(chunks)} chunks to ChromaDB...")
    collection.add(
        documents=chunks,
        ids=ids,
        metadatas=metadatas,
    )

    logger.info(
        f"Vector DB created at: {CHROMA_DB_DIR}\n"
        f"  Collection : {CHROMA_COLLECTION_NAME}\n"
        f"  Documents  : {collection.count()}\n"
        f"  Embedding  : {EMBEDDING_MODEL_NAME}"
    )


def _auto_initialize_vector_db() -> None:
    """
    Auto-initialize the VectorDB from .txt files in the data directory.

    If no .txt files exist, scrapes a default Wikipedia article first
    using task1_data_collection.
    """
    from utils.config import DATA_DIR

    txt_files = list(DATA_DIR.glob("*.txt"))

    # If no data files exist, scrape a default article
    if not txt_files:
        logger.info("[Auto-init] No data files found. Scraping default Wikipedia article...")
        from task1_data_collection import (
            search_wikipedia, fetch_article_text, clean_text,
            sanitize_filename, save_text,
        )
        default_query = "Mahatma Gandhi"
        title = search_wikipedia(default_query)
        text, url = fetch_article_text(title)
        text = clean_text(text)
        filename = sanitize_filename(title) + ".txt"
        filepath = DATA_DIR / filename
        save_text(text, filepath)
        txt_files = [filepath]
        logger.info(f"[Auto-init] Scraped '{title}' → {filepath}")

    # Chunk and embed all .txt files
    for txt_file in txt_files:
        logger.info(f"[Auto-init] Processing: {txt_file.name}")
        text = load_text(txt_file)
        chunks = chunk_text(text)
        create_vector_db(chunks, source_file=txt_file.name)

    logger.info("[Auto-init] ✅ VectorDB initialized successfully.")


def query_vector_db(query: str, n_results: int = 2) -> list[dict]:
    """
    Query the vector database and return the top-k closest chunks.

    If the collection does not exist, auto-initializes the VectorDB
    by scraping data and building the collection first.

    Args:
        query:     The search query string.
        n_results: Number of results to return (default 2).

    Returns:
        List of dicts with keys 'text', 'metadata', and 'distance'.
    """
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME,
    )
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

    # Try to get the collection — auto-initialize if it doesn't exist
    try:
        collection = client.get_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=embedding_fn,
        )
    except Exception as e:
        if "not found" in str(e).lower() or "does not exist" in str(e).lower():
            logger.warning(
                f"[VectorDB] Collection '{CHROMA_COLLECTION_NAME}' not found. "
                "Auto-initializing..."
            )
            _auto_initialize_vector_db()
            # Retry after initialization
            collection = client.get_collection(
                name=CHROMA_COLLECTION_NAME,
                embedding_function=embedding_fn,
            )
        else:
            raise

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    output = []
    for i in range(len(results["documents"][0])):
        output.append({
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return output


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    """Entry-point: parse CLI args, chunk text, build vector DB."""
    parser = argparse.ArgumentParser(
        description="Create a vector database from a scraped Wikipedia article.",
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to the scraped Wikipedia .txt file.",
    )
    args = parser.parse_args()

    filepath = Path(args.input)

    try:
        # Step 1 — Load the text
        text = load_text(filepath)

        # Step 2 — Chunk the text
        chunks = chunk_text(text)

        # Step 3 — Create vector DB with embeddings
        create_vector_db(chunks, source_file=filepath.name)

        # Summary
        print(f"\n{'─' * 60}")
        print(f"  Source file  : {filepath}")
        print(f"  Chunks       : {len(chunks)}")
        print(f"  Chunk size   : {CHUNK_SIZE} chars, {CHUNK_OVERLAP} overlap")
        print(f"  Embedding    : {EMBEDDING_MODEL_NAME}")
        print(f"  Vector DB    : ChromaDB @ {CHROMA_DB_DIR}")
        print(f"{'─' * 60}\n")

        # Quick sanity check — query with a sample
        sample_query = chunks[0][:100] if chunks else "test"
        results = query_vector_db(sample_query, n_results=2)
        print("Sanity check — top-2 results for a sample query:")
        for i, r in enumerate(results, 1):
            preview = r["text"][:120].replace("\n", " ")
            print(f"  {i}. (dist={r['distance']:.4f}) {preview}...")
        print()

    except (FileNotFoundError, ValueError) as e:
        logger.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
