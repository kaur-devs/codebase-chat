import { FileCode, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';

export default function SourceCitation({ sources }) {
  const [expanded, setExpanded] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors cursor-pointer"
      >
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <FileCode size={12} />
        {sources.length} source{sources.length !== 1 ? 's' : ''} referenced
      </button>

      {expanded && (
        <div className="mt-2 space-y-1">
          {sources.map((src, i) => (
            <div
              key={i}
              className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900 border border-zinc-800 rounded-md text-xs"
            >
              <FileCode size={12} className="text-violet-400 shrink-0" />
              <span className="text-zinc-300 truncate">{src.file_path}</span>
              {src.function_name && (
                <span className="text-violet-400">→ {src.function_name}()</span>
              )}
              <span className="text-zinc-600 ml-auto shrink-0">
                L{src.line_start}–{src.line_end}
              </span>
              {src.similarity != null && (
                <span className="text-zinc-600 shrink-0">
                  {Math.round(src.similarity * 100)}%
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
