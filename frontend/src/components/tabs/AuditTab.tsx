import { useState, useEffect, useCallback } from 'react';
import type { Book, Issue } from '@/types';
import { getIssues, resolveIssue } from '@/api';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';

interface AuditTabProps {
  selectedBook: Book;
  apiKey?: string;
}

const severityConfig = {
  high: { label: 'High', color: 'text-accent-rose', border: 'border-accent-rose/30', bg: 'bg-accent-rose/10' },
  medium: { label: 'Medium', color: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/10' },
  low: { label: 'Low', color: 'text-accent-cyan', border: 'border-accent-cyan/30', bg: 'bg-accent-cyan/10' },
};

export function AuditTab({ selectedBook }: AuditTabProps) {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const loadIssues = useCallback(async () => {
    if (!selectedBook?.id) return;
    setLoading(true);
    try {
      const data = await getIssues(selectedBook.id);
      setIssues(data);
    } catch (err: unknown) {
      toast.error('issue読み込みに失敗: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
    }
  }, [selectedBook?.id]);

  useEffect(() => {
    loadIssues();
  }, [loadIssues]);

  const handleResolve = async (issueId: number, action: string = 'resolve') => {
    try {
      await resolveIssue(issueId, action);
      toast.success(`Issue #${issueId} を「${action}」で解決しました。`);
      loadIssues();
    } catch (err: unknown) {
      toast.error('issueの解決に失敗しました: ' + (err instanceof Error ? err.message : String(err)));
    }
  };

  if (!selectedBook) {
    return <div className="text-center py-8">作品を選択してください。</div>;
  }

  return (
    <div className="animate-fade-in flex flex-col gap-6">
      <h2 className="text-xl font-bold">品質監査 - {selectedBook.title}</h2>
      {loading && <div className="text-center py-4">監査データを読み込み中...</div>}
      {issues.length === 0 && (
        <div className="text-center py-8">
          <h3 className="font-semibold">issueが見つかりませんでした</h3>
          <p className="text-sm text-muted-foreground">
            現在監視対象のissueはありません。素晴らしい！
          </p>
        </div>
      )}
      {issues.length > 0 && (
        <div className="space-y-4">
          {issues.map((issue) => (
            <div key={issue.id} className="border rounded-lg p-4">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold">{issue.title}</h3>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${severityConfig[issue.severity].color}`}>
                  {severityConfig[issue.severity].label}
                </span>
              </div>
              <p className="text-sm text-muted-foreground mb-2">{issue.description}</p>
              {expandedId === issue.id && (
                <div className="mt-4 p-3 bg-[var(--muted)] rounded">
                  <h4 className="font-medium mb-2">詳細情報</h4>
                  <pre className="text-xs overflow-auto">{JSON.stringify(issue.detail || {}, null, 2)}</pre>
                </div>
              )}
              <div className="flex justify-end mt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setExpandedId(expandedId === issue.id ? null : issue.id)}
                >
                  {expandedId === issue.id ? '詳細を閉じる' : '詳細を表示'}
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => handleResolve(issue.id, 'resolve')}
                  className="ml-2"
                >
                  解決
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}