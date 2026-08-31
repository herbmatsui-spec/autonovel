import React, { useState } from "react";

interface EditorProps {
  content: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
}

export const Editor: React.FC<EditorProps> = ({ content, onChange, readOnly = false }) => {
  const [tab, setTab] = useState<"edit" | "preview">("edit");

  // ルビ記法 ｜親文字《ルビ》 を HTML に変換する簡易パーサー
  const renderRuby = (text: string) => {
    const formatted = text
      .replace(/｜(.+?)《(.+?)》/g, "<ruby>$1<rt>$2</rt></ruby>")
      .replace(/\n/g, "<br />");
    return { __html: formatted };
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
          >
            ✏️ エディタ
          </button>
          <button
            type="button"
            className={`btn-tab ${tab === "preview" ? "btn-tab--active" : ""}`}
            onClick={() => setTab("preview")}
          >
            📖 ルビ・縦横プレビュー
          </button>
        </div>
        <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
          文字数: <strong>{charCount}</strong> 文字
        </div>
      </div>

      {tab === "edit" ? (
        <textarea
          className="textarea"
          style={{ flex: 1, minHeight: "220px", fontFamily: "inherit", resize: "vertical" }}
          value={content}
          onChange={(e) => onChange(e.target.value)}
          readOnly={readOnly}
          placeholder="ここに本文を入力またはAI生成された内容が表示されます。"
        />
      ) : (
        <div
          className="output-area"
          style={{
            flex: 1,
            minHeight: "220px",
            overflowY: "auto",
            lineHeight: "1.8",
            letterSpacing: "0.05em",
          }}
          dangerouslySetInnerHTML={renderRuby(content || "本文がありません。")}
        />
      )}
    </div>
  );
};
