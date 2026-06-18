import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { User, Bot, Copy, Check } from 'lucide-react';
import { useState } from 'react';
import SourceCitation from './SourceCitation';

function CodeBlock({ className, children }) {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || '');
  const code = String(children).replace(/\n$/, '');

  function handleCopy() {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (!match) {
    return (
      <code className="px-1.5 py-0.5 bg-zinc-800 text-violet-300 text-xs rounded">
        {children}
      </code>
    );
  }

  return (
    <div className="relative group my-3">
      <div className="flex items-center justify-between px-4 py-1.5 bg-zinc-800 rounded-t-lg border border-zinc-700 border-b-0">
        <span className="text-xs text-zinc-500">{match[1]}</span>
        <button
          onClick={handleCopy}
          className="text-zinc-500 hover:text-zinc-300 transition-colors cursor-pointer"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
      </div>
      <SyntaxHighlighter
        style={oneDark}
        language={match[1]}
        customStyle={{
          margin: 0,
          borderTopLeftRadius: 0,
          borderTopRightRadius: 0,
          borderBottomLeftRadius: '0.5rem',
          borderBottomRightRadius: '0.5rem',
          fontSize: '13px',
          border: '1px solid rgb(63 63 70)',
          borderTop: 'none',
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-lg bg-violet-500/10 flex items-center justify-center shrink-0 mt-1">
          <Bot size={14} className="text-violet-400" />
        </div>
      )}

      <div className={`max-w-[85%] ${isUser ? 'order-first' : ''}`}>
        {isUser ? (
          <div className="bg-zinc-800 rounded-2xl rounded-tr-sm px-4 py-2.5">
            <p className="text-sm text-zinc-200">{message.content}</p>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="prose prose-invert prose-sm max-w-none text-zinc-300 [&>p]:leading-relaxed">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ className, children, ...props }) {
                    const isBlock = /language-/.test(className || '');
                    if (isBlock) return <CodeBlock className={className}>{children}</CodeBlock>;
                    return (
                      <code className="px-1.5 py-0.5 bg-zinc-800 text-violet-300 text-xs rounded" {...props}>
                        {children}
                      </code>
                    );
                  },
                  pre({ children }) {
                    return <>{children}</>;
                  },
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
            {message.sources && <SourceCitation sources={message.sources} />}
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-7 h-7 rounded-lg bg-zinc-800 flex items-center justify-center shrink-0 mt-1">
          <User size={14} className="text-zinc-400" />
        </div>
      )}
    </div>
  );
}
