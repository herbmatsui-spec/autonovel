import React, { useState } from "react";

export interface ConflictItem {
  category: string;
  severity: "critical" | "high" | "medium" | "low";
  title: string;
  description: string;
  field_path: string | null;
  current_value: string | null;
  suggested_value: string | null;
  evidence_past: string;
  evidence_current: string;
  constraint_for_next: string;
  confidence: number;
}

export interface ConflictReport {
  book_id: number;
  ep_num: number;
  patch_review_id: number | null;
  summary: string;
  total_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  conflicts: ConflictItem[];
}

export interface ConflictReportPanelProps {
  report: ConflictReport;
  onApprove?: (reviewId: number, comment?: string) => void;
  onReject?: (reviewId: number, comment: string) => void;
  onRevise?: (reviewId: number, proposedContent: string, comment?: string) => void;
  onClose?: () => void;
  onRunAudit?: () => void;
  isLoading?: boolean;
}

const SEVERITY_COLORS = {
  critical: "#ff6b6b",
  high: "#ffb74d",
  medium: "#ffd54f",
  low: "#cddc39",
} as const;

const SEVERITY_LABELS = {
  critical: "緊急",
  high: "高",
  medium: "中",
  low: "低",
} as const;

const CATEGORY_LABELS: Record<string, string> = {
  fast_screen: "プロット構造",
  logical_consistency: "論理整合性",
  deai: "AI感・文体",
  ability_consistency: "能力整合性",
  causal_integrity: "因果律",
  rhythm: "文長リズム",
  dialogue: "台詞・会話比率",
  cliche: "AI定型表現",
  hook: "引き・クリフハンガー",
  character: "キャラクター心理",
};

