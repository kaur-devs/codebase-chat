import { useState, useCallback } from 'react';
import { createShare, revokeShare } from '../lib/api';

export function useShare(conversationId) {
  const [link, setLink] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const share = useCallback(
    async (ttlDays = 30) => {
      setLoading(true);
      setError(null);

      const result = await createShare(conversationId, ttlDays);
      setLink(result);
      setLoading(false);
      return result;
    },
    []
  );

  const revoke = useCallback(async () => {
    if (!link) return;
    setLoading(true);
    try {
      await revokeShare(link.token);
      setLink(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [link]);

  return { link, loading, error, share, revoke };
}
