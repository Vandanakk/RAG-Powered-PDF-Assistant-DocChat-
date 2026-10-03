import React, { useState, useEffect, useCallback } from 'react';
import type { DocumentInfo, DocumentUploadResponse, ChatMessage, ChatHistoryItem } from './types';
import { getDocuments, deleteDocument, askQuestion, checkHealth } from './services/api';
import { FileUpload } from './components/FileUpload';
import { DocumentList } from './components/DocumentList';
import { ChatWindow } from './components/ChatWindow';
import { MessageSquareText, Cpu } from 'lucide-react';

export const App: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<DocumentInfo | null>(null);
  const [messagesByDoc, setMessagesByDoc] = useState<Record<string, ChatMessage[]>>({});
  const [isLoadingDocs, setIsLoadingDocs] = useState<boolean>(true);
  const [isLoadingChat, setIsLoadingChat] = useState<boolean>(false);
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);
  const [appError, setAppError] = useState<string | null>(null);

  // Check backend health & fetch available documents on startup
  const fetchInitialData = useCallback(async () => {
    setIsLoadingDocs(true);
    setAppError(null);

    try {
      await checkHealth();
      setIsBackendHealthy(true);
    } catch {
      setIsBackendHealthy(false);
      setAppError('Backend API is currently unreachable. If hosted on a free cloud service, it may take 30–60 seconds to spin up.');
    }

    try {
      const docs = await getDocuments();
      setDocuments(docs);
      setSelectedDocument((prev) => {
        if (prev && docs.some((d) => d.document_id === prev.document_id)) {
          return prev;
        }
        return docs.length > 0 ? docs[0] : null;
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch document list.';
      // Don't overwrite backend offline message
      if (isBackendHealthy !== false) {
        setAppError(msg);
      }
    } finally {
      setIsLoadingDocs(false);
    }
  }, [isBackendHealthy]);

  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  // Handle successful document upload
  const handleUploadSuccess = (uploaded: DocumentUploadResponse) => {
    const newDoc: DocumentInfo = {
      document_id: uploaded.document_id,
      filename: uploaded.filename,
      number_of_pages: uploaded.number_of_pages,
      number_of_chunks: uploaded.number_of_chunks,
      uploaded_at: new Date().toISOString(),
    };

    setDocuments((prev) => [newDoc, ...prev.filter((d) => d.document_id !== newDoc.document_id)]);
    setSelectedDocument(newDoc);
    setAppError(null);
  };

  // Handle deleting a document
  const handleDeleteDocument = async (documentId: string) => {
    setDeletingDocId(documentId);
    setAppError(null);

    try {
      await deleteDocument(documentId);

      // Remove from document list
      const updatedDocs = documents.filter((d) => d.document_id !== documentId);
      setDocuments(updatedDocs);

      // Clear chat messages for deleted document
      setMessagesByDoc((prev) => {
        const next = { ...prev };
        delete next[documentId];
        return next;
      });

      // If deleted document was selected, select next available or null
      if (selectedDocument?.document_id === documentId) {
        setSelectedDocument(updatedDocs.length > 0 ? updatedDocs[0] : null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete document.';
      setAppError(msg);
    } finally {
      setDeletingDocId(null);
    }
  };

  // Handle sending a chat message
  const handleSendMessage = async (question: string) => {
    if (!selectedDocument) return;

    const docId = selectedDocument.document_id;
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const previousHistory: ChatHistoryItem[] = (messagesByDoc[docId] || [])
      .filter((m) => !m.isError && m.text.trim())
      .slice(-6)
      .map((m) => ({ role: m.sender, text: m.text }));

    const userMessage: ChatMessage = {
      id: `msg_user_${Date.now()}`,
      sender: 'user',
      text: question,
      timestamp: timeStr,
    };

    // Optimistically append user message
    setMessagesByDoc((prev) => ({
      ...prev,
      [docId]: [...(prev[docId] || []), userMessage],
    }));

    setIsLoadingChat(true);
    setAppError(null);

    try {
      const response = await askQuestion(docId, question, previousHistory);

      const assistantMessage: ChatMessage = {
        id: `msg_asst_${Date.now()}`,
        sender: 'assistant',
        text: response.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sources: response.sources,
      };

      setMessagesByDoc((prev) => ({
        ...prev,
        [docId]: [...(prev[docId] || []), assistantMessage],
      }));
    } catch (err: unknown) {
      const errorText = err instanceof Error ? err.message : 'Failed to get answer.';
      const errorMessage: ChatMessage = {
        id: `msg_err_${Date.now()}`,
        sender: 'assistant',
        text: `Error: ${errorText}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isError: true,
      };

      setMessagesByDoc((prev) => ({
        ...prev,
        [docId]: [...(prev[docId] || []), errorMessage],
      }));
    } finally {
      setIsLoadingChat(false);
    }
  };

  const currentMessages = selectedDocument ? messagesByDoc[selectedDocument.document_id] || [] : [];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 font-sans">
      {/* LEFT SIDEBAR */}
      <aside className="w-80 md:w-88 h-full bg-slate-900/95 border-r border-slate-800 flex flex-col shrink-0">
        {/* Brand / Logo */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-lg shadow-cyan-500/20">
              <MessageSquareText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h1 className="text-base font-bold tracking-tight text-white">DocChat</h1>
                <span className="text-[10px] uppercase font-mono tracking-wider px-1.5 py-0.5 rounded-md bg-cyan-950 text-cyan-400 border border-cyan-800">
                  RAG
                </span>
              </div>
              <p className="text-[11px] text-slate-400">PDF Question Answering</p>
            </div>
          </div>

          {/* Backend Status indicator */}
          <div
            title={
              isBackendHealthy === true
                ? 'Backend connected'
                : isBackendHealthy === false
                ? 'Backend offline'
                : 'Connecting...'
            }
            className="flex items-center gap-1.5 text-[11px] text-slate-400"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isBackendHealthy === true
                  ? 'bg-emerald-400 ring-2 ring-emerald-500/20'
                  : isBackendHealthy === false
                  ? 'bg-rose-500 ring-2 ring-rose-500/20'
                  : 'bg-amber-400 animate-ping'
              }`}
            />
          </div>
        </div>

        {/* Upload Action Section */}
        <div className="p-4 border-b border-slate-800/80 bg-slate-900/50">
          <FileUpload
            onUploadSuccess={handleUploadSuccess}
            isProcessing={isLoadingChat}
          />
        </div>

        {/* Uploaded Documents List */}
        <div className="flex-1 p-4 overflow-hidden flex flex-col">
          <div className="flex items-center justify-between mb-2 px-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono">
              Documents ({documents.length})
            </span>
          </div>

          <DocumentList
            documents={documents}
            selectedDocumentId={selectedDocument?.document_id || null}
            onSelectDocument={(doc) => {
              setSelectedDocument(doc);
              setAppError(null);
            }}
            onDeleteDocument={handleDeleteDocument}
            deletingDocId={deletingDocId}
            isLoading={isLoadingDocs}
          />
        </div>

        {/* Sidebar Footer info */}
        <div className="p-3 border-t border-slate-800 bg-slate-950/40 text-[11px] text-slate-500 flex items-center justify-between font-mono">
          <span className="flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-cyan-500" />
            all-MiniLM-L6-v2 + Gemini
          </span>
          <span>v1.0</span>
        </div>
      </aside>

      {/* MAIN AREA */}
      <main className="flex-1 h-full flex flex-col min-w-0 bg-slate-900">
        <ChatWindow
          selectedDocument={selectedDocument}
          messages={currentMessages}
          isLoading={isLoadingChat}
          onSendMessage={handleSendMessage}
          error={appError}
        />
      </main>
    </div>
  );
};

export default App;
