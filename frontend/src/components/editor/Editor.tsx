import React, { useState, useRef, useEffect, useCallback } from "react";
import { InlineAiToolbar } from "./InlineAiToolbar";
import { AutosaveIndicator } from "./AutosaveIndicator";
import { EditorToolbar } from "./EditorToolbar";
import { useNovelContext } from "../../context/NovelContext";
import { useHistoryStack } from "../../hooks/useHistoryStack";
import { useSnapshotHistory } from "../../hooks/useSnapshotHistory";
import { HistoryDrawer } from "./HistoryDrawer";
import { useAutosave, SaveStatus } from "../../hooks/useAutosave";
import { EditorFontFamily, EditorFontSize } from "../../types";

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
  const { activeHighlight, setActiveHighlight, selectedBookId, currentEpNum } = useNovelContext();
  const [tab, setTab] = useState<"edit" | "preview">("edit");
  const [selectedText, setSelectedText] = useState("");
const [selectionRange, setSelectionRange] = useState<{ start: number; end: number } | null>(null);
   const [isHistoryDrawerOpen, setIsHistoryDrawerOpen] = useState(false);
   const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(null);
   const { past, future, present, pushState, undo, redo, canUndo, canRedo } = useHistoryStack();
   const { snapshots, takeSnapshot, restoreSnapshot } = useSnapshotHistory(
     selectedBookId,
     currentEpNum
   );
   const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 編集中の下書きを localStorage にミラー保存 (リロード時の復元用)
  const draftKey = `autonovel.editor.draft.${selectedBookId}.${currentEpNum}`;
  useEffect(() => {
    if (readOnly) return;
    const id = setInterval(() => {
      try {
        window.localStorage.setItem(draftKey, content);
      } catch {
        // ignore storage error
      }
    }, 5000);
    return () => clearInterval(id);
  }, [content, draftKey, readOnly]);

