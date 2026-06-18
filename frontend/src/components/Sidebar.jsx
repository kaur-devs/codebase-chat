import { useState } from 'react';
import { Plus, MessageSquare, Trash2, GitBranch, ChevronDown, ChevronRight, LogOut } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export default function Sidebar({
  repos,
  selectedRepo,
  onSelectRepo,
  conversations,
  selectedConversation,
  onSelectConversation,
  onNewConversation,
  onDeleteRepo,
  onAddRepo,
}) {
  const { user, logout } = useAuth();
  const [expandedRepo, setExpandedRepo] = useState(null);

  return (
    <aside className="w-72 h-screen flex flex-col bg-zinc-950 border-r border-zinc-800">
      <div className="p-4 border-b border-zinc-800">
        <h1 className="text-sm font-semibold text-zinc-100 tracking-tight">Codebase Chat</h1>
        <p className="text-xs text-zinc-500 mt-0.5">Ask questions about any repo</p>
      </div>

      <div className="p-3">
        <button
          onClick={onAddRepo}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-zinc-300 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-lg transition-colors cursor-pointer"
        >
          <Plus size={14} />
          Index new repo
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2">
        <p className="px-2 py-1.5 text-xs font-medium text-zinc-500 uppercase tracking-wider">
          Repositories
        </p>

        {repos.length === 0 && (
          <p className="px-3 py-4 text-xs text-zinc-600 text-center">
            No repos indexed yet
          </p>
        )}

        {repos.map((repo) => (
          <div key={repo.id} className="mb-1">
            <button
              onClick={() => {
                onSelectRepo(repo);
                setExpandedRepo(expandedRepo === repo.id ? null : repo.id);
              }}
              className={`w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors cursor-pointer ${
                selectedRepo?.id === repo.id
                  ? 'bg-zinc-800 text-zinc-100'
                  : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-300'
              }`}
            >
              <GitBranch size={14} className="shrink-0 text-violet-400" />
              <span className="truncate flex-1 text-left">
                {repo.owner}/{repo.name}
              </span>
              {selectedRepo?.id === repo.id ? (
                <ChevronDown size={14} className="shrink-0 text-zinc-500" />
              ) : (
                <ChevronRight size={14} className="shrink-0 text-zinc-600" />
              )}
            </button>

            {expandedRepo === repo.id && (
              <div className="ml-5 mt-1 space-y-0.5">
                <button
                  onClick={onNewConversation}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900 rounded-md transition-colors cursor-pointer"
                >
                  <Plus size={12} />
                  New chat
                </button>

                {conversations.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => onSelectConversation(conv)}
                    className={`w-full flex items-center gap-2 px-3 py-1.5 text-xs rounded-md transition-colors cursor-pointer ${
                      selectedConversation?.id === conv.id
                        ? 'bg-zinc-800 text-zinc-200'
                        : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900'
                    }`}
                  >
                    <MessageSquare size={12} className="shrink-0" />
                    <span className="truncate text-left">{conv.title}</span>
                  </button>
                ))}

                <button
                  onClick={() => onDeleteRepo(repo.id)}
                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-red-500/70 hover:text-red-400 hover:bg-zinc-900 rounded-md transition-colors cursor-pointer"
                >
                  <Trash2 size={12} />
                  Remove repo
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {user && (
        <div className="p-3 border-t border-zinc-800 flex items-center gap-3">
          <img
            src={user.avatar_url}
            alt=""
            className="w-7 h-7 rounded-full"
          />
          <span className="text-xs text-zinc-400 truncate flex-1">{user.username}</span>
          <button
            onClick={logout}
            className="text-zinc-600 hover:text-zinc-400 transition-colors cursor-pointer"
            title="Sign out"
          >
            <LogOut size={14} />
          </button>
        </div>
      )}
    </aside>
  );
}
