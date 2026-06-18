import { useState, useCallback, useRef } from 'react';
import { streamChat } from '../lib/api';

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const cancelRef = useRef(null);

  const sendMessage = useCallback(
    (repoId, question) => {
      const userMsg = { role: 'user', content: question };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);

      const assistantMsg = { role: 'assistant', content: '', sources: null };
      setMessages((prev) => [...prev, assistantMsg]);

      const cancel = streamChat(
        { repo_id: repoId, question, conversation_id: conversationId },
        (token) => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            updated[updated.length - 1] = { ...last, content: last.content + token };
            return updated;
          });
        },
        (sources, convId) => {
          setConversationId(convId);
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            updated[updated.length - 1] = { ...last, sources };
            return updated;
          });
        },
        () => setIsStreaming(false),
        (err) => {
          setIsStreaming(false);
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            updated[updated.length - 1] = {
              ...last,
              content: `Error: ${err.message}`,
            };
            return updated;
          });
        }
      );

      cancelRef.current = cancel;
    },
    [conversationId]
  );

  const stopStreaming = useCallback(() => {
    if (cancelRef.current) cancelRef.current();
    setIsStreaming(false);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setConversationId(null);
  }, []);

  const loadMessages = useCallback((msgs, convId) => {
    setMessages(msgs);
    setConversationId(convId);
  }, []);

  return { messages, isStreaming, conversationId, sendMessage, stopStreaming, clearMessages, loadMessages };
}