// 矛盾診断ハイライトがアクティブになった際のフォーカス & 選択処理
   useEffect(() => {
     if (!activeHighlight?.conflictingText) return;
 
     // プレビューモードならエディタタブへ自動切り替え
     setTab("edit");
 
     const target = activeHighlight.conflictingText;
     const idx = content.indexOf(target);
     if (idx !== -1 && textareaRef.current) {
       const textarea = textareaRef.current;
       textarea.focus();
       textarea.setSelectionRange(idx, idx + target.length);
       setSelectedText(target);
       setSelectionRange({ start: idx, end: idx + target.length });
 
       // スクロール位置の概算調整
       const linesBefore = content.substring(0, idx).split("\n").length;
       const lineHeight = 24;
       textarea.scrollTop = Math.max(0, (linesBefore - 3) * lineHeight);
     }
   }, [activeHighlight, content]);
 
   const handleUndo = () => {
     const previousText = undo();
     if (previousText !== null) {
       onChange(previousText);
     }
   };
 
   const handleRedo = () => {
     const nextText = redo();
     if (nextText !== null) {
       onChange(nextText);
     }
   };
 
   const handleOpenHistoryDrawer = () => {
     setIsHistoryDrawerOpen(true);
   };
 
   const handleCloseHistoryDrawer = () => {
     setIsHistoryDrawerOpen(false);
   };
 
   const handleSelectSnapshot = (snapshotId: string | null) => {
     setSelectedSnapshotId(snapshotId);
   };
 
   const handleRestoreSnapshot = (snapshotId: string) => {
     const restoredText = restoreSnapshot(snapshotId);
     if (restoredText !== null) {
       // Save current state to undo stack before restoring
       pushState(content);
       // Take a snapshot of the current state as "復元直前"
       takeSnapshot("復元直前", content, "manual");
       // Update content
       onChange(restoredText);
       // Show toast
       const snapshot = snapshots.find((s) => s.id === snapshotId);
       const timeStr = snapshot ? new Date(snapshot.timestamp).toLocaleTimeString() : "";
       onToast?.(`✨ ${timeStr}のバージョンに復元しました`, "success");
     }
     // Close drawer after restore
     setIsHistoryDrawerOpen(false);
   };
 
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

  // ルビ記法挿入ヘルパー
  const handleInsertRuby = () => {
    if (!textareaRef.current) return;
    const start = textareaRef.current.selectionStart;
    const end = textareaRef.current.selectionEnd;
    const selected = content.substring(start, end) || "親文字";
    const rubySnippet = `｜${selected}《ルビ》`;
    const before = content.substring(0, start);
    const after = content.substring(end);
    const updated = `${before}${rubySnippet}${after}`;
    onChange(updated);
    onToast?.("📖 ルビ記法（｜親文字《ルビ》）を挿入しました", "info");

    // カーソル位置を《ルビ》の内部にフォーカス
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        const cursorStart = start + 1 + selected.length + 1;
        textareaRef.current.setSelectionRange(cursorStart, cursorStart + 2);
      }
    }, 50);
};
   const handleCreateBranch = async () => {
     const branchName = window.prompt("新しいIFルートの名前を入力してください（例: 第○話のIFルート）", `IFルート_第${currentEpNum}話`);
     if (!branchName) return; // user cancelled
     try {
       const response = await fetch(`/api/branches/${selectedBookId}/fork`, {
         method: 'POST',
         headers: {
           'Content-Type': 'application/json',
         },
         body: JSON.stringify({
           parent_id: 1, // TODO: we need to get the current branch id? We don't have it in context.
           name: branchName,
           fork_ep_num: currentEpNum,
         }),
       });
       if (!response.ok) {
         throw new Error(`Failed to create branch: ${response.status}`);
       }
       const result = await response.json();
       onToast?.(`✨ IFルート「${branchName}」を作成しました`, "success");
     } catch (err) {
       onToast?.(`❌ エラー: ${err.message || err}`, "error");
     }
   };
   // キーボードショートカット (Ctrl+B = ルビ挿入のみ。Ctrl+S は no-op につき未実装)
