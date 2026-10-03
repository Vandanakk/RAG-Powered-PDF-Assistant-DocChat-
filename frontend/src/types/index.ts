export interface SourceChunk {
  page: number;
  text: string;
  chunk_index?: number;
}

export interface DocumentInfo {
  document_id: string;
  filename: string;
  number_of_pages: number;
  number_of_chunks: number;
  uploaded_at: string;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  number_of_pages: number;
  number_of_chunks: number;
  message: string;
}

export interface ChatHistoryItem {
  role: 'user' | 'assistant';
  text: string;
}

export interface ChatRequest {
  document_id: string;
  question: string;
  history?: ChatHistoryItem[];
}

export interface ChatResponse {
  answer: string;
  sources: SourceChunk[];
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  sources?: SourceChunk[];
  isError?: boolean;
}

export interface HealthResponse {
  status: string;
}

export interface DocumentDeleteResponse {
  success: boolean;
  message: string;
  document_id: string;
}
