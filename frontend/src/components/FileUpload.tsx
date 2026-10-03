import React, { useState, useRef } from 'react';
import { Loader2, CheckCircle2, AlertCircle, FileUp } from 'lucide-react';
import { uploadDocument } from '../services/api';
import type { DocumentUploadResponse } from '../types';

interface FileUploadProps {
  onUploadSuccess: (doc: DocumentUploadResponse) => void;
  isProcessing?: boolean;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onUploadSuccess,
  isProcessing = false,
}) => {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Reset input so same file can be selected again if needed
    event.target.value = '';

    if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
      setStatusMessage({
        type: 'error',
        text: 'Only PDF files (.pdf) are supported.',
      });
      return;
    }

    if (file.size === 0) {
      setStatusMessage({
        type: 'error',
        text: 'Selected file is empty.',
      });
      return;
    }

    try {
      setUploading(true);
      setProgress(0);
      setStatusMessage(null);

      const response = await uploadDocument(file, (progressEvent) => {
        if (progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setProgress(percent);
        }
      });

      setStatusMessage({
        type: 'success',
        text: `"${response.filename}" successfully uploaded and indexed!`,
      });

      onUploadSuccess(response);

      // Auto dismiss success toast after 4s
      setTimeout(() => {
        setStatusMessage((current) => (current?.type === 'success' ? null : current));
      }, 4000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed.';
      setStatusMessage({
        type: 'error',
        text: message,
      });
    } finally {
      setUploading(false);
      setProgress(null);
    }
  };

  const triggerFileInput = () => {
    if (!uploading && !isProcessing) {
      fileInputRef.current?.click();
    }
  };

  const isDisabled = uploading || isProcessing;

  return (
    <div className="w-full space-y-2.5">
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={handleFileChange}
        disabled={isDisabled}
      />

      <button
        type="button"
        onClick={triggerFileInput}
        disabled={isDisabled}
        className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-medium text-sm transition-all shadow-sm ${
          isDisabled
            ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700/50'
            : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-cyan-500/20 hover:shadow-cyan-500/30 cursor-pointer active:scale-[0.98]'
        }`}
      >
        {uploading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin text-cyan-200" />
            <span>Processing PDF...</span>
          </>
        ) : (
          <>
            <FileUp className="w-4 h-4" />
            <span>Upload PDF</span>
          </>
        )}
      </button>

      {/* Upload progress bar */}
      {uploading && progress !== null && (
        <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div
            className="bg-cyan-400 h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${Math.max(progress, 15)}%` }}
          />
        </div>
      )}

      {/* Status banner */}
      {statusMessage && (
        <div
          className={`flex items-start gap-2 p-2.5 rounded-lg text-xs leading-snug animate-fadeIn ${
            statusMessage.type === 'success'
              ? 'bg-emerald-950/70 border border-emerald-800/80 text-emerald-200'
              : 'bg-rose-950/70 border border-rose-800/80 text-rose-200'
          }`}
        >
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          )}
          <span className="flex-1 break-words">{statusMessage.text}</span>
        </div>
      )}
    </div>
  );
};