const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "b") {
    e.preventDefault();
    handleInsertRuby();
  } else if ((e.ctrlKey || e.metaKey) && e.key === "z") {
    e.preventDefault();
    handleUndo();
  } else if ((e.ctrlKey || e.metaKey) && e.key === "y") {
    e.preventDefault();
    handleRedo();
  } else if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === "Z") {
    e.preventDefault();
    handleRedo();
  }
};

  const charCount = content.replace(/\s/g, "").length;
  const lineCount = content ? content.split("\n").length : 0;
  const readingTimeMin = Math.ceil(charCount / 400); // 一般的な日本語読了速度: 400文字/分

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
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
<div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
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
           {tab === "edit" && (
             <button
               type="button"
               className="inline-ai-btn"
               onClick={handleInsertRuby}
               title="選択文字にルビ記法を挿入 (Ctrl+B)"
               data-testid="btn-insert-ruby"
             >
               🏷️ ルビ挿入
             </button>
)}
      {isHistoryDrawerOpen && (
        <HistoryDrawer
          isOpen={isHistoryDrawerOpen}
          onClose={handleCloseHistoryDrawer}
          snapshots={snapshots}
          currentText={content}
          onSnapshotSelect={handleSelectSnapshot}
          onRestore={handleRestoreSnapshot}
        />
      )}
           {/* History buttons */}
           <button
             type="button"
             onClick={handleUndo}
             disabled={!canUndo}
             title="元に戻す (Ctrl+Z)"
             data-testid="btn-undo"
           >
             ↩ 元に戻す
           </button>
           <button
             type="button"
             onClick={handleRedo}
             disabled={!canRedo}
             title="やり直す (Ctrl+Y)"
             data-testid="btn-redo"
           >
             ↪ やり直す
           </button>
           <button
             type="button"
             onClick={handleOpenHistoryDrawer}
             title="バージョン履歴"
             data-testid="btn-history"
           >
             ⏱️ 履歴
           </button>
{isHistoryDrawerOpen && (
        <HistoryDrawer
          isOpen={isHistoryDrawerOpen}
          onClose={handleCloseHistoryDrawer}
          snapshots={snapshots}
          currentText={content}
          onSnapshotSelect={handleSelectSnapshot}
          onRestore={handleRestoreSnapshot}
        />
      )}
     </div>
        <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", display: "flex", gap: "12px" }}>
          <span>行数: <strong>{lineCount}</strong> 行</span>
          <span>文字数: <strong data-testid="editor-char-count">{charCount}</strong> 文字</span>
          <span>読了目安: <strong>約{readingTimeMin || 1}</strong> 分</span>
        </div>
      </div>

      {/* 矛盾フォーカス時の警告通知バー */}
      {activeHighlight && (
        <div
          style={{
            background: "rgba(239, 68, 68, 0.15)",
            border: "1px solid rgba(239, 68, 68, 0.4)",
            borderRadius: "6px",
            padding: "8px 12px",
            marginBottom: "8px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: "0.85rem",
          }}
          data-testid="active-highlight-banner"
        >
          <div style={{ color: "#f87171" }}>
            🚨 <strong>設定矛盾検出:</strong> 「{activeHighlight.conflictingText}」
            {activeHighlight.suggestedFix && (
              <span style={{ color: "var(--accent-cyan)", marginLeft: "8px" }}>
                → 修正案: 「{activeHighlight.suggestedFix}」
              </span>
)}
      {isHistoryDrawerOpen && (
        <HistoryDrawer
          isOpen={isHistoryDrawerOpen}
          onClose={handleCloseHistoryDrawer}
          snapshots={snapshots}
          currentText={content}
          onSnapshotSelect={handleSelectSnapshot}
          onRestore={handleRestoreSnapshot}
        />
      )}
     </div>
          <div style={{ display: "flex", gap: "6px" }}>
{activeHighlight.suggestedFix && (
               <>
                 <button
                   type="button"
                   className="btn btn-primary"
                   style={{ padding: "3px 8px", fontSize: "0.75rem" }}
                   onClick={() => {
                     if (content.includes(activeHighlight.conflictingText)) {
                       onChange(content.replace(activeHighlight.conflictingText, activeHighlight.suggestedFix));
                       setActiveHighlight(null);
                       onToast?.("✨ 修正案を適用しました", "success");
                     }
                   }}
                 >
                   1クリック修正
                 </button>
                 <button
                   type="button"
                   onClick={handleCreateBranch}
                   title="現在の話数からIFルートを分岐"
                   data-testid="btn-create-branch"
                 >
                   🌿 IF分岐を作成
                 </button>
               </>
             )}
      {isHistoryDrawerOpen && (
        <HistoryDrawer
          isOpen={isHistoryDrawerOpen}
          onClose={handleCloseHistoryDrawer}
          snapshots={snapshots}
          currentText={content}
          onSnapshotSelect={handleSelectSnapshot}
          onRestore={handleRestoreSnapshot}
        />
      )}
            <button
              type="button"
              style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              onClick={() => setActiveHighlight(null)}
            >
              ✕
            </button>
{isHistoryDrawerOpen && (
        <HistoryDrawer
          isOpen={isHistoryDrawerOpen}
          onClose={handleCloseHistoryDrawer}
          snapshots={snapshots}
          currentText={content}
          onSnapshotSelect={handleSelectSnapshot}
          onRestore={handleRestoreSnapshot}
        />
      )}
     </div>
        </div>
      )}

      {/* テキスト選択時のインライン AI フローティングツールバー */}
      {tab === "edit" && selectedText && selectionRange && !activeHighlight && (
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
          onKeyDown={handleKeyDown}
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
