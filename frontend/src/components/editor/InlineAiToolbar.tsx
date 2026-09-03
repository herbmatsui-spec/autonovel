import React, { useState, useEffect, useRef } from "react";
import { AssistAction, SensoryType, ToneType, AssistResponse } from "../../types/editor";
import { assistContent } from "../../api/editor";

interface InlineAiToolbarProps {
  selectedText: string;
  genre?: string;
  contextBefore?: string;
  contextAfter?: string;
  onApplyResult: (newText: string, mode: "replace" | "append") => void;
  onClose: () => void;
  onToast?: (msg: string, type: "success" | "error" | "info") => void;
}

export const InlineAiToolbar: React.FC<InlineAiToolbarProps> = ({
  selectedText,
  genre = "ハイファンタジー (R15)",
  contextBefore = "",
  contextAfter = "",
  onApplyResult,
  onClose,
  onToast,
}) => {
  const [loading, setLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [preview, setPreview] = useState<AssistResponse | null>(null);
  const toolbarRef = useRef<HTMLDivElement>(null);

  // Click Outside & Escape キー検知
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (toolbarRef.current && !toolbarRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  const handleAction = async (
    action: AssistAction,
    sensoryType?: SensoryType,
    toneType?: ToneType
  ) => {
    if (!selectedText.trim()) {
      onToast?.("テキストを選択してください", "info");
      return;
    }

    const actionKey = sensoryType || toneType || action;
    setActiveAction(actionKey);
    setLoading(true);
    try {
      const res = await assistContent({
        text: selectedText,
        action,
        sensory_type: sensoryType,
        tone_type: toneType,
        genre,
        context_before: contextBefore,
        context_after: contextAfter,
      });
      setPreview(res);
      onToast?.(`✨ ${res.diff_summary} 完了`, "success");
    } catch (err: any) {
      onToast?.(`❌ エラー: ${err.message || err}`, "error");
    } finally {
      setLoading(false);
      setActiveAction(null);
    }
  };

  return (
    <div ref={toolbarRef} className="inline-ai-toolbar" data-testid="inline-ai-toolbar">
      {!preview ? (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.8rem", color: "var(--accent-purple)", fontWeight: 600 }}>
            <span>🪄 AI推敲:</span>
          </div>

          {/* 五感描写ボタン */}
          <button
            type="button"
            className="inline-ai-btn"
            disabled={loading}
            onClick={() => handleAction("describe", "visual")}
            title="光影や細部の視覚描写を肉付け"
            data-testid="btn-sensory-visual"
          >
            {activeAction === "visual" ? <span className="spinner" /> : "👁️"} 視覚
          </button>
          <button
            type="button"
            className="inline-ai-btn"
            disabled={loading}
            onClick={() => handleAction("describe", "auditory")}
            title="環境音や声の響きを肉付け"
          >
            {activeAction === "auditory" ? <span className="spinner" /> : "👂"} 聴覚
          </button>
          <button
            type="button"
            className="inline-ai-btn"
            disabled={loading}
            onClick={() => handleAction("describe", "olfactory")}
            title="大気の匂いや香りを肉付け"
          >
            {activeAction === "olfactory" ? <span className="spinner" /> : "👃"} 嗅覚
          </button>
          <button
            type="button"
            className="inline-ai-btn"
            disabled={loading}
            onClick={() => handleAction("describe", "tactile")}
            title="肌触り・温度・身体感覚を肉付け"
          >
            {activeAction === "tactile" ? <span className="spinner" /> : "✋"} 触覚
          </button>
          <button
            type="button"
            className="inline-ai-btn"
            disabled={loading}
            onClick={() => handleAction("describe", "metaphor")}
            title="美しい比喩・詩的表現に昇華"
          >
            {activeAction === "metaphor" ? <span className="spinner" /> : "✨"} 比喩
          </button>

          {/* Show, Don't Tell */}
          <button
            type="button"
            className="inline-ai-btn"
            disabled={loading}
            onClick={() => handleAction("show_dont_tell")}
            title="感情の説明を行動・情景描写に変換"
            data-testid="btn-show-dont-tell"
          >
            {activeAction === "show_dont_tell" ? <span className="spinner" /> : "🎭"} Show, Don't Tell
          </button>

          {/* トーン変換 */}
          <button
            type="button"
            className="inline-ai-btn"
            disabled={loading}
            onClick={() => handleAction("rewrite", undefined, "tension")}
            title="息詰まる緊迫感・サスペンスに書き換え"
          >
            {activeAction === "tension" ? <span className="spinner" /> : "⚡"} 緊迫感UP
          </button>
          <button
            type="button"
            className="inline-ai-btn"
            disabled={loading}
            onClick={() => handleAction("rewrite", undefined, "fast_paced")}
            title="テンポ良く小気味よい文章に書き換え"
          >
            {activeAction === "fast_paced" ? <span className="spinner" /> : "⏩"} テンポ加速
          </button>

          {loading && (
            <span style={{ fontSize: "0.8rem", color: "var(--accent-cyan)", marginLeft: "4px" }}>
              ⏳ 生成中...
            </span>
          )}

          <button
            type="button"
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              marginLeft: "auto",
              fontSize: "0.9rem",
            }}
            onClick={onClose}
            title="ツールバーを閉じる"
          >
            ✕
          </button>
        </>
      ) : (
        /* 生成結果のプレビュー & 適用選択 */
        <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--accent-cyan)" }}>
              📝 提案プレビュー ({preview.diff_summary})
            </span>
            <button
              type="button"
              style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              onClick={() => setPreview(null)}
            >
              ↩ 再選択
            </button>
          </div>

          <div
            style={{
              background: "rgba(0,0,0,0.4)",
              padding: "8px 12px",
              borderRadius: "6px",
              fontSize: "0.85rem",
              lineHeight: "1.6",
              maxHeight: "120px",
              overflowY: "auto",
            }}
            data-testid="assist-preview-content"
          >
            {preview.result_text}
          </div>

          <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
            <button
              type="button"
              className="inline-ai-btn inline-ai-btn--active"
              onClick={() => {
                onApplyResult(preview.result_text, "replace");
                onClose();
              }}
              data-testid="btn-apply-replace"
            >
              ✅ 選択箇所を置換
            </button>
            <button
              type="button"
              className="inline-ai-btn"
              onClick={() => {
                onApplyResult(preview.result_text, "append");
                onClose();
              }}
            >
              ➕ 直後に追記
            </button>
            <button type="button" className="btn-tab" onClick={onClose}>
              キャンセル
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
