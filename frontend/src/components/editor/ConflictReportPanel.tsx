import React, { useState } from "react";

interface ConflictItem {
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

interface ConflictReport {
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

interface ConflictReportPanelProps {
  report: ConflictReport;
  onApprove: (reviewId: number, comment?: string) => void;
  onReject: (reviewId: number, comment: string) => void;
  onRevise: (reviewId: number, proposedContent: string, comment?: string) => void;
  onClose: () => void;
}

const SEVERITY_COLORS = {
  critical: "#ff4444",
  high: "#ff8800",
  medium: "#ffcc00",
  low: "#88cc00",
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
};

export const ConflictReportPanel: React.FC<ConflictReportPanelProps> = ({
  report,
  onApprove,
  onReject,
  onRevise,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<"list" | "diff" | "actions">("list");
  const [selectedConflict, setSelectedConflict] = useState<ConflictItem | null>(null);
  const [revisionContent, setRevisionContent] = useState("");
  const [revisionComment, setRevisionComment] = useState("");
  const [rejectComment, setRejectComment] = useState("");

  const handleApprove = () => {
    if (report.patch_review_id) {
      onApprove(report.patch_review_id);
    }
  };

  const handleReject = () => {
    if (report.patch_review_id && rejectComment.trim()) {
      onReject(report.patch_review_id, rejectComment);
    }
  };

  const handleRevise = () => {
    if (report.patch_review_id && revisionContent.trim()) {
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
          <pre className="diff-content">{curLines.map((l, i) => (
            <div key={i} className="diff-line removed">{l}</div>
          ))}</pre>
        </div>
        <div className="diff-side">
          <div className="diff-header">推奨値</div>
          <pre className="diff-content">{sugLines.map((l, i) => (
            <div key={i} className="diff-line added">{l}</div>
          ))}</pre>
        </div>
      </div>
    );
  };

  return (
    <div className="conflict-report-panel">
      <div className="panel-header">
        <h2>⚠️ 矛盾レポート - 第{report.ep_num}話</h2>
        <button className="btn-close" onClick={onClose}>×</button>
      </div>

      <div className="panel-summary">
        <div className="summary-stats">
          <span className="stat total">総計: {report.total_count}</span>
          <span className="stat critical" style={{color: SEVERITY_COLORS.critical}}>緊急: {report.critical_count}</span>
          <span className="stat high" style={{color: SEVERITY_COLORS.high}}>高: {report.high_count}</span>
          <span className="stat medium" style={{color: SEVERITY_COLORS.medium}}>中: {report.medium_count}</span>
          <span className="stat low" style={{color: SEVERITY_COLORS.low}}>低: {report.low_count}</span>
        </div>
        <pre className="summary-text">{report.summary}</pre>
      </div>

      <div className="panel-tabs">
        <button
          className={activeTab === "list" ? "active" : ""}
          onClick={() => setActiveTab("list")}
        >
          矛盾一覧 ({report.conflicts.length})
        </button>
        <button
          className={activeTab === "diff" ? "active" : ""}
          onClick={() => setActiveTab("diff")}
          disabled={!selectedConflict}
        >
          詳細diff
        </button>
        <button
          className={activeTab === "actions" ? "active" : ""}
          onClick={() => setActiveTab("actions")}
        >
          アクション
        </button>
      </div>

      <div className="panel-content">
        {activeTab === "list" && (
          <div className="conflict-list" style={{maxHeight: "400px", overflowY: "auto"}}>
            {report.conflicts.map((conflict, index) => (
              <div
                key={index}
                className="conflict-card"
                style={{
                  borderLeft: `4px solid ${SEVERITY_COLORS[conflict.severity]}`,
                  background: selectedConflict === conflict ? "rgba(0,123,255,0.1)" : "transparent",
                }}
                onClick={() => setSelectedConflict(conflict)}
              >
                <div className="conflict-header">
                  <span className="conflict-category">{CATEGORY_LABELS[conflict.category] || conflict.category}</span>
                  <span
                    className="conflict-severity"
                    style={{background: SEVERITY_COLORS[conflict.severity], color: "#fff"}}
                  >
                    {SEVERITY_LABELS[conflict.severity]}
                  </span>
                  <span className="conflict-confidence">信頼度: {(conflict.confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="conflict-description">{conflict.description}</div>
                {conflict.field_path && (
                  <div className="conflict-field">フィールド: <code>{conflict.field_path}</code></div>
                )}
              </div>
            ))}
          </div>
        )}

        {activeTab === "diff" && selectedConflict && (
          <div className="diff-view">
            <h4>{CATEGORY_LABELS[selectedConflict.category] || selectedConflict.category}</h4>
            {renderDiff(selectedConflict.current_value, selectedConflict.suggested_value)}
            {selectedConflict.evidence_past && (
              <details>
                <summary>過去の証拠</summary>
                <pre>{selectedConflict.evidence_past}</pre>
              </details>
            )}
            {selectedConflict.evidence_current && (
              <details>
                <summary>現在の証拠</summary>
                <pre>{selectedConflict.evidence_current}</pre>
              </details>
            )}
            {selectedConflict.constraint_for_next && (
              <details>
                <summary>次回への制約</summary>
                <pre>{selectedConflict.constraint_for_next}</pre>
              </details>
            )}
          </div>
        )}

        {activeTab === "actions" && (
          <div className="actions-view">
            <div className="action-group">
              <h4>承認</h4>
              <p>矛盾内容を確認し、推奨修正案を適用して次に進みます。</p>
              <button className="btn-primary" onClick={handleApprove}>
                ✅ 承認して続行
              </button>
            </div>

            <div className="action-group">
              <h4>差し戻し</h4>
              <p>矛盾指摘に不同意の場合、理由を添えて差し戻します（修復フェーズへ）。</p>
              <textarea
                placeholder="差し戻し理由（必須）"
                value={rejectComment}
                onChange={(e) => setRejectComment(e.target.value)}
                rows={3}
              />
              <button className="btn-danger" onClick={handleReject} disabled={!rejectComment.trim()}>
                ❌ 差し戻し
              </button>
            </div>

            <div className="action-group">
              <h4>修正案を提示</h4>
              <p>推奨値を修正して再レビューを要求します。</p>
              <textarea
                placeholder="修正後の提案内容"
                value={revisionContent}
                onChange={(e) => setRevisionContent(e.target.value)}
                rows={5}
                defaultValue={selectedConflict?.suggested_value || ""}
              />
              <textarea
                placeholder="修正理由（任意）"
                value={revisionComment}
                onChange={(e) => setRevisionComment(e.target.value)}
                rows={2}
              />
              <button className="btn-secondary" onClick={handleRevise} disabled={!revisionContent.trim()}>
                🔄 修正案を提示
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};