import { useState, useRef, useEffect } from 'react';
import { Send, Square, MessageSquare } from 'lucide-react';
import MessageBubble from './MessageBubble';

export default function ChatPanel({ messages, isStreaming, onSend, onStop, repoName }) {
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [repoName]);

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setInput('');
  }

  if (!repoName) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <MessageSquare size={48} className="mx-auto text-zinc-700 mb-4" />
          <h2 className="text-lg font-medium text-zinc-400">No repo selected</h2>
          <p className="text-sm text-zinc-600 mt-1">Index a repository to start chatting</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="px-6 py-3 border-b border-zinc-800">
        <h2 className="text-sm font-medium text-zinc-200">{repoName}</h2>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <h3 className="text-base font-medium text-zinc-400 mb-2">
                Ask anything about this codebase
              </h3>
              <div className="space-y-2">
                {[
                  'How does the authentication work?',
                  'What are the main API endpoints?',
                  'Explain the database schema',
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => {
                      setInput(q);
                      inputRef.current?.focus();
                    }}
                    className="block w-full text-left px-4 py-2.5 text-sm text-zinc-500 bg-zinc-900/50 hover:bg-zinc-800 border border-zinc-800 rounded-lg transition-colors cursor-pointer"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="px-6 py-4 border-t border-zinc-800">
        <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded-xl px-4 py-2 focus-within:border-violet-500/50 transition-colors">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about the codebase..."
            className="flex-1 bg-transparent text-sm text-zinc-200 placeholder:text-zinc-600 outline-none"
            disabled={isStreaming}
          />
          {isStreaming ? (
            <button
              type="button"
              onClick={onStop}
              className="p-1.5 text-red-400 hover:text-red-300 transition-colors cursor-pointer"
              title="Stop generating"
            >
              <Square size={16} />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="p-1.5 text-violet-400 hover:text-violet-300 disabled:text-zinc-700 transition-colors cursor-pointer disabled:cursor-not-allowed"
            >
              <Send size={16} />
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
