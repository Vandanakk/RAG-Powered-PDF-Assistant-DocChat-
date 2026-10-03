# DocChat — Full-Stack RAG-Powered PDF Assistant

DocChat is a production-grade, full-stack Retrieval-Augmented Generation (RAG) application that allows users to upload PDF documents and ask questions grounded strictly in their content.

Responses are generated using Google Gemini and backed by vector similarity search with ChromaDB and `all-MiniLM-L6-v2` embeddings, ensuring zero hallucinations from general LLM knowledge.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│                   React + TypeScript                   │
│              (Vite + Tailwind CSS + Axios)             │
│            Runs on http://localhost:5173              │
└───────────────────────────┬────────────────────────────┘
                            │ REST API Requests
                            ▼
┌────────────────────────────────────────────────────────┐
│                     FastAPI App                        │
│             Runs on http://localhost:8000              │
│                                                        │
│  ┌───────────────────┐        ┌─────────────────────┐  │
│  │    PDF Service    │        │  Embedding Service  │  │
│  │ (PyMuPDF Chunking)│        │(all-MiniLM-L6-v2)   │  │
│  └─────────┬─────────┘        └──────────┬──────────┘  │
│            │                             │             │
│            ▼                             ▼             │
│  ┌──────────────────────────────────────────────────┐  │
│  │       Persistent ChromaDB Vector Store           │  │
│  │           (Scoped by document_id)                │  │
│  └──────────────────────────┬───────────────────────┘  │
│                             │ Retrieved Top-k Chunks   │
│                             ▼                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │               Gemini LLM Service                 │  │
│  │   (Strict grounded prompt: answer ONLY from doc) │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### RAG Pipeline Mechanics
1. **Document Upload**:
   - PyMuPDF extracts text page-by-page.
   - Text is split into **500-character chunks with 100-character overlap**.
   - Each chunk retains its 1-indexed **page number**, **chunk index**, and unique **document_id**.
   - `sentence-transformers` (`all-MiniLM-L6-v2`) computes vector embeddings (model loaded **once** at server boot).
   - Vectors, text, and metadata are indexed into persistent ChromaDB storage (`data/chroma/`).
2. **Document Isolation**:
   - All queries filter strictly by `where={"document_id": document_id}`.
   - Chunks from different documents are never mixed.
3. **Question Answering & Grounding**:
   - The user query is embedded with `all-MiniLM-L6-v2`.
   - The top-k most relevant chunks are retrieved from ChromaDB.
   - Gemini receives ONLY the retrieved snippets along with the strict instruction:
     > *"Answer the user's question using ONLY the provided document context. If the answer cannot be found in the provided context, say: 'I couldn't find the answer in the uploaded document.' Do not invent information."*
   - Returns the answer along with cited sources (page numbers and exact text snippets).

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application, CORS, lifespan startup
│   │   ├── config.py               # Centralized configuration & environment loader
│   │   ├── models.py               # Pydantic schemas (Request/Response models)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── pdf_service.py      # PyMuPDF text extraction & chunking
│   │   │   ├── embedding_service.py# SentenceTransformer singleton loader & caching
│   │   │   ├── vector_service.py   # ChromaDB persistent client & registry
│   │   │   ├── llm_service.py      # Google GenAI Gemini client & grounded prompt
│   │   │   └── rag_service.py      # Orchestration pipeline
│   │   └── api/
│   │       ├── __init__.py
│   │       └── routes.py           # FastAPI endpoints (/upload, /chat, /documents, /health)
│   ├── tests/
│   │   └── test_api.py             # Pytest suite (health, upload, isolation, chat)
│   └── requirements.txt            # Backend Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── FileUpload.tsx      # Upload button, progress bar & error/success alerts
│   │   │   ├── DocumentList.tsx    # Sidebar document selector with page counts
│   │   │   ├── ChatWindow.tsx      # Chat conversation view with sources & empty states
│   │   │   ├── ChatInput.tsx       # Auto-expanding chat input with Enter to send
│   │   │   └── SourceCard.tsx      # Citation card showing page number and text snippet
│   │   ├── services/
│   │   │   └── api.ts              # Axios client with TypeScript interfaces
│   │   ├── types/
│   │   │   └── index.ts            # Frontend TypeScript type definitions
│   │   ├── App.tsx                 # Main layout & state coordination
│   │   ├── main.tsx                # React DOM root
│   │   └── index.css               # Tailwind CSS styles & modern dark theme
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── data/
│   ├── chroma/                     # Persistent ChromaDB storage (gitignored)
│   └── documents.json              # Document metadata registry
├── .env.example                    # Environment variable template
├── .gitignore                      # Git ignore rules
├── rag_pipeline.py                 # Original standalone script (preserved)
├── search.py                       # Original similarity search test (preserved)
├── database_test.py                # Original ChromaDB test script (preserved)
└── llm_test.py                     # Original Gemini test script (preserved)
```

---

## Step-by-Step Setup Guide

### 1. Clone the Project
```bash
git clone https://github.com/Vandanakk/RAG-Powered-PDF-Assistant-DocChat-.git
cd RAG-Powered-PDF-Assistant-DocChat-
```

---

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:

**macOS / Linux:**
```bash
cp .env.example .env
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

Open `.env` and set your Google Gemini API key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
CHROMA_PERSIST_DIR=./data/chroma
TOP_K_CHUNKS=2
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

