# DocChat — RAG-powered PDF Assistant

> Upload any PDF and ask questions. Answers are grounded in your document with source chunks shown for transparency.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green) ![React](https://img.shields.io/badge/React-18-61DAFB) ![ChromaDB](https://img.shields.io/badge/ChromaDB-vector--store-orange) ![Claude API](https://img.shields.io/badge/Claude-API-blueviolet)

---

## What it does

DocChat lets you upload any PDF and have a grounded conversation with it. Instead of sending the entire document to an LLM (expensive, hits token limits), it uses a **RAG (Retrieval-Augmented Generation)** pipeline to find only the most relevant sections and answer from those.

---

## Architecture

### Ingestion pipeline (runs on upload)
```
PDF file
  └─► PyMuPDF extracts raw text page by page
        └─► Text split into 500-char chunks with 100-char overlap
              └─► sentence-transformers (all-MiniLM-L6-v2) embeds each chunk
                    └─► ChromaDB stores vectors + metadata (doc_id, filename, chunk_index)
```

### Query pipeline (runs on every question)
```
User question
  └─► Embed question using same model (all-MiniLM-L6-v2)
        └─► ChromaDB retrieves top-4 semantically similar chunks (filtered by doc_id)
              └─► Chunks injected into prompt as context
                    └─► Claude API (claude-sonnet-4) answers from context only
                          └─► Answer + source chunks returned to React UI
```

> **Why the same embedding model for both chunks and query?**
> Similarity search only works when vectors live in the same space. Using different models for ingestion vs retrieval breaks semantic search entirely.

> **Why 100-char overlap between chunks?**
> If an answer spans a chunk boundary, overlap ensures neither chunk loses the surrounding context needed to answer correctly.

---

## Tech stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React + Vite | Chat UI, PDF upload, source chunk display |
| Backend | FastAPI (Python) | REST API, request handling |
| PDF extraction | PyMuPDF (fitz) | Extract raw text from PDFs |
| Embeddings | sentence-transformers | Convert text to vectors |
| Vector store | ChromaDB | Store and retrieve vectors by similarity |
| LLM | Anthropic Claude API | Generate grounded answers |
| Deployment | Vercel + Render | Frontend + backend hosting |

---

## API endpoints

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| POST | `/upload` | `file` (multipart) | Upload a PDF, returns `doc_id` |
| POST | `/ask` | `{ question, doc_id }` | Ask a question, returns answer + source chunks |
| GET | `/documents` | — | List all uploaded documents |

---

## Local setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Anthropic API key ([get one here](https://console.anthropic.com))

### 1. Clone the repo
```bash
git clone https://github.com/Vandanakk/RAG-Powered-PDF-Assistant-DocChat-.git
cd RAG-Powered-PDF-Assistant-DocChat-
```

### 2. Backend
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set your API key
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=your_key_here

# Start the server
python main.py
# API running at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 3. Frontend
```bash
# In a new terminal
cd frontend
npm install
npm run dev
# App running at http://localhost:5173
```

---

## Deployment

### Backend → Render
1. Connect your GitHub repo to Render
2. Set environment variable: `ANTHROPIC_API_KEY`
3. Start command: `uvicorn main:app --host 0.0.0.0 --port 10000`

### Frontend → Vercel
1. Connect `/frontend` folder to Vercel, framework = Vite
2. Update the `API` constant in `src/App.jsx` to your Render backend URL
3. Deploy

---

## Project structure

```
docchat/
├── backend/
│   ├── main.py          # FastAPI app, route definitions
│   ├── rag.py           # Core RAG pipeline (ingest, retrieve, answer)
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx      # Main UI component
    │   ├── App.css      # Styles
    │   └── main.jsx     # Entry point
    ├── index.html
    └── package.json
```

---
