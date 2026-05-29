### DocChat — RAG-Powered PDF Assistant

Upload any PDF and ask questions. Answers are grounded in the document using a RAG pipeline.

## What it does

Instead of sending the entire PDF to an LLM, DocChat retrieves only the most relevant chunks and answers from those — keeping responses accurate and context-aware.

## How it works
PDF file
└─► PyMuPDF extracts text page by page
└─► Text split into 500-char chunks (100-char overlap)
└─► sentence-transformers embeds each chunk (all-MiniLM-L6-v2)
└─► ChromaDB stores vectors + metadata
User question
└─► Embedded with same model
└─► ChromaDB retrieves top-2 similar chunks
└─► Gemini API answers using chunks as context

## Stack
- Python
- PyMuPDF — PDF text extraction
- sentence-transformers — vector embeddings
- ChromaDB — local vector store
- Gemini API — answer generation

## Setup

```bash
pip install pymupdf chromadb sentence-transformers google-genai python-dotenv
```

Create a `.env` file:
GEMINI_API_KEY=your_key_here

Run:
```bash
python rag_pipeline.py
```

## Files
- `rag_pipeline.py` — core RAG pipeline
- `search.py` — similarity search logic
- `database_test.py` — ChromaDB tests
- `llm_test.py` — Gemini API tests