---

### 3. Backend Setup

#### 3.1 Create and Activate Virtual Environment

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### 3.2 Install Backend Dependencies
```bash
pip install -r backend/requirements.txt
```

#### 3.3 Run Backend Tests
Run the automated test suite to verify upload validation, document isolation, and health checks:
```bash
cd backend
python -m pytest tests/test_api.py -v
cd ..
```

#### 3.4 Start FastAPI Server
From the `backend` directory:
```bash
cd backend
uvicorn app.main:app --reload
```
The backend API is now running at `http://localhost:8000` (Interactive Swagger docs available at `http://localhost:8000/docs`).

---

### 4. Frontend Setup

In a **new terminal window**:

#### 4.1 Install Frontend Dependencies
```bash
cd frontend
npm install
```

#### 4.2 Start React Development Server
```bash
npm run dev
```
The frontend is now running at `http://localhost:5173`.

---

### 5. Using the Application

1. **Open the App**: Navigate to `http://localhost:5173` in your browser.
2. **Verify Connection**: Look at the top-right of the sidebar — a green indicator confirms DocChat is connected to FastAPI.
3. **Upload a PDF**:
   - Click the **"Upload PDF"** button in the sidebar.
   - Select any PDF document from your computer.
   - Watch the progress bar as DocChat extracts text, chunks it, encodes embeddings, and indexes it into ChromaDB.
   - Upon completion, the new document is automatically selected.
4. **Ask a Question**:
   - Type your question in the chat input at the bottom and press `Enter` (or click the Send button).
   - Alternatively, click one of the suggested sample questions in the empty state.
5. **Inspect Answers and Citations**:
   - View the grounded answer generated by Gemini.
   - Expand the **"Retrieved Sources"** section below the answer to inspect the exact page numbers and chunk snippets used to answer.

---

## API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check returning `{"status": "ok"}` |
| `POST` | `/api/documents/upload` | Upload and chunk PDF, compute embeddings, store in ChromaDB |
| `POST` | `/api/chat` | Submit question with `document_id`, retrieve chunks, answer via Gemini |
| `GET` | `/api/documents` | List all uploaded documents with page and chunk counts |
| `DELETE` | `/api/documents/{document_id}` | Delete document embeddings from ChromaDB and metadata registry |

### Sample Chat Request:
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc_xxxx",
    "question": "What is the primary conclusion of the document?"
  }'
```

### Sample Chat Response:
```json
{
  "answer": "The primary conclusion is that...",
  "sources": [
    {
      "page": 4,
      "text": "In conclusion, our results demonstrate...",
      "chunk_index": 7
    }
  ]
}
```

---

## Production Deployment Guide

DocChat is architected to deploy cleanly with zero code modifications:
- **Backend**: FastAPI Web Service on **Render**
- **Frontend**: Single-Page React App on **Vercel**

### 1. Backend on Render (Python Web Service)

#### Option A: Blueprint (`render.yaml`)
1. Push your repository to GitHub.
2. In the Render Dashboard, click **New +** → **Blueprint**.
3. Select your repository. Render automatically reads `render.yaml`.
4. Enter the required secret environment variables (`GEMINI_API_KEY`, `CORS_ORIGINS`).

#### Option B: Manual Configuration
1. In Render, select **New +** → **Web Service**.
2. Connect your GitHub repository.
3. Configure the service settings:
   - **Name**: `docchat-backend`
   - **Region**: Nearest to your users (e.g., Oregon, Frankfurt)
   - **Root Directory**: `backend`
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. In **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.11.8`
   - `GEMINI_API_KEY`: *(Your Google Gemini API Key)*
   - `GEMINI_MODEL`: `gemini-2.5-flash`
   - `TOP_K_CHUNKS`: `5`
   - `CORS_ORIGINS`: `https://<your-vercel-app>.vercel.app` *(update once Vercel is deployed)*
   - *(Optional for paid disk)* `DATA_DIR`: `/var/data`

> [!IMPORTANT]
> **ChromaDB Cloud Persistence Considerations**:
> - Render free instances have an **ephemeral disk**. Documents uploaded during a live session remain queryable while the container is active, but if the free instance spins down due to inactivity (15 mins), the filesystem resets.
> - To persist documents across restarts on Render, attach a **Persistent Disk** (Render Starter plan or above) mounted at `/var/data` and set `DATA_DIR=/var/data`. DocChat automatically stores both ChromaDB vectors and `documents.json` inside the mounted disk.

---

### 2. Frontend on Vercel

1. In the Vercel Dashboard, click **Add New...** → **Project**.
2. Import your GitHub repository.
3. In **Project Configuration**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. In **Environment Variables**, add:
   - `VITE_API_BASE_URL`: `https://<your-render-service-name>.onrender.com/api`
5. Click **Deploy**.
6. Once deployed, copy your production Vercel URL (e.g. `https://docchat-app.vercel.app`) and add it to `CORS_ORIGINS` in your Render Backend environment variables.

---

## Standalone Test Scripts (Preserved)

The original CLI scripts have been preserved for experimentation:
- `python rag_pipeline.py`: Original CLI RAG pipeline.
- `python search.py`: Standalone embedding cosine similarity demonstration.
- `python database_test.py`: Standalone ChromaDB persistent client test.
- `python llm_test.py`: Standalone Gemini API test (loads key from `.env`).

