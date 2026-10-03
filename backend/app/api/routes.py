from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.config import settings
from app.models import (
    DocumentUploadResponse,
    DocumentInfo,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    DocumentDeleteResponse,
)
from app.services.rag_service import get_rag_service, DocumentNotFoundError

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify backend service readiness."""
    return HealthResponse(status="ok")

@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and index a PDF document.
    - Validates file format and non-empty content
    - Extracts text page-by-page
    - Creates 500-char chunks with 100-char overlap
    - Generates embeddings with all-MiniLM-L6-v2
    - Stores into ChromaDB with document-scoped metadata
    """
    # 1. Validate filename and extension
    filename = file.filename or "uploaded.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF files (.pdf) are supported.",
        )

    # 2. Read content into memory and validate size
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {max_mb} MB.",
        )

    # 3. Process and index
    rag_service = get_rag_service()
    try:
        response = rag_service.process_and_index_document(
            file_bytes=content,
            filename=filename,
        )
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process and index document: {str(e)}",
        )

@router.post("/chat", response_model=ChatResponse)
async def chat_with_document(request: ChatRequest):
    """
    Ask a question grounded strictly in the selected document.
    - Retrieves top-k chunks from ChromaDB for the document
    - Passes chunks to Gemini with grounded prompt
    - Returns answer and cited sources
    """
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    rag_service = get_rag_service()
    try:
        return rag_service.answer_question(
            document_id=request.document_id,
            question=request.question,
            history=request.history,
        )
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        # Configuration error (e.g. missing API key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except RuntimeError as e:
        # LLM or embedding error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during chat processing: {str(e)}",
        )

@router.get("/documents", response_model=List[DocumentInfo])
async def get_documents():
    """Retrieve list of all uploaded and indexed documents."""
    rag_service = get_rag_service()
    try:
        return rag_service.list_documents()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documents: {str(e)}",
        )

@router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(document_id: str):
    """
    Delete a document and all its indexed chunks/embeddings.
    - Removes chunks from ChromaDB
    - Removes metadata from documents registry
    - Cleans up any stored document artifacts
    """
    rag_service = get_rag_service()
    try:
        rag_service.delete_document(document_id)
        return DocumentDeleteResponse(
            success=True,
            message=f"Document '{document_id}' successfully deleted.",
            document_id=document_id,
        )
    except DocumentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )

