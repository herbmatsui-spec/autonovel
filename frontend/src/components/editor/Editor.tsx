import React, { useState, useRef } from "react";
import { InlineAiToolbar } from "./InlineAiToolbar";

interface EditorProps {
  content: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
  genre?: string;
  onToast?: (msg: string, type: "success" | "error" | "info") => void;
}

export const Editor: React.FC<EditorProps> = ({
  content,
  onChange,
  readOnly = false,
  genre = "ハイファンタジー (R15)",
  onToast,
}) => {
  const [tab, setTab] = useState<"edit" | "preview">("edit");
  const [selectedText, setSelectedText] = useState("");
  const [selectionRange, setSelectionRange] = useState<{ start: number; end: number } | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ルビ記法 ｜親文字《ルビ》 を HTML に変換する簡易パーサー
  const renderRuby = (text: string) => {
    const formatted = text
      .replace(/｜(.+?)《(.+?)》/g, "<ruby>$1<rt>$2</rt></ruby>")
      .replace(/\n/g, "<br />");
    return { __html: formatted };
  };

  const handleSelect = () => {
    if (!textareaRef.current) return;
    const start = textareaRef.current.selectionStart;
    const end = textareaRef.current.selectionEnd;
    if (start !== end && start < end) {
      const sel = content.substring(start, end);
      if (sel.trim()) {
        setSelectedText(sel);
        setSelectionRange({ start, end });
      }
    }
  };

  const handleApplyResult = (newText: string, mode: "replace" | "append") => {
    if (!selectionRange) {
      // 選択範囲がない場合は末尾追記
      onChange(content ? `${content}\n\n${newText}` : newText);
      return;
    }

    const before = content.substring(0, selectionRange.start);
    const after = content.substring(selectionRange.end);

    if (mode === "replace") {
      const updated = `${before}${newText}${after}`;
      onChange(updated);
    } else {
      const selected = content.substring(selectionRange.start, selectionRange.end);
      const updated = `${before}${selected}\n${newText}${after}`;
      onChange(updated);
    }
    setSelectedText("");
    setSelectionRange(null);
  };

  const charCount = content.replace(/\s/g, "").length;

  return (
    <div className="editor-container" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "8px",
          borderBottom: "1px solid var(--border-color)",
          paddingBottom: "8px",
        }}
      >
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            className={`btn-tab ${tab === "edit" ? "btn-tab--active" : ""}`}
            onClick={() => setTab("edit")}
            data-testid="tab-edit"
          >
            ✏️ エディタ
          </button>
          <button
            type="button"
            className={`btn-tab ${tab === "preview" ? "btn-tab--active" : ""}`}
            onClick={() => setTab("preview")}
            data-testid="tab-preview"
          >
            📖 ルビ・プレビュー
          </button>
        </div>
        <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
          文字数: <strong>{charCount}</strong> 文字
        </div>
      </div>

      {/* テキスト選択時のインライン AI フローティングツールバー */}
      {tab === "edit" && selectedText && selectionRange && (
        <InlineAiToolbar
          selectedText={selectedText}
          genre={genre}
          contextBefore={content.substring(0, selectionRange.start)}
          contextAfter={content.substring(selectionRange.end)}
          onApplyResult={handleApplyResult}
          onClose={() => {
            setSelectedText("");
            setSelectionRange(null);
          }}
          onToast={onToast}
        />
      )}

      {tab === "edit" ? (
        <textarea
          ref={textareaRef}
          className="textarea"
          style={{ flex: 1, minHeight: "280px", fontFamily: "inherit", resize: "vertical", lineHeight: "1.7" }}
          value={content}
          onChange={(e) => onChange(e.target.value)}
          onSelect={handleSelect}
          readOnly={readOnly}
          placeholder="ここに本文を入力してください。文章を選択するとインラインAI推敲ツールバーが表示されます。"
          data-testid="editor-textarea"
        />
      ) : (
        <div
          className="output-area"
          style={{
            flex: 1,
            minHeight: "280px",
            overflowY: "auto",
            lineHeight: "1.9",
            letterSpacing: "0.05em",
          }}
          dangerouslySetInnerHTML={renderRuby(content || "本文がありません。")}
          data-testid="editor-preview"
        />
      )}
    </div>
  );
};
