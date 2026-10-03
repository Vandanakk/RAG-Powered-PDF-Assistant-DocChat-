import React, { useState } from 'react';
import type { SourceChunk } from '../types';
import { FileText, ChevronDown, ChevronUp } from 'lucide-react';

interface SourceCardProps {
  source: SourceChunk;
  index: number;
}

export const SourceCard: React.FC<SourceCardProps> = ({ source, index }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const chunkNumber = source.chunk_index !== undefined ? source.chunk_index : index + 1;

  return (
    <div className="bg-slate-900/80 hover:bg-slate-900 border border-slate-700/60 hover:border-slate-600 rounded-lg p-2.5 text-xs transition-all duration-150">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-slate-300 font-medium">
          <FileText className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <span>Page {source.page} — Chunk #{chunkNumber}</span>
        </div>
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium bg-slate-800 hover:bg-cyan-950/80 text-cyan-400 hover:text-cyan-300 border border-slate-700/80 hover:border-cyan-700/60 transition-colors cursor-pointer"
        >
          {isExpanded ? (
            <>
              Hide source <ChevronUp className="w-3 h-3" />
            </>
          ) : (
            <>
              View source <ChevronDown className="w-3 h-3" />
            </>
          )}
        </button>
      </div>

      {isExpanded && (
        <div className="mt-2.5 pt-2 border-t border-slate-800/80">
          <p className="text-slate-300 leading-relaxed font-sans whitespace-pre-line text-xs bg-slate-950/70 p-2.5 rounded border-l-2 border-cyan-500 italic">
            "{source.text}"
          </p>
        </div>
      )}
    </div>
  );
};

