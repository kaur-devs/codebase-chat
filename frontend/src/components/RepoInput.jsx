import { useState } from 'react';
import { Link, Loader2, AlertCircle } from 'lucide-react';
import { apiPost } from '../lib/api';

export default function RepoInput({ onIndexed, onClose }) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');

    const trimmed = url.trim();
    if (!trimmed) return;

    const githubPattern = /^https:\/\/github\.com\/[a-zA-Z0-9\-_.]+\/[a-zA-Z0-9\-_.]+\/?$/;
    if (!githubPattern.test(trimmed)) {
      setError('Enter a valid GitHub URL (https://github.com/owner/repo)');
      return;
    }

    setLoading(true);
    try {
      const repo = await apiPost('/repos/index', { url: trimmed });
      onIndexed(repo);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-md mx-4 p-6">
        <h3 className="text-base font-medium text-zinc-200 mb-1">Index a repository</h3>
        <p className="text-xs text-zinc-500 mb-4">
          Paste a GitHub repo URL. We'll clone it, parse the code, and make it searchable.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="flex items-center gap-2 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 focus-within:border-violet-500/50 transition-colors">
            <Link size={14} className="text-zinc-600 shrink-0" />
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://github.com/owner/repo"
              className="flex-1 bg-transparent text-sm text-zinc-200 placeholder:text-zinc-600 outline-none"
              disabled={loading}
              autoFocus
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 mt-3 text-xs text-red-400">
              <AlertCircle size={14} />
              {error}
            </div>
          )}

          {loading && (
            <div className="flex items-center gap-2 mt-3 text-xs text-violet-400">
              <Loader2 size={14} className="animate-spin" />
              Cloning and indexing... this may take a minute for large repos.
            </div>
          )}

          <div className="flex gap-2 mt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="flex-1 px-4 py-2 text-sm text-zinc-400 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors cursor-pointer disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !url.trim()}
              className="flex-1 px-4 py-2 text-sm text-white bg-violet-600 hover:bg-violet-500 disabled:bg-zinc-800 disabled:text-zinc-600 rounded-lg transition-colors cursor-pointer"
            >
              {loading ? 'Indexing...' : 'Index repo'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
