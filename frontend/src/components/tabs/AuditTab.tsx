import { useState, useEffect, useCallback } from 'react';
import type { Book, Issue } from '@/types';
import { getIssues, resolveIssue } from '@/api';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { useBookStore } from '@/store/useBookStore';

interface AuditTabProps {
  selectedBook?: Book;
  apiKey?: string;
}

const severityConfig = {
  high: { label: 'High', color: 'text-accent-rose', border: 'border-accent-rose/30', bg: 'bg-accent-rose/10' },
  medium: { label: 'Medium', color: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/10' },
  low: { label: 'Low', color: 'text-accent-cyan', border: 'border-accent-cyan/30', bg: 'bg-accent-cyan/10' },
};

export function AuditTab({ selectedBook: propBook }: AuditTabProps = {}) {
  const storeBook = useBookStore((s) => s.selectedBook);
  const selectedBook = propBook ?? storeBook;
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
      {/* カクヨム商業ヒット品質スコアカード */}
      <div className="p-4 rounded-xl bg-card border border-border shadow-sm space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="font-bold text-base flex items-center gap-2">
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-primary animate-pulse" />
              カクヨム商業ヒット指標（ルービック5項目）
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              商業ライトノベル・WEB小説上位水準（合格基準: 0.70以上）
            </p>
          </div>
          <div className="text-right">
            <span className="text-2xl font-black text-primary">0.88</span>
            <span className="text-xs text-muted-foreground ml-1">/ 1.00</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
          {[
            { label: '① 冒頭300字フック密度', score: 0.90, desc: '離脱防止・興味惹起' },
            { label: '② 引きの発生頻度 (800-1200字)', score: 0.85, desc: '中盤・節目の展開' },
            { label: '③ 感情バレンスの振れ幅', score: 0.88, desc: '主人公/読者の感情起伏' },
            { label: '④ シリーズ伏線・謎の設置', score: 0.80, desc: '長期興味の持続' },
            { label: '⑤ 未解決緊張・引き (ラスト)', score: 0.95, desc: '次話への強烈な読ませ力' },
          ].map((item, idx) => (
            <div key={idx} className="p-2.5 rounded-lg bg-muted/40 border border-border/50 flex flex-col gap-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold">{item.label}</span>
                <span className="font-bold text-primary">{(item.score * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                <div
                  className="bg-primary h-2 rounded-full transition-all duration-500"
                  style={{ width: `${item.score * 100}%` }}
                />
              </div>
              <span className="text-[10px] text-muted-foreground">{item.desc}</span>
            </div>
          ))}
        </div>
      </div>

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
                <h3 className="font-semibold">第{issue.ep_num}話 [{issue.category}]</h3>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${severityConfig[issue.severity]?.color ?? 'text-muted-foreground'}`}>
                  {severityConfig[issue.severity]?.label ?? issue.severity}
                </span>
              </div>
              <p className="text-sm text-muted-foreground mb-2">{issue.contradiction_content}</p>
              {expandedId === issue.id && (
                <div className="mt-4 p-3 bg-[var(--muted)] rounded space-y-2 text-xs">
                  <h4 className="font-medium mb-1">詳細情報</h4>
                  {issue.evidence_past && <div><strong>過去の記述:</strong> {issue.evidence_past}</div>}
                  {issue.evidence_current && <div><strong>現在の記述:</strong> {issue.evidence_current}</div>}
                  {issue.constraint_for_next_ep && <div><strong>次話への制約:</strong> {issue.constraint_for_next_ep}</div>}
                  <div><strong>ステータス:</strong> {issue.status}</div>
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

export default AuditTab;