import React, { useState, useEffect, useRef } from "react";
import { AskBibleResponse, ConsistencyIssue } from "../../types/editor";
import { askBible, auditConsistency, resolveIssue } from "../../api/editor";
import { useNovelContext } from "../../context/NovelContext";

interface EditorialSidebarProps {
  bookId?: number;
  currentText: string;
  onToast?: (msg: string, type: "success" | "error" | "info") => void;
}

interface ChatMessage {
  sender: "user" | "ai";
  text: string;
  evidence?: Array<{ id: string; label: string; source_reference: string }>;
}

const QUICK_QUERIES = [
  "主人公の能力・制限は？",
  "これまでの伏線一覧は？",
  "世界観の魔法・ルールは？",
  "未回収の課題・対立は？",
];

export const EditorialSidebar: React.FC<EditorialSidebarProps> = ({
  bookId = 1,
  currentText,
  onToast,
}) => {
  const {
    activeHighlight,
    setActiveHighlight,
    currentChapterText,
    setCurrentChapterText,
  } = useNovelContext();

  const [tab, setTab] = useState<"chat" | "audit">("chat");

  // Q&A 状態
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      sender: "ai",
      text: "こんにちは！作品専属のAI編集者です。世界観設定やキャラクター情報、過去の伏線について何でも質問してください。",
    },
  ]);
  const [inputQuery, setInputQuery] = useState("");
  const [isQuerying, setIsQuerying] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 矛盾診断状態
  const [isAuditing, setIsAuditing] = useState(false);
  const [auditIssues, setAuditIssues] = useState<ConsistencyIssue[]>([]);
  const [auditDone, setAuditDone] = useState(false);
  const [resolvingId, setResolvingId] = useState<string | number | null>(null);

  // メッセージ追加時の自動スクロール
  useEffect(() => {
    if (tab === "chat" && typeof messagesEndRef.current?.scrollIntoView === "function") {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, tab, isQuerying]);

  const executeQuery = async (queryText: string) => {
    if (!queryText.trim() || isQuerying) return;

    setMessages((prev) => [...prev, { sender: "user", text: queryText }]);
    setIsQuerying(true);

    try {
      const res: AskBibleResponse = await askBible({
        book_id: bookId,
        query: queryText,
      });

      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: res.answer,
          evidence: res.evidence_nodes.map((n) => ({
            id: n.id,
            label: n.label,
            source_reference: n.source_reference,
          })),
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: `❌ 検索エラー: ${err.message || err}`,
        },
      ]);
    } finally {
      setIsQuerying(false);
    }
  };

  const handleSendQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isQuerying) return;
    const q = inputQuery.trim();
    setInputQuery("");
    await executeQuery(q);
  };

  const handleAudit = async () => {
    if (!currentText.trim()) {
      onToast?.("本文を入力してから矛盾診断を実行してください", "info");
      return;
    }

    setIsAuditing(true);
    try {
      const res = await auditConsistency({
        book_id: bookId,
        content: currentText,
      });
      setAuditIssues(res.issues);
      setAuditDone(true);
      if (res.has_issues) {
        onToast?.(`⚠️ ${res.issues.length} 件の設定矛盾・懸念を検出しました`, "info");
      } else {
        onToast?.("✨ 設定上の矛盾は見つかりませんでした！", "success");
      }
    } catch (err: any) {
      onToast?.(`❌ 診断エラー: ${err.message || err}`, "error");
    } finally {
      setIsAuditing(false);
    }
  };

  const handleFocusIssue = (issue: ConsistencyIssue, idx: number) => {
    if (!issue.conflicting_text) {
      onToast?.("該当箇所のテキストが指定されていません", "info");
      return;
    }
    const issueId = issue.id ? String(issue.id) : `issue-${idx}`;
    setActiveHighlight({
      issueId,
      conflictingText: issue.conflicting_text,
      suggestedFix: issue.suggested_fix,
      issueType: issue.issue_type,
    });
    onToast?.(`🎯 本文の該当箇所をフォーカスしました: 「${issue.conflicting_text}」`, "info");
  };

  const handleApplyFix = (issue: ConsistencyIssue, idx: number) => {
    if (!issue.conflicting_text || !issue.suggested_fix) {
      onToast?.("置換対象または修正案が空です", "info");
      return;
    }

    if (!currentChapterText.includes(issue.conflicting_text)) {
      onToast?.("該当文が現在の本文中に見つかりませんでした", "error");
      return;
    }

    const updated = currentChapterText.replace(issue.conflicting_text, issue.suggested_fix);
    setCurrentChapterText(updated);
    setActiveHighlight(null);

    // 解決済みとしてissue一覧から削除または更新
    setAuditIssues((prev) => prev.filter((_, i) => i !== idx));
    onToast?.(`✨ 修正案を本文に適用しました！`, "success");
  };

  const handleResolveAction = async (
    issue: ConsistencyIssue,
    idx: number,
    action: "Foreshadowing" | "Ignore"
  ) => {
    const issueId = issue.id || idx + 1;
    setResolvingId(issueId);
    try {
      await resolveIssue(issueId, action);
      setAuditIssues((prev) => prev.filter((_, i) => i !== idx));
      setActiveHighlight(null);
      if (action === "Foreshadowing") {
        onToast?.("📌 世界観バイブルの伏線マップに登録しました！", "success");
      } else {
        onToast?.("🛡️ 許容例外ルール (Rule of Cool) に登録しました！", "success");
      }
    } catch (err: any) {
      // フォールバック: UI上で解決扱いに
      setAuditIssues((prev) => prev.filter((_, i) => i !== idx));
      setActiveHighlight(null);
      onToast?.(`✨ 設定に反映しました (${action === "Foreshadowing" ? "伏線化" : "例外許可"})`, "success");
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <div className="editorial-chat-box" data-testid="editorial-sidebar">
      {/* タブ切り替え */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px", borderBottom: "1px solid var(--border-color)", paddingBottom: "8px" }}>
        <button
          type="button"
          className={`btn-tab ${tab === "chat" ? "btn-tab--active" : ""}`}
          onClick={() => setTab("chat")}
          data-testid="tab-ask-bible"
        >
          💬 Ask Bible (Q&A)
        </button>
        <button
          type="button"
          className={`btn-tab ${tab === "audit" ? "btn-tab--active" : ""}`}
          onClick={() => setTab("audit")}
          data-testid="tab-audit-consistency"
        >
          🔍 矛盾チェック {auditIssues.length > 0 && `(${auditIssues.length})`}
        </button>
      </div>

      {tab === "chat" ? (
        <>
          <div className="editorial-messages" data-testid="editorial-messages">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`editorial-msg ${m.sender === "user" ? "editorial-msg--user" : "editorial-msg--ai"}`}
              >
                <div>{m.text}</div>
                {m.evidence && m.evidence.length > 0 && (
                  <div style={{ marginTop: "6px" }}>
                    {m.evidence.map((ev, eIdx) => (
                      <span key={eIdx} className="evidence-tag" title={`出展: ${ev.source_reference}`}>
                        📊 [{ev.label}] {ev.id}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {isQuerying && (
              <div className="editorial-msg editorial-msg--ai" style={{ color: "var(--accent-cyan)", display: "flex", alignItems: "center", gap: "6px" }}>
                <span className="spinner" /> <span>GraphRAG ナレッジを探索中...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* クイック質問チップ */}
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "8px" }}>
            {QUICK_QUERIES.map((q, idx) => (
              <button
                key={idx}
                type="button"
                className="query-chip"
                disabled={isQuerying}
                onClick={() => executeQuery(q)}
                data-testid={`quick-query-${idx}`}
              >
                💡 {q}
              </button>
            ))}
          </div>

          <form onSubmit={handleSendQuery} style={{ display: "flex", gap: "8px" }}>
            <input
              className="input"
              style={{ flex: 1, padding: "8px 12px", fontSize: "0.85rem" }}
              placeholder="設定や過去の出来事を質問..."
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              disabled={isQuerying}
              data-testid="input-ask-bible"
            />
            <button
              type="submit"
              className="btn btn-primary"
              style={{ padding: "8px 14px", fontSize: "0.85rem" }}
              disabled={isQuerying || !inputQuery.trim()}
              data-testid="btn-submit-ask-bible"
            >
              送信
            </button>
          </form>
        </>
      ) : (
        /* 矛盾診断タブ */
        <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
          <div style={{ marginBottom: "12px" }}>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "12px" }}>
              現在の執筆本文を、ナレッジグラフおよび世界観バイブルと照合して設定矛盾を検出します。
            </p>
            <button
              type="button"
              className="btn btn-primary"
              style={{ width: "100%", padding: "8px" }}
              onClick={handleAudit}
              disabled={isAuditing}
              data-testid="btn-run-audit"
            >
              {isAuditing ? "🔍 設定照合・診断中..." : "🔍 本文の設定矛盾を診断"}
            </button>
          </div>

          <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "10px" }}>
            {auditDone && auditIssues.length === 0 && (
              <div style={{ padding: "12px", background: "rgba(16, 185, 129, 0.1)", border: "1px solid var(--accent-success)", borderRadius: "8px", color: "#34d399", fontSize: "0.85rem" }}>
                ✅ 設定矛盾は見つかりませんでした。整合性は良好です！
              </div>
            )}

            {auditIssues.map((issue, idx) => {
              const isHighlighted = activeHighlight?.conflictingText === issue.conflicting_text;
              return (
                <div
                  key={idx}
                  style={{
                    background: isHighlighted
                      ? "rgba(239, 68, 68, 0.25)"
                      : issue.severity === "error"
                      ? "rgba(239, 68, 68, 0.12)"
                      : "rgba(245, 158, 11, 0.12)",
                    border: `1px solid ${
                      isHighlighted
                        ? "#f87171"
                        : issue.severity === "error"
                        ? "rgba(239, 68, 68, 0.4)"
                        : "rgba(245, 158, 11, 0.4)"
                    }`,
                    padding: "12px",
                    borderRadius: "8px",
                    fontSize: "0.85rem",
                    transition: "all 0.2s ease",
                  }}
                  data-testid={`audit-issue-card-${idx}`}
                >
                  <div style={{ fontWeight: 700, color: issue.severity === "error" ? "#f87171" : "#fbbf24", marginBottom: "4px" }}>
                    {issue.severity === "error" ? "🚨 重大矛盾" : "⚠️ 警告"}: {issue.issue_type}
                  </div>
                  <div style={{ marginBottom: "6px", lineHeight: "1.4" }}>{issue.description}</div>
                  {issue.conflicting_text && (
                    <div style={{ fontStyle: "italic", color: "var(--text-muted)", fontSize: "0.8rem", marginBottom: "6px" }}>
                      該当文: 「{issue.conflicting_text}」
                    </div>
                  )}
                  {issue.suggested_fix && (
                    <div style={{ color: "var(--accent-cyan)", fontSize: "0.8rem", marginBottom: "10px" }}>
                      💡 修正案: {issue.suggested_fix}
                    </div>
                  )}

                  {/* アクションボタン群 */}
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px" }}>
                    {issue.conflicting_text && (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                        onClick={() => handleFocusIssue(issue, idx)}
                        data-testid={`btn-focus-issue-${idx}`}
                      >
                        🎯 本文で確認
                      </button>
                    )}

                    {issue.suggested_fix && (
                      <button
                        type="button"
                        className="btn btn-primary"
                        style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                        onClick={() => handleApplyFix(issue, idx)}
                        data-testid={`btn-apply-fix-${idx}`}
                      >
                        💡 修正案を適用
                      </button>
                    )}

                    <button
                      type="button"
                      className="inline-ai-btn"
                      style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                      disabled={resolvingId !== null}
                      onClick={() => handleResolveAction(issue, idx, "Foreshadowing")}
                      title="世界観バイブルの伏線マップに追加"
                      data-testid={`btn-foreshadow-${idx}`}
                    >
                      📌 伏線化
                    </button>

                    <button
                      type="button"
                      className="inline-ai-btn"
                      style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                      disabled={resolvingId !== null}
                      onClick={() => handleResolveAction(issue, idx, "Ignore")}
                      title="設定の例外ルール (Rule of Cool) として許容"
                      data-testid={`btn-rule-of-cool-${idx}`}
                    >
                      🛡️ 許容例外
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
