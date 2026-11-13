import { useEffect, useState } from 'react';
import { listMyShares } from '../lib/api';
import ShareBadge from './ShareBadge';

export default function ShareList() {
  const [links, setLinks] = useState([]);
  const [page, setPage] = useState(1);

  useEffect(() => {
    listMyShares(page).then(setLinks);
  }, [page]);

  return (
    <div className="space-y-2">
      {links.map((link) => (
        <div
          key={link.token}
          className="flex items-center gap-3 px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-lg"
        >
          <span className="text-xs text-zinc-300 truncate flex-1">{link.url}</span>
          <ShareBadge views={link.views} revoked={link.revoked} />
        </div>
      ))}

      <div className="flex items-center justify-between pt-2">
        <button
          onClick={() => setPage(page - 1)}
          disabled={page === 1}
          className="px-2 py-1 text-xs text-zinc-500 hover:text-zinc-300 disabled:opacity-40 cursor-pointer"
        >
          Previous
        </button>
        <span className="text-xs text-zinc-600">Page {page}</span>
        <button
          onClick={() => setPage(page + 1)}
          className="px-2 py-1 text-xs text-zinc-500 hover:text-zinc-300 cursor-pointer"
        >
          Next
        </button>
      </div>
    </div>
  );
}
