import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { FileCode, Loader2 } from 'lucide-react';
import { fetchSharedConversation } from '../lib/api';

export default function SharedConversation() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchSharedConversation(token)
      .then(setData)
      .catch((err) => setError(err.message));
  });

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950">
        <p className="text-sm text-red-400">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950">
        <Loader2 size={18} className="text-zinc-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 py-10 px-4">
      <div className="max-w-3xl mx-auto">
        <header className="mb-8 pb-5 border-b border-zinc-800">
          <h1 className="text-lg font-semibold text-zinc-100">{data.title}</h1>
          <p className="mt-1 text-xs text-zinc-500 flex items-center gap-1.5">
            <FileCode size={12} className="text-violet-400" />
            {data.repository}
          </p>
          <p className="mt-3 text-xs text-zinc-600 leading-relaxed">{data.readme}</p>
        </header>

        <div className="space-y-6">
          {data.messages.map((message) => (
            <article>
              <p className="text-xs font-medium text-zinc-500 mb-1.5">
                {message.role === 'user' ? 'Question' : 'Answer'}
              </p>
              <div className="text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed">
                {message.content}
              </div>
            </article>
          ))}
        </div>

        <footer className="mt-10 pt-5 border-t border-zinc-800">
          <p className="text-xs text-zinc-600">
            Shared from Codebase Chat — a read-only snapshot of this conversation.
          </p>
        </footer>
      </div>
    </div>
  );
}
