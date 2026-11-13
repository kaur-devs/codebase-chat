import { Eye, Link2 } from 'lucide-react';

export default function ShareBadge({ views, revoked }) {
  if (revoked) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs text-zinc-600 bg-zinc-900 border border-zinc-800 rounded-full">
        Revoked
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 text-xs text-violet-300 bg-violet-500/10 border border-violet-500/20 rounded-full">
      <Link2 size={10} />
      Shared
      <span className="inline-flex items-center gap-0.5 text-zinc-500">
        <Eye size={10} />
        {views ?? 0}
      </span>
    </span>
  );
}
