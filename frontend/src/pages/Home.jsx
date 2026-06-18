import { useState, useEffect, useCallback } from 'react';
import Sidebar from '../components/Sidebar';
import ChatPanel from '../components/ChatPanel';
import FileTree from '../components/FileTree';
import RepoInput from '../components/RepoInput';
import { useChat } from '../hooks/useChat';
import { apiGet, apiDelete } from '../lib/api';

export default function Home() {
  const [repos, setRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [repoDetail, setRepoDetail] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [showRepoInput, setShowRepoInput] = useState(false);

  const { messages, isStreaming, sendMessage, stopStreaming, clearMessages, loadMessages } = useChat();

  const fetchRepos = useCallback(async () => {
    try {
      const data = await apiGet('/repos/');
      setRepos(data);
    } catch {
      // user may not be authenticated yet
    }
  }, []);

  useEffect(() => {
    fetchRepos();
  }, [fetchRepos]);

  useEffect(() => {
    if (!selectedRepo) {
      setConversations([]);
      setRepoDetail(null);
      return;
    }

    apiGet(`/repos/${selectedRepo.id}`).then(setRepoDetail).catch(() => {});
    apiGet(`/chat/conversations/${selectedRepo.id}`).then(setConversations).catch(() => {});
  }, [selectedRepo]);

  function handleSelectRepo(repo) {
    setSelectedRepo(repo);
    setSelectedConversation(null);
    clearMessages();
  }

  async function handleSelectConversation(conv) {
    setSelectedConversation(conv);
    try {
      const msgs = await apiGet(`/chat/messages/${conv.id}`);
      loadMessages(msgs, conv.id);
    } catch {
      // ignore
    }
  }

  function handleNewConversation() {
    setSelectedConversation(null);
    clearMessages();
  }

  async function handleDeleteRepo(repoId) {
    try {
      await apiDelete(`/repos/${repoId}`);
      setRepos((prev) => prev.filter((r) => r.id !== repoId));
      if (selectedRepo?.id === repoId) {
        setSelectedRepo(null);
        setRepoDetail(null);
        clearMessages();
      }
    } catch {
      // ignore
    }
  }

  function handleRepoIndexed(repo) {
    setRepos((prev) => [repo, ...prev]);
    setSelectedRepo(repo);
    setShowRepoInput(false);
    clearMessages();
  }

  function handleSend(question) {
    if (!selectedRepo) return;
    sendMessage(selectedRepo.id, question);
  }

  const repoName = selectedRepo ? `${selectedRepo.owner}/${selectedRepo.name}` : null;

  return (
    <div className="flex h-screen bg-zinc-950">
      <Sidebar
        repos={repos}
        selectedRepo={selectedRepo}
        onSelectRepo={handleSelectRepo}
        conversations={conversations}
        selectedConversation={selectedConversation}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteRepo={handleDeleteRepo}
        onAddRepo={() => setShowRepoInput(true)}
      />

      <main className="flex-1 flex flex-col min-h-0">
        <ChatPanel
          messages={messages}
          isStreaming={isStreaming}
          onSend={handleSend}
          onStop={stopStreaming}
          repoName={repoName}
        />

        {repoDetail?.file_tree && (
          <div className="border-t border-zinc-800">
            <FileTree treeString={repoDetail.file_tree} />
          </div>
        )}
      </main>

      {showRepoInput && (
        <RepoInput
          onIndexed={handleRepoIndexed}
          onClose={() => setShowRepoInput(false)}
        />
      )}
    </div>
  );
}
