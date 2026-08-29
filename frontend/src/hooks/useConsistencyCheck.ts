import { useState, useCallback } from 'react';
import { useBookStore } from '@/store/useBookStore';

export interface Finding {
  category: string;
  severity: 'high' | 'medium' | 'low';
  description: string;
  evidence?: { source: string; text: string }[];
  suggestion?: string;
  is_intentional?: boolean;
}

interface ConsistencyCheckResult {
  findings: Finding[];
  total: number;
  summary: { high: number; medium: number; low: number };
}

export function useConsistencyCheck() {
  const { selectedBook } = useBookStore();
  const [findings, setFindings] = useState<Finding[]>([]);
  const [summary, setSummary] = useState({ high: 0, medium: 0, low: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runCheck = useCallback(async (epNum?: number) => {
    if (!selectedBook) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/consistency/${selectedBook.id}/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ep_num: epNum, branch_id: 1 }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setFindings(data.findings);
      setSummary(data.summary);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [selectedBook]);

  const dismiss = useCallback(async (findingKey: string, reason: string) => {
    if (!selectedBook) return;
    try {
      await fetch(`/api/consistency/${selectedBook.id}/dismiss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ finding_key: findingKey, reason }),
      });
      // Refetch
      await runCheck();
    } catch (e: any) {
      setError(e.message);
    }
  }, [selectedBook, runCheck]);

  return { findings, summary, loading, error, runCheck, dismiss };
}