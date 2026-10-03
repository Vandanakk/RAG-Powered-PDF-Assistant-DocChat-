import React, { useState, useRef, useEffect } from 'react';
import { SendHorizontal, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (question: string) => void;
  isLoading: boolean;
  disabled: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isLoading,
  disabled,
  placeholder = "Ask anything about this document...",
}) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || disabled) return;
    onSendMessage(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  const isButtonDisabled = disabled || isLoading || !input.trim();

  return (
    <form onSubmit={handleSubmit} className="relative w-full">
      <div className="relative flex items-end gap-2 bg-slate-800/80 backdrop-blur border border-slate-700/70 rounded-2xl p-2 focus-within:border-cyan-500/80 focus-within:ring-2 focus-within:ring-cyan-500/20 transition-all shadow-lg">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={disabled || isLoading}
          placeholder={disabled ? "Select or upload a document first" : placeholder}
          rows={1}
          className="w-full bg-transparent text-slate-100 placeholder-slate-500 text-sm px-3 py-2 resize-none focus:outline-none max-h-32 disabled:cursor-not-allowed leading-relaxed"
        />

        <button
          type="submit"
          disabled={isButtonDisabled}
          className={`p-2.5 rounded-xl transition-all duration-200 shrink-0 cursor-pointer flex items-center justify-center ${
            isButtonDisabled
              ? 'bg-slate-700/40 text-slate-600 cursor-not-allowed'
              : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 active:scale-95 shadow-md shadow-cyan-500/25'
          }`}
          title="Send message (Enter)"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin text-cyan-900" />
          ) : (
            <SendHorizontal className="w-4 h-4" />
          )}
        </button>
      </div>
      <p className="text-[11px] text-slate-500 text-right mt-1.5 pr-2">
        Press <span className="font-mono text-slate-400">Enter</span> to send, <span className="font-mono text-slate-400">Shift + Enter</span> for new line
      </p>
    </form>
  );
};
