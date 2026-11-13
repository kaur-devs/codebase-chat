import { useState } from 'react';
import { Link2, Copy, Check, X, Trash2 } from 'lucide-react';
import { useShare } from '../hooks/useShare';

export default function ShareDialog({ conversation, onClose }) {
  const { link, loading, error, share, revoke } = useShare(conversation.id);
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(link.url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="w-full max-w-md bg-zinc-950 border border-zinc-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
            <Link2 size={14} className="text-violet-400" />
            Share this conversation
          </h2>
          <button
            onClick={onClose}
            className="text-zinc-600 hover:text-zinc-400 cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        <p
          className="text-xs text-zinc-500 mb-4"
          dangerouslySetInnerHTML={{ __html: conversation.title }}
        />

        {!link && (
          <button
            onClick={() => share(30)}
            disabled={loading}
            className="w-full px-3 py-2 text-sm text-zinc-100 bg-violet-600 hover:bg-violet-500 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
          >
            {loading ? 'Creating link…' : 'Create public link'}
          </button>
        )}

        {link && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg">
              <span className="text-xs text-zinc-300 truncate flex-1">{link.url}</span>
              <button onClick={copy} className="text-zinc-500 hover:text-zinc-300 cursor-pointer">
                {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
              </button>
            </div>

            <p className="text-xs text-zinc-600">
              Anyone with this link can read the conversation. Expires{' '}
              {new Date(link.expires).toLocaleDateString()}.
            </p>

            <button
              onClick={revoke}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs text-red-400 hover:bg-zinc-900 border border-zinc-800 rounded-lg cursor-pointer"
            >
              <Trash2 size={12} />
              Revoke link
            </button>
          </div>
        )}

        {error && <p className="mt-3 text-xs text-red-400">{error}</p>}
      </div>
    </div>
  );
}