export const ConflictReportPanel: React.FC<ConflictReportPanelProps> = ({
  report,
  onApprove,
  onReject,
  onRevise,
  onClose,
  onRunAudit,
  isLoading = false,
}) => {
  const [activeTab, setActiveTab] = useState<"list" | "diff" | "actions">("list");
  const [selectedConflict, setSelectedConflict] = useState<ConflictItem | null>(null);
  const [revisionContent, setRevisionContent] = useState("");
  const [revisionComment, setRevisionComment] = useState("");
  const [rejectComment, setRejectComment] = useState("");

  const handleApprove = () => {
    if (report.patch_review_id && onApprove) {
      onApprove(report.patch_review_id);
    }
  };

  const handleReject = () => {
    if (report.patch_review_id && rejectComment.trim() && onReject) {
      onReject(report.patch_review_id, rejectComment);
    }
  };

  const handleRevise = () => {
    if (report.patch_review_id && revisionContent.trim() && onRevise) {
      onRevise(report.patch_review_id, revisionContent, revisionComment);
    }
  };

  const renderDiff = (current: string | null, suggested: string | null) => {
    if (!current && !suggested) return <div className="diff-empty">差分なし</div>;

    const curLines = (current || "").split("\n");
    const sugLines = (suggested || "").split("\n");

    return (
      <div className="diff-container">
        <div className="diff-side">
          <div className="diff-header">現在の値</div>
          <pre className="diff-content">
            {curLines.map((l, i) => (
              <div key={i} className="diff-line removed">{l}</div>
            ))}
          </pre>
        </div>
        <div className="diff-side">
          <div className="diff-header">推奨値</div>
          <pre className="diff-content">
            {sugLines.map((l, i) => (
              <div key={i} className="diff-line added">{l}</div>
            ))}
          </pre>
        </div>
      </div>
    );
  };

  return (
    <div className="conflict-report-panel" data-testid="conflict-report-panel">
      <div className="panel-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <h2 style={{ fontSize: "1.1rem", margin: 0 }}>⚠️ 矛盾・二層監査レポート - 第{report.ep_num}話</h2>
        {onClose && (
          <button className="btn-close" onClick={onClose} aria-label="閉じる">×</button>
        )}
      </div>

      <div className="panel-summary" style={{ marginBottom: "16px", padding: "12px", background: "var(--bg-input)", borderRadius: "8px" }}>
        <div className="summary-stats" style={{ display: "flex", gap: "12px", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 600 }}>
          <span className="stat total">総計: {report.total_count}</span>
          <span className="stat critical" style={{ color: SEVERITY_COLORS.critical }}>緊急: {report.critical_count}</span>
          <span className="stat high" style={{ color: SEVERITY_COLORS.high }}>高: {report.high_count}</span>
          <span className="stat medium" style={{ color: SEVERITY_COLORS.medium }}>中: {report.medium_count}</span>
          <span className="stat low" style={{ color: SEVERITY_COLORS.low }}>低: {report.low_count}</span>
        </div>
        {report.summary && <pre className="summary-text" style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)", whiteSpace: "pre-wrap" }}>{report.summary}</pre>}
      </div>

      <div className="panel-tabs" style={{ display: "flex", gap: "8px", marginBottom: "12px" }}>
        <button
          type="button"
          className={`btn-tab ${activeTab === "list" ? "btn-tab--active" : ""}`}
          onClick={() => setActiveTab("list")}
        >
          矛盾・指摘一覧 ({report.conflicts.length})
        </button>
        <button
          type="button"
          className={`btn-tab ${activeTab === "diff" ? "btn-tab--active" : ""}`}
          onClick={() => setActiveTab("diff")}
          disabled={!selectedConflict}
        >
          詳細diff
        </button>
        {report.patch_review_id && (
          <button
            type="button"
            className={`btn-tab ${activeTab === "actions" ? "btn-tab--active" : ""}`}
            onClick={() => setActiveTab("actions")}
          >
            アクション
          </button>
        )}
      </div>

      <div className="panel-content">
        {activeTab === "list" && (
          <div className="conflict-list" style={{ maxHeight: "400px", overflowY: "auto" }}>
            {report.conflicts.length === 0 ? (
              <div style={{ textAlign: "center", padding: "32px 16px", color: "var(--text-muted)" }}>
                <div style={{ fontSize: "2rem", marginBottom: "8px" }}>✅</div>
                <div style={{ fontWeight: 600, marginBottom: "8px" }}>矛盾やAI定型表現は検出されませんでした</div>
                <div style={{ fontSize: "0.85rem", marginBottom: "16px" }}>文章のテンポと一貫性は良好に保たれています。</div>
                {onRunAudit && (
                  <button
                    type="button"
                    className="inline-ai-btn"
                    data-testid="btn-run-audit-panel"
                    onClick={onRunAudit}
                    disabled={isLoading}
                    style={{ padding: "8px 16px", fontSize: "0.9rem" }}
                  >
                    {isLoading ? "🧠 二層診断を実行中..." : "🧠 AI二層診断を実行する"}
                  </button>
                )}
              </div>
            ) : (
              report.conflicts.map((conflict, index) => (
                <div
                  key={index}
                  className="conflict-card"
                  style={{
                    borderLeft: `4px solid ${SEVERITY_COLORS[conflict.severity]}`,
                    background: selectedConflict === conflict ? "rgba(255, 213, 79, 0.1)" : "var(--bg-input)",
                    padding: "12px",
                    borderRadius: "6px",
                    marginBottom: "8px",
                    cursor: "pointer",
                  }}
                  onClick={() => setSelectedConflict(conflict)}
                >
                  <div className="conflict-header" style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "6px" }}>
                    <span className="conflict-category" style={{ fontWeight: 600, color: "var(--accent-cyan)" }}>
                      {CATEGORY_LABELS[conflict.category] || conflict.category}
                    </span>
                    <span
                      className="conflict-severity"
                      style={{ background: SEVERITY_COLORS[conflict.severity], color: "#000", padding: "2px 6px", borderRadius: "4px", fontSize: "0.75rem", fontWeight: 700 }}
                    >
                      {SEVERITY_LABELS[conflict.severity]}
                    </span>
                    {conflict.confidence && (
                      <span className="conflict-confidence" style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginLeft: "auto" }}>
                        信頼度: {(conflict.confidence * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                  <div style={{ fontWeight: 600, fontSize: "0.9rem", marginBottom: "4px" }}>{conflict.title}</div>
                  <div className="conflict-description" style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>{conflict.description}</div>
                  {conflict.field_path && (
                    <div className="conflict-field" style={{ fontSize: "0.8rem", marginTop: "4px" }}>
                      対象箇所: <code>{conflict.field_path}</code>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === "diff" && selectedConflict && (
          <div className="diff-view">
            <h4>{CATEGORY_LABELS[selectedConflict.category] || selectedConflict.category}</h4>
            {renderDiff(selectedConflict.current_value, selectedConflict.suggested_value)}
            {selectedConflict.evidence_past && (
              <details style={{ marginTop: "12px" }}>
                <summary>過去の記述根拠</summary>
                <pre style={{ fontSize: "0.85rem", whiteSpace: "pre-wrap" }}>{selectedConflict.evidence_past}</pre>
              </details>
            )}
            {selectedConflict.evidence_current && (
              <details style={{ marginTop: "8px" }}>
                <summary>現在の記述箇所</summary>
                <pre style={{ fontSize: "0.85rem", whiteSpace: "pre-wrap" }}>{selectedConflict.evidence_current}</pre>
              </details>
            )}
          </div>
        )}

        {activeTab === "actions" && report.patch_review_id && (
          <div className="actions-view" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div className="action-section">
              <h4>承認</h4>
              <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>推奨されたパッチをそのまま本文へ適用します。</p>
              <button type="button" className="btn-primary" onClick={handleApprove}>パッチを適用して承認</button>
            </div>
            <div className="action-section">
              <h4>却下</h4>
              <textarea
                placeholder="却下理由を入力してください..."
                value={rejectComment}
                onChange={(e) => setRejectComment(e.target.value)}
                style={{ width: "100%", minHeight: "60px", marginBottom: "8px" }}
              />
              <button type="button" className="btn-secondary" onClick={handleReject} disabled={!rejectComment.trim()}>
                指摘を却下
              </button>
            </div>
            <div className="action-section">
              <h4>修正して適用</h4>
              <textarea
                placeholder="修正後の本文内容..."
                value={revisionContent}
                onChange={(e) => setRevisionContent(e.target.value)}
                style={{ width: "100%", minHeight: "80px", marginBottom: "8px" }}
              />
              <button type="button" className="btn-secondary" onClick={handleRevise} disabled={!revisionContent.trim()}>
                修正内容を適用
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};