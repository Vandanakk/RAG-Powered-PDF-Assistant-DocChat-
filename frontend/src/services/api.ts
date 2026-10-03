import axios from 'axios';
import type { AxiosError } from 'axios';
import type {
  DocumentInfo,
  DocumentUploadResponse,
  ChatResponse,
  HealthResponse,
  DocumentDeleteResponse,
  ChatHistoryItem,
} from '../types';

const resolveApiBaseUrl = (): string => {
  let url = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').trim();
  url = url.replace(/\/+$/, '');
  if (!url.endsWith('/api')) {
    url = `${url}/api`;
  }
  return url;
};

const API_BASE_URL = resolveApiBaseUrl();

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60s for embedding & LLM generation
});

export const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string }>;
    if (axiosError.response?.data?.detail) {
      return axiosError.response.data.detail;
    }
    if (axiosError.message) {
      if (axiosError.code === 'ECONNABORTED') {
        return 'Request timed out. Please try again.';
      }
      if (axiosError.message.includes('Network Error')) {
        return 'Unable to connect to the backend server. If using a free cloud tier (e.g. Render), it may take 30–60 seconds to wake up from sleep.';
      }
      return axiosError.message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred.';
};

export const uploadDocument = async (
  file: File,
  onUploadProgress?: (progressEvent: { loaded: number; total?: number }) => void
): Promise<DocumentUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await apiClient.post<DocumentUploadResponse>(
      '/documents/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress,
      }
    );
    return response.data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
};

export const getDocuments = async (): Promise<DocumentInfo[]> => {
  try {
    const response = await apiClient.get<DocumentInfo[]>('/documents');
    return response.data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
};

export const deleteDocument = async (documentId: string): Promise<DocumentDeleteResponse> => {
  try {
    const response = await apiClient.delete<DocumentDeleteResponse>(`/documents/${documentId}`);
    return response.data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
};

export const askQuestion = async (
  documentId: string,
  question: string,
  history?: ChatHistoryItem[]
): Promise<ChatResponse> => {
  try {
    const response = await apiClient.post<ChatResponse>('/chat', {
      document_id: documentId,
      question: question.trim(),
      history: history && history.length > 0 ? history : undefined,
    });
    return response.data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
};

export const checkHealth = async (): Promise<HealthResponse> => {
  try {
    const response = await apiClient.get<HealthResponse>('/health');
    return response.data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
};

