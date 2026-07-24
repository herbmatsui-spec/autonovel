import { useState, useEffect } from 'react';
import type { Book } from '@/types';
import { getIssues, resolveIssue } from '@/api';
import { toast } from 'sonner';

interface Issue {
  id: number;
  category: string;
  severity: 'high' | 'medium' | 'low';
  ep_num: number;
  created_at: string;
  contradiction_content: string;
  evidence_past?: string;
  evidence_current?: string;
  constraint_for_next_ep?: string;
  status: string;
  resolved_note?: string;
}

interface AuditTabProps {
  selectedBook: Book;
  apiKey: string;
}

const severityConfig = {
  high: { label: 'High', color: 'text-accent-rose', border: 'border-accent-rose/30', bg: 'bg-accent-rose/10' },
  medium: { label: 'Medium', color: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/10' },
  low: { label: 'Low', color: 'text-accent-cyan', border: 'border-accent-cyan/30', bg: 'bg-accent-cyan/10' },
};

export function AuditTab({ selectedBook, apiKey }: AuditTabProps) {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const loadIssues = async () => {
    setLoading(true);
    try {
      const data = await getIssues(selectedBook.id);
      setIssues(data);
    } catch (err: any) {
      toast.error('issue読み込みに失敗: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIssues();
  }, [selectedBook.id]);

  const handleResolve = async (issueId: number, action: string) => {
    try {
      await resolveIssue(issueId, action, apiKey);
      toast.success(`Issue #${issueId} を「${action}」で解決しました。`);
      loadIssues();
    } catch (err: any) {
      toast.error('解決に失敗: ' + err.message);
    }
  };

  const unresolved = issues.filter((i) => i.status === 'open');
  const resolved = issues.filter((i) => i.status !== 'open');

  return (
    <div className="animate-fade-in flex flex-col gap-8">
      <div>
        <h3 className="text-xl text-white font-bold">⚖️ 監査・チケット管理ダッシュボード</h3>
        <p className="text-secondary text-sm">
          AIが検出した作品内の矛盾や整合性の問題を解決します。
        </p>
      </div>

      {loading && issues.length === 0 ? (
        <div className="text-sm text-muted">読み込み中...</div>
      ) : unresolved.length === 0 ? (
        <div className="glass-panel p-6 text-center text-emerald-400">
          ✅ 未解決のIssueはありません。作品の整合性は良好です。
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <h4 className="text-sm font-bold text-muted-foreground">未解決のIssue ({unresolved.length}件)</h4>
          {unresolved.map((issue) => {
            const sev = severityConfig[issue.severity] || severityConfig.medium;
            return (
              <div key={issue.id} className={`glass-panel border ${sev.border} p-5`}>
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`badge ${sev.bg} ${sev.color}`}>{sev.label}</span>
                      <span className="text-xs text-muted">EP {issue.ep_num}</span>
                      <span className="text-xs text-muted">#{issue.id}</span>
                    </div>
                    <h5 className="text-sm font-bold mb-1">{issue.category}</h5>
                    <p className="text-sm text-secondary whitespace-pre-wrap">{issue.contradiction_content}</p>
                  </div>
                </div>

                {expandedId === issue.id && (
                  <div className="mt-4 space-y-2">
                    {issue.evidence_past && (
                      <div className="text-xs">
                        <span className="font-bold text-muted-foreground">過去の設定: </span>
                        <span className="text-secondary">{issue.evidence_past}</span>
                      </div>
                    )}
                    {issue.evidence_current && (
                      <div className="text-xs">
                        <span className="font-bold text-muted-foreground">現在の設定: </span>
                        <span className="text-secondary">{issue.evidence_current}</span>
                      </div>
                    )}
                    {issue.constraint_for_next_ep && (
                      <div className="text-xs">
                        <span className="font-bold text-muted-foreground">次のEPへの制約: </span>
                        <span className="text-secondary">{issue.constraint_for_next_ep}</span>
                      </div>
                    )}
                  </div>
                )}

                <div className="flex gap-2 mt-4">
                  <button onClick={() => handleResolve(issue.id, 'Auto-Fix')} className="btn btn-primary text-xs">
                    🪄 AIクイック修正
                  </button>
                  <button onClick={() => handleResolve(issue.id, 'Foreshadowing')} className="btn btn-secondary text-xs">
                    🔮 伏線として登録
                  </button>
                  <button onClick={() => handleResolve(issue.id, 'Ignore')} className="btn btn-secondary text-xs">
                    😎 無視する
                  </button>
                  <button onClick={() => setExpandedId(expandedId === issue.id ? null : issue.id)} className="btn btn-secondary text-xs">
                    {expandedId === issue.id ? '詳細を閉じる' : '詳細を表示'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {resolved.length > 0 && (
        <details className="glass-panel p-5">
          <summary className="text-sm font-bold cursor-pointer">解決済みIssue一覧 ({resolved.length}件)</summary>
          <div className="mt-4 space-y-2">
            {resolved.map((issue) => (
              <div key={issue.id} className="text-xs text-muted flex justify-between">
                <span>#{issue.id} {issue.category} (EP {issue.ep_num})</span>
                <span>{issue.status}</span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}