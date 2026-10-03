from typing import List, Optional
from pydantic import BaseModel, Field

class SourceChunk(BaseModel):
    page: int = Field(..., description="1-indexed page number where the chunk was found")
    text: str = Field(..., description="Text content of the retrieved chunk")
    chunk_index: Optional[int] = Field(None, description="Index of the chunk in the document")

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    number_of_pages: int
    number_of_chunks: int
    message: str

class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    number_of_pages: int
    number_of_chunks: int
    uploaded_at: str

class ChatMessageItem(BaseModel):
    role: str = Field(..., description="Role of the sender ('user' or 'assistant')")
    text: str = Field(..., description="Message text content")

class ChatRequest(BaseModel):
    document_id: str = Field(..., min_length=1, description="Unique identifier of the target document")
    question: str = Field(..., min_length=1, description="Question to answer using the document context")
    history: Optional[List[ChatMessageItem]] = Field(default=None, description="Recent conversation turns for follow-up resolution")

class ChatResponse(BaseModel):

    answer: str
    sources: List[SourceChunk]

class HealthResponse(BaseModel):
    status: str = "ok"

class DocumentDeleteResponse(BaseModel):
    success: bool = True
    message: str
    document_id: str

