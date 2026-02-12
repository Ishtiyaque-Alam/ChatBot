# Voice-Enabled RAG System

An end-to-end voice-enabled conversational system that scrapes Wikipedia articles, builds a vector database, transcribes audio via an ASR model, translates Indian languages to English, and generates answers using Retrieval-Augmented Generation (RAG). Includes a React frontend with a FastAPI backend for full-stack deployment.

---
![Demo Image](Assets\image.png)

![ChatBot UI](Assets\image-copy.png)
## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Individual Tasks](#running-individual-tasks)
  - [Task 1 - Data Collection](#task-1--data-collection-wikipedia-scraping)
  - [Task 2 - Vector Database](#task-2--vector-database)
  - [Task 3 - ASR Server](#task-3--asr-server)
  - [Task 4 - Translation](#task-4--translation)
  - [Task 5 - RAG Pipeline](#task-5--rag-pipeline)
- [Running the Full Application](#running-the-full-application)
  - [Backend Server](#1-backend-api-server)
  - [ASR Server](#2-asr-server)
  - [Frontend](#3-frontend-dev-server)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Observations and Challenges](#observations-and-challenges)

---

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- MySQL Server (for chat history persistence)
- NVIDIA GPU with CUDA (RTX 3050 Ti or better recommended for the ASR model)
- API keys:
  - **Sarvam AI**: Sign up at [sarvam.ai](https://www.sarvam.ai/) (free 1000 credits)
  - **Groq**: Sign up at [console.groq.com](https://console.groq.com/) (free LLM inference)

---

## Installation

### Python Backend

```bash
# Clone the repository
git clone https://github.com/Ishtiyaque-Alam/ChatBot.git
cd ChatBot

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install Python dependencies
pip install -r requirements.txt
```

### React Frontend

```bash
cd frontend
npm install
cd ..
```

---

## Configuration

Create a `.env` file in the project root with the following keys:

```env
SARVAM_API_KEY=your_sarvam_api_key
GROQ_API_KEY=your_groq_api_key

# MySQL (defaults shown)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=root
```

All configuration is centralized in `utils/config.py`. Environment variables override the defaults.

---

## Running Individual Tasks

Each task is a standalone script and can be run independently.

### Task 1 -- Data Collection (Wikipedia Scraping)

Searches Wikipedia for the closest article, scrapes its full text, and saves it to the `data/` directory.

```bash
python task1_data_collection.py --query "Mahatma Gandhi"
```

| Flag           | Description                                     |
|----------------|-------------------------------------------------|
| `--query`      | (Required) The Wikipedia search topic            |
| `--use-bs4`    | Use BeautifulSoup for richer HTML scraping        |
| `--output-dir` | Custom output directory (default: `data/`)        |

Output: `data/mahatma_gandhi.txt`

---

### Task 2 -- Vector Database

Chunks the scraped article text, generates embeddings using `all-MiniLM-L6-v2`, and stores them in a persistent ChromaDB collection.

```bash
python task2_vector_db.py --input data/mahatma_gandhi.txt
```

| Flag      | Description                                  |
|-----------|----------------------------------------------|
| `--input` | (Required) Path to the `.txt` file to embed  |

Output: Persistent ChromaDB collection at `data/chroma_db/`

If the vector database does not exist when queried at runtime, the system will auto-initialize it from any `.txt` files in the `data/` directory (or scrape a default Wikipedia article if no data files are present).

---

### Task 3 -- ASR Server

Starts a FastAPI server hosting the `ai4bharat/indicwav2vec-hindi` ASR model. This server is used by the RAG pipeline and the backend API to transcribe audio.

```bash
uvicorn task3_asr_server:app --host 0.0.0.0 --port 8081
```

API documentation is available at `http://localhost:8081/docs` once running.

Testing the endpoint directly:

```bash
curl -X POST http://localhost:8081/transcribe -F "Assets\Recording (4) copy.wav"
```

Response:

```json
{
  "text": "transcribed hindi text",
  "language": "hi",
  "model": "ai4bharat/indicwav2vec-hindi"
}
```

---

### Task 4 -- Translation

Translates Indian-language text to English using the Sarvam AI translation API.

```bash
python task4_translation.py --text "नमस्ते दुनिया" --source hi-IN
```

| Flag       | Description                                             |
|------------|---------------------------------------------------------|
| `--text`   | (Required) Text to translate                             |
| `--source` | (Required) Source language BCP-47 code (e.g., `hi-IN`)   |
| `--target` | Target language code (default: `en-IN`)                  |

---

### Task 5 -- RAG Pipeline

Runs the full end-to-end pipeline: Audio transcription, translation, vector retrieval, and LLM-based answer generation.

**Prerequisite**: The ASR server (Task 3) must be running.

```bash
python task5_rag_pipeline.py --audio path/to/question.wav --source hi-IN
```

The pipeline executes in four steps:

1. **Transcribe** -- Sends audio to the ASR server for Hindi transcription
2. **Translate** -- Converts the Hindi transcription to English via Sarvam API
3. **Retrieve** -- Queries the ChromaDB vector database for relevant context
4. **Generate** -- Sends the query and retrieved context to Groq LLM for the final answer

---

## Running the Full Application

To run the complete system with the React frontend and FastAPI backend, start all three services.

### 1. Backend API Server

The unified API server handles sessions, text/audio chat, and history. It connects the frontend to the chatbot pipeline and MySQL database.

```bash
# From the project root (with venv activated)
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

API endpoints:

| Method | Endpoint                          | Description                    |
|--------|-----------------------------------|--------------------------------|
| POST   | `/api/session`                    | Create a new chat session      |
| GET    | `/api/sessions`                   | List all sessions              |
| GET    | `/api/session/{id}/history`       | Get message history            |
| POST   | `/api/chat`                       | Send a text message            |
| POST   | `/api/chat/audio`                 | Send an audio message          |
| GET    | `/health`                         | Health check                   |

### 2. ASR Server

Required for audio message processing.

```bash
uvicorn task3_asr_server:app --host 0.0.0.0 --port 8081
```

### 3. Frontend Dev Server

```bash
cd frontend
npm run dev
```

The frontend is accessible at `http://localhost:5173`. API requests are proxied to the backend via the Vite dev server configuration.

### Quick Start (All Services)

Open three separate terminals and run:

```bash
# Terminal 1 -- Backend API
venv\Scripts\activate
uvicorn api_server:app --host 0.0.0.0 --port 8000

# Terminal 2 -- ASR Server
venv\Scripts\activate
uvicorn task3_asr_server:app --host 0.0.0.0 --port 8081

# Terminal 3 -- Frontend
cd frontend
npm run dev
```

Then open `http://localhost:5173` in your browser.

---

## Technology Stack

| Component          | Technology                               | Reason                                                |
|--------------------|------------------------------------------|-------------------------------------------------------|
| Wikipedia Search   | `wikipedia` Python library               | Wraps MediaWiki API; no API key required              |
| Web Scraping       | `beautifulsoup4` + `requests`            | Fallback for richer HTML parsing                      |
| Text Chunking      | LangChain `RecursiveCharacterTextSplitter` | Smart splitting by paragraph, sentence, and word    |
| Embeddings         | `all-MiniLM-L6-v2`                      | Fast, 384-dimensional, excellent quality/speed ratio  |
| Vector DB          | ChromaDB                                 | Zero-config, pip-installable, persistent on-disk      |
| ASR Model          | `ai4bharat/indicwav2vec-hindi`           | Open-source Hindi ASR from AI4Bharat                  |
| Backend Framework  | FastAPI                                  | Auto-generated docs, async support, type validation   |
| Translation        | Sarvam AI (`mayura:v1`)                  | Supports 12+ Indian languages                        |
| LLM                | Groq (Llama 3.3 70B)                    | Free tier, fast inference                             |
| Chat History       | MySQL + SQLAlchemy                       | Persistent session and message storage                |
| Frontend           | React + Vite + Tailwind CSS v4           | Modern SPA with hot reload and utility-first styling  |
| Gradio UI          | Gradio                                   | Standalone chat interface with audio recording        |

### Chunking Parameters

- **Chunk size**: 500 characters (~80-120 tokens) -- fits within the 256-token context window of `all-MiniLM-L6-v2` while preserving paragraph-level semantics.
- **Overlap**: 100 characters -- sentences spanning chunk boundaries are captured in both adjacent chunks, preventing information loss.

### Vector DB: ChromaDB

Benefits:
- Zero configuration, pip-installable
- Persistent on-disk storage
- Built-in embedding function support
- Simple Python API with metadata filtering

Drawbacks:
- Single-process only (not suited for distributed deployments)
- Not designed for billion-scale datasets

For a single-article knowledge base, ChromaDB is the ideal lightweight choice.

---

## Project Structure

```
AI4Bharat/
├── .env                        # API keys and database credentials
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── task1_data_collection.py    # Task 1: Wikipedia article scraping
├── task2_vector_db.py          # Task 2: Vector DB creation + auto-init
├── task3_asr_server.py         # Task 3: FastAPI ASR server
├── task4_translation.py        # Task 4: Sarvam translation
├── task5_rag_pipeline.py       # Task 5: End-to-end RAG pipeline
│
├── api_server.py               # Unified backend API for the frontend
├── chatbot.py                  # VoiceChatbot class (orchestrates pipeline)
├── chat_db.py                  # MySQL chat history (SQLAlchemy ORM)
├── app.py                      # Gradio chat UI (standalone)
│
├── utils/
│   └── config.py               # Centralized configuration
│
├── data/                       # Generated data (gitignored)
│   ├── *.txt                   # Scraped Wikipedia articles
│   └── chroma_db/              # Persistent vector database
│
└── frontend/                   # React frontend application
    ├── src/
    │   ├── pages/              # Homepage, ChatbotPage
    │   ├── components/         # Sidebar, ChatWindow, InputBar, Orb
    │   └── services/           # API client layer
    ├── vite.config.js          # Vite config with API proxy
    └── package.json            # Node.js dependencies
```

---

## Observations and Challenges

1. **Wikipedia Disambiguation**: The `wikipedia` library can hit disambiguation pages. This is handled by automatically selecting the first option from the disambiguation list.

2. **ASR Model Loading Time**: The `indicwav2vec-hindi` model takes approximately 10-15 seconds to load at server startup. Once loaded, inference is fast on GPU.

3. **Audio Format Handling**: Browser recordings use WebM/Opus format. The ASR server converts audio to 16kHz mono WAV using the bundled `imageio-ffmpeg` binary before processing with librosa.

4. **Sarvam API Character Limit**: The `mayura:v1` translation model has a 1000-character limit per request. For typical voice questions, this is sufficient.

5. **ChromaDB Auto-Initialization**: If the vector database collection does not exist when a query requires it, the system automatically chunks and embeds available data files, or scrapes a default Wikipedia article if no data is present.

6. **GPU Memory**: The RTX 3050 Ti (4GB VRAM) handles the ASR model. The embedding model runs on CPU, keeping GPU memory free for ASR inference.

7. **Modular Design**: Each task is a standalone script that can be run independently. Task 5, the Gradio UI, and the API server import functions from the task modules for integration.
