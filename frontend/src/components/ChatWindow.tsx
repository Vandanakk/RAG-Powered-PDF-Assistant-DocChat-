import React, { useEffect, useRef } from 'react';
import type { ChatMessage, DocumentInfo } from '../types';
import { SourceCard } from './SourceCard';
import { ChatInput } from './ChatInput';
import {
  Bot,
  User,
  FileText,
  Sparkles,
  Layers,
  AlertCircle,
} from 'lucide-react';

interface ChatWindowProps {
  selectedDocument: DocumentInfo | null;
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (question: string) => void;
  error?: string | null;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  selectedDocument,
  messages,
  isLoading,
  onSendMessage,
  error,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-900 overflow-hidden relative">
      {/* Top Header */}
      <header className="h-16 border-b border-slate-800 bg-slate-900/90 backdrop-blur px-6 flex items-center justify-between shrink-0 z-10">
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <FileText className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-slate-100 truncate">
              {selectedDocument ? selectedDocument.filename : 'No Document Selected'}
            </h2>
            <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
              {selectedDocument ? (
                <>
                  <span className="flex items-center gap-1">
                    {selectedDocument.number_of_pages} {selectedDocument.number_of_pages === 1 ? 'page' : 'pages'}
                  </span>
                  <span>•</span>
                  <span>{selectedDocument.number_of_chunks} indexed chunks</span>
                </>
              ) : (
                <span>Please select or upload a document</span>
              )}
            </div>
          </div>
        </div>

        {selectedDocument && (
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            RAG Grounded Active
          </div>
        )}
      </header>

      {/* Chat Messages Conversation Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {/* Global error banner if present */}
        {error && (
          <div className="flex items-center gap-2.5 p-3 rounded-xl bg-rose-950/70 border border-rose-800/80 text-rose-200 text-xs shadow-lg animate-fadeIn">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Empty State 1: No PDF Selected */}
        {!selectedDocument && (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 max-w-md mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mb-4 shadow-xl">
              <FileText className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-semibold text-slate-200 mb-1">
              Upload a PDF to start asking questions.
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Upload any PDF document from the sidebar to extract text, generate vector embeddings, and ask grounded questions.
            </p>
          </div>
        )}

        {/* Empty State 2: PDF Selected but no messages */}
        {selectedDocument && messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 max-w-lg mx-auto">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-4 shadow-xl">
              <Sparkles className="w-7 h-7" />
            </div>
            <h3 className="text-base font-semibold text-slate-200 mb-1">
              Ask anything about this document.
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed mb-6">
              DocChat retrieves relevant sections from <span className="text-cyan-300 font-medium">"{selectedDocument.filename}"</span> using ChromaDB and answers using strictly verified context.
            </p>

            <div className="w-full grid grid-cols-1 gap-2 text-left">
              {[
                "What is the main topic of this document?",
                "Can you summarize the key findings?",
                "What are the conclusions or recommendations?",
              ].map((suggestion, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => onSendMessage(suggestion)}
                  disabled={isLoading}
                  className="p-2.5 rounded-xl bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 text-xs text-slate-300 hover:text-cyan-300 transition-all text-left flex items-center justify-between cursor-pointer"
                >
                  <span>"{suggestion}"</span>
                  <span className="text-slate-500 text-[10px]">Ask →</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Chat Messages */}
        {messages.map((message) => {
          const isUser = message.sender === 'user';

          return (
            <div
              key={message.id}
              className={`flex gap-3 max-w-3xl ${isUser ? 'ml-auto justify-end' : 'mr-auto justify-start'}`}
            >
              {/* Bot Avatar */}
              {!isUser && (
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center text-white shrink-0 shadow-md">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              {/* Message Bubble Container */}
              <div className={`space-y-3 ${isUser ? 'items-end' : 'items-start'}`}>
                <div
                  className={`p-4 rounded-2xl text-sm leading-relaxed ${
                    isUser
                      ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-tr-none shadow-lg shadow-cyan-950/40'
                      : message.isError
                      ? 'bg-rose-950/70 border border-rose-800/80 text-rose-200 rounded-tl-none shadow-md'
                      : 'bg-slate-800/90 border border-slate-700/60 text-slate-200 rounded-tl-none shadow-md backdrop-blur'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.text}</p>
                </div>

                {/* Sources Section below Assistant Answer */}
                {!isUser && message.sources && message.sources.length > 0 && (
                  <div className="mt-2 space-y-2 bg-slate-950/40 border border-slate-800/80 rounded-xl p-3">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-cyan-400">
                      <Layers className="w-3.5 h-3.5" />
                      <span>Sources ({message.sources.length})</span>
                    </div>

                    <div className="grid grid-cols-1 gap-2 pt-1">
                      {message.sources.map((source, idx) => (
                        <SourceCard key={idx} source={source} index={idx} />
                      ))}
                    </div>
                  </div>
                )}

                <div className={`text-[10px] text-slate-500 font-mono ${isUser ? 'text-right' : 'text-left'}`}>
                  {message.timestamp}
                </div>
              </div>

              {/* User Avatar */}
              {isUser && (
                <div className="w-8 h-8 rounded-xl bg-slate-700 flex items-center justify-center text-slate-200 shrink-0 shadow-md">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          );
        })}

        {/* Loading Indicator while processing RAG request */}
        {isLoading && (
          <div className="flex gap-3 mr-auto max-w-xl animate-fadeIn">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center text-white shrink-0 shadow-md">
              <Bot className="w-4 h-4 animate-pulse" />
            </div>

            <div className="bg-slate-800/90 border border-slate-700/60 rounded-2xl rounded-tl-none p-4 shadow-md space-y-2">
              <div className="flex items-center gap-2 text-xs text-cyan-300 font-medium">
                <Sparkles className="w-3.5 h-3.5 animate-spin" />
                <span>Searching ChromaDB & generating answer...</span>
              </div>
              <div className="flex gap-1.5 items-center pt-1">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Bottom Chat Input Bar */}
      <div className="p-4 md:px-6 bg-slate-900/95 border-t border-slate-800 shrink-0">
        <div className="max-w-3xl mx-auto">
          <ChatInput
            onSendMessage={onSendMessage}
            isLoading={isLoading}
            disabled={!selectedDocument}
            placeholder={
              selectedDocument
                ? `Ask anything about "${selectedDocument.filename}"...`
                : "Select or upload a PDF to start asking questions"
            }
          />
        </div>
      </div>
    </div>
  );
};
