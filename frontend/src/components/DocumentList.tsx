import React from 'react';
import type { DocumentInfo } from '../types';
import { FileText, Trash2, Loader2, CheckCircle2 } from 'lucide-react';

interface DocumentListProps {
  documents: DocumentInfo[];
  selectedDocumentId: string | null;
  onSelectDocument: (doc: DocumentInfo) => void;
  onDeleteDocument: (documentId: string) => void;
  deletingDocId?: string | null;
  isLoading?: boolean;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  selectedDocumentId,
  onSelectDocument,
  onDeleteDocument,
  deletingDocId = null,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="space-y-2 py-4">
        {[1, 2, 3].map((n) => (
          <div
            key={n}
            className="animate-pulse bg-slate-800/60 rounded-xl h-16 w-full border border-slate-700/40"
          />
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="text-center py-8 px-4 rounded-xl border border-dashed border-slate-800 text-slate-500 text-xs">
        <FileText className="w-8 h-8 mx-auto mb-2 text-slate-600 opacity-60" />
        <p className="font-medium text-slate-400">No documents yet</p>
        <p className="mt-1">Upload a PDF above to begin asking questions.</p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5 overflow-y-auto max-h-[calc(100vh-280px)] pr-1">
      {documents.map((doc) => {
        const isSelected = doc.document_id === selectedDocumentId;
        const isDeleting = deletingDocId === doc.document_id;

        return (
          <div
            key={doc.document_id}
            onClick={() => {
              if (!isDeleting) {
                onSelectDocument(doc);
              }
            }}
            className={`group relative w-full text-left p-3 rounded-xl transition-all duration-200 border cursor-pointer select-none ${
              isSelected
                ? 'bg-cyan-950/60 border-cyan-500/80 shadow-lg shadow-cyan-950/40 text-white ring-1 ring-cyan-500/40'
                : 'bg-slate-800/40 hover:bg-slate-800/80 border-slate-700/40 text-slate-300 hover:text-white'
            }`}
          >
            <div className="flex items-start gap-2.5">
              <div
                className={`p-2 rounded-lg shrink-0 transition-colors ${
                  isSelected
                    ? 'bg-cyan-500 text-slate-950'
                    : 'bg-slate-700/50 group-hover:bg-slate-700 text-cyan-400'
                }`}
              >
                <FileText className="w-4 h-4" />
              </div>

              <div className="flex-1 min-w-0 pr-8">
                <p className="text-xs font-semibold truncate leading-tight mb-1">
                  {doc.filename}
                </p>

                <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
                  <span>{doc.number_of_pages} {doc.number_of_pages === 1 ? 'page' : 'pages'}</span>
                  <span>•</span>
                  <span>{doc.number_of_chunks} chunks</span>
                </div>

                {isSelected && (
                  <div className="mt-1.5 flex items-center gap-1 text-[10px] text-cyan-400 font-medium">
                    <CheckCircle2 className="w-3 h-3 text-cyan-400 shrink-0" />
                    <span>Active document</span>
                  </div>
                )}
              </div>

              {/* Delete Button */}
              <button
                type="button"
                title={`Delete ${doc.filename}`}
                disabled={isDeleting}
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteDocument(doc.document_id);
                }}
                className={`absolute top-2.5 right-2.5 p-1.5 rounded-lg transition-colors cursor-pointer ${
                  isDeleting
                    ? 'text-amber-400 bg-amber-950/40 cursor-not-allowed'
                    : 'text-slate-400 hover:text-rose-300 hover:bg-rose-950/60 opacity-70 group-hover:opacity-100'
                }`}
              >
                {isDeleting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};

