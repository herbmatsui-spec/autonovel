import React, { useState, useRef, useEffect, useCallback } from "react";
import { InlineAiToolbar } from "./InlineAiToolbar";
import { AutosaveIndicator } from "./AutosaveIndicator";
import { EditorToolbar } from "./EditorToolbar";
import { useNovelContext } from "../../context/NovelContext";
import { fetchNodeSummary } from "../../api/graph";
import { SnippetTooltip } from "./SnippetTooltip";
import { useHistoryStack } from "../../hooks/useHistoryStack";
import { useSnapshotHistory } from "../../hooks/useSnapshotHistory";
import { HistoryDrawer } from "./HistoryDrawer";
import { EditorFontFamily, EditorFontSize } from "../../types";
import { useChapterAudio } from "../../hooks/useChapterAudio";

// Step 9: 新しいフックとモーダルのインポート
import { useIndexedDbAutosave } from "../../hooks/useIndexedDbAutosave";
import { useCrashRecovery } from "../../hooks/useCrashRecovery";
import { RecoveryModal } from "./RecoveryModal";

// 提案3: 巨大コンポーネント分割（Gutter / Preview / AudioSection）
import { EditorGutter } from "./EditorGutter";
import { EditorPreview } from "./EditorPreview";
import { EditorAudioSection } from "./EditorAudioSection";

import { findNearestImageMarker } from "../../utils/multimedia";

interface EditorProps {
   content: string;
   onChange: (value: string) => void;
   readOnly?: boolean;
   genre?: string;
   onToast?: (msg: string, type: "success" | "error" | "info") => void;
   onCreateBranch?: () => void;
   onSceneChange?: (sceneName: string | null) => void;
}

export const Editor: React.FC<EditorProps> = ({
   content,
   onChange,
   readOnly = false,
   genre = "ハイファンタジー (R15)",
   onToast,
   onCreateBranch,
   onSceneChange,
 }) => {
   const {
     activeHighlight,
     setActiveHighlight,
     selectedBookId,
     currentEpNum,
     character,
     hoveredNodeSummary,
     setHoveredNodeSummary,
     lineScores,
     setLineScores,
     contentLengthLimit
   } = useNovelContext();
   const [tab, setTab] = useState<"edit" | "preview">("edit");
   const [selectedText, setSelectedText] = useState("");
   const [selectionRange, setSelectionRange] = useState<{ start: number; end: number } | null>(null);
   const [isHistoryDrawerOpen, setIsHistoryDrawerOpen] = useState(false);
   const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(null);
   const [isZenMode, setIsZenMode] = useState(false);
   const [fontFamily, setFontFamily] = useState<EditorFontFamily>("serif");
   const [fontSize, setFontSize] = useState<EditorFontSize>("medium");
   const { past, future, present, pushState, undo, redo, canUndo, canRedo } = useHistoryStack();
   const gutterInnerRef = useRef<HTMLDivElement>(null);
   const { snapshots, takeSnapshot, restoreSnapshot } = useSnapshotHistory(
     selectedBookId,
     currentEpNum
   );
   const { audioTrack, synthesizing: isSynthesizingAudio, synthesize: triggerSynthesizeAudio } = useChapterAudio(
     selectedBookId,
     currentEpNum
   );
   const textareaRef = useRef<HTMLTextAreaElement>(null);
   const mirrorRef = useRef<HTMLDivElement>(null);
   const [tooltipPos, setTooltipPos] = useState<{ top: number; left: number } | null>(null);

   const handleSynthesizeAudio = async () => {
     if (!content.trim()) {
       onToast?.("⚠️ 本文が入力されていません", "error");
       return;
     }
     onToast?.("🎙️ 音声合成を開始しました...", "info");
     const res = await triggerSynthesizeAudio(content);
     if (res) {
       onToast?.("✨ 音声合成が完了しました！", "success");
     } else {
       onToast?.("❌ 音声合成に失敗しました", "error");
     }
   };

// Autosave hook - Step 9: 使用 useIndexedDbAutosave
    const { status, lastSavedAt, save: triggerSave } = useIndexedDbAutosave(selectedBookId, currentEpNum, content);

   // Step 9: クラッシュリカバリフック
    const { isOpen, recoverySnapshot, dismiss } = useCrashRecovery(selectedBookId, currentEpNum, content);

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

   const handleScroll = (e: React.UIEvent<HTMLTextAreaElement>) => {
     const scrollTop = e.currentTarget.scrollTop;
     if (mirrorRef.current) {
       mirrorRef.current.scrollTop = scrollTop;
       mirrorRef.current.scrollLeft = e.currentTarget.scrollLeft;
     }
     if (gutterInnerRef.current) {
       gutterInnerRef.current.style.transform = `translateY(-${scrollTop}px)`;
     }

     // Step 8: Sync scene preview with scroll position
     if (onSceneChange) {
       const lineHeight = 24; // Approximate line height in px
       const firstVisibleLine = Math.floor(scrollTop / lineHeight);
       const lines = content.split('\n');
       let charPos = 0;
       for (let i = 0; i < firstVisibleLine && i < lines.length; i++) {
         charPos += (lines[i]?.length || 0) + 1;
       }
       
       // Use the start of the first visible line as the reference position
       const nearest = findNearestImageMarker(content, charPos);
       onSceneChange(nearest ? (nearest as any).sceneName : null);
     }
   };

   const handleGutterClick = (e: React.MouseEvent<HTMLDivElement>) => {
     const gutterRect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
     const lineHeight = 24; // must match the line-height in px (font-size * line-height)
     const lineNumber = Math.floor((e.clientY - gutterRect.top) / lineHeight);
     if (lineNumber < 0) return;
     const lines = content.split('\n');
     let lineStart = 0;
     for (let i = 0; i < lineNumber; i++) {
       if (i >= lines.length) break;
       lineStart += (lines[i]?.length || 0) + 1; // +1 for newline
     }
     setSelectionRange({ start: lineStart, end: lineStart });
     // Move viewport to the line and set cursor position
     if (textareaRef.current) {
       textareaRef.current.focus();
       textareaRef.current.setSelectionRange(lineStart, lineStart);
       textareaRef.current.scrollTop = lineNumber * lineHeight;
     }
   };

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
       pushState(content);
       takeSnapshot("復元直前", content, "manual");
       onChange(restoredText);
       const snapshot = snapshots.find((s) => s.id === snapshotId);
       const timeStr = snapshot ? new Date(snapshot.timestamp).toLocaleTimeString() : "";
       onToast?.(`✨ ${timeStr}のバージョンに復元しました`, "success");
     }
     setIsHistoryDrawerOpen(false);
   };

   // ルビ変換・ハイライトレンダリングは EditorPreview.tsx に移動（提案3）

   const updateCurrentScene = useCallback(() => {
     if (!textareaRef.current || !onSceneChange) return;
     const position = textareaRef.current.selectionStart;
     const nearest = findNearestImageMarker(content, position);
     onSceneChange(nearest ? (nearest as any).sceneName : null);
   }, [content, onSceneChange]);

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
     updateCurrentScene();
   };

   const handleApplyResult = (newText: string, mode: "replace" | "append") => {
     if (!selectionRange) {
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
     onToast?.("📖 ルビ記法（｜親文字《ルビ」）を挿入しました", "info");

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
      if (!branchName) return;
      try {
        const response = await fetch(`/api/branches/${selectedBookId}/fork`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            parent_id: 1,
            name: branchName,
            fork_ep_num: currentEpNum,
          }),
        });
        if (!response.ok) throw new Error(`Failed to create branch: ${response.status}`);
        const result = await response.json();
        onToast?.(`✨ IFルート「${branchName}」を作成しました`, "success");
        onCreateBranch?.();
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        onToast?.(`❌ エラー: ${msg}`, "error");
      }
    };

   // キーボードショートカット
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
     } else if ((e.ctrlKey || e.metaKey) && e.key === "s") {
       e.preventDefault();
       triggerSave();
       onToast?.("💾 手動保存しました", "success");
     } else if (e.key === "Escape" && isZenMode) {
       setIsZenMode(false);
     }
   };

   const charCount = content.replace(/\s/g, "").length;
   const lineCount = content ? content.split("\n").length : 0;
   const manuscriptPages = Math.ceil(charCount / 400);
   const readingTimeMin = Math.ceil(charCount / 400);
   // 提案5: 文字数上限（contentLengthLimit）に対する進捗率と警告レベル
   const charLimitRatio = contentLengthLimit > 0 ? charCount / contentLengthLimit : 0;
   const charLimitLevel =
     charLimitRatio >= 1 ? "exceeded" : charLimitRatio >= 0.9 ? "warning" : "normal";
   const charLimitColor =
     charLimitLevel === "exceeded"
       ? "var(--accent-danger)"
       : charLimitLevel === "warning"
         ? "var(--accent-yellow)"
         : "var(--text-muted)";

   const editorClassName = [
     "textarea",
     fontFamily === "serif" ? "font-serif" : "font-sans",
     `editor-font-size-${fontSize}`,
     "editor-line-height",
   ].join(" ");

   // Zenモード用オーバーレイ
   if (isZenMode) {
     return (
       <div className="zen-mode-overlay">
         <div className="zen-mode-container">
           <div className="zen-mode__header">
             <span className="zen-mode__title">{genre}</span>
             <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
               <AutosaveIndicator status={status} lastSavedAt={lastSavedAt} />
               <span className="zen-mode__manuscript">📄 約{manuscriptPages}枚</span>
               <button
                 type="button"
                 className="zen-mode__exit"
                 onClick={() => setIsZenMode(false)}
                 aria-label="Zenモードを終了"
               >
                 Zenモード終了 (Esc)
               </button>
             </div>
           </div>
           <textarea
             ref={textareaRef}
             className={editorClassName}
             style={{ flex: 1, minHeight: "0", fontFamily: "inherit", resize: "none", lineHeight: "1.9", outline: "none" }}
             value={content}
             onChange={(e) => onChange(e.target.value)}
             onSelect={handleSelect}
             onKeyDown={handleKeyDown}
             readOnly={readOnly}
             placeholder="ここに本文を入力してください..."
             data-testid="editor-textarea-zen"
           />
         </div>
       </div>
     );
   }

   // ハイライト・ルビ変換レンダリングは EditorPreview.tsx に移動（提案3）

   return (
     <>
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
           </div>

           {/* EditorToolbar */}
           <EditorToolbar
             fontFamily={fontFamily}
             onFontFamilyChange={setFontFamily}
             fontSize={fontSize}
             onFontSizeChange={setFontSize}
             onZenModeToggle={() => setIsZenMode(true)}
             isZenMode={isZenMode}
             manuscriptPages={manuscriptPages}
             onSynthesizeAudio={handleSynthesizeAudio}
             isSynthesizingAudio={isSynthesizingAudio}
           />
         </div>

         <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
           <span>行数: <strong>{lineCount}</strong> 行</span>
           <span>
             文字数: <strong data-testid="editor-char-count" style={{ color: charLimitColor }}>{charCount}</strong>
             / {contentLengthLimit} 文字
             {charLimitLevel === "exceeded" && (
               <span style={{ color: "var(--accent-danger)", marginLeft: "4px" }}>（上限超過）</span>
             )}
             {charLimitLevel === "warning" && (
               <span style={{ color: "var(--accent-yellow)", marginLeft: "4px" }}>（まもなく上限）</span>
             )}
           </span>
           <span>読了目安: <strong>約{readingTimeMin || 1}</strong> 分</span>
           <span>原稿用紙: <strong>約{manuscriptPages}</strong> 枚</span>
           <AutosaveIndicator status={status} lastSavedAt={lastSavedAt} />
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
               <button
                 type="button"
                 style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
                 onClick={() => setActiveHighlight(null)}
               >
                 ✕
               </button>
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
             {...(onToast ? { onToast } : {})}
           />
         )}

         {tab === "edit" ? (
           <div style={{ position: "relative", flex: 1, minHeight: "280px" }}>
             {/* 行番号ガター（EditorGutter に分割） */}
             <EditorGutter
               content={content}
               lineScores={lineScores}
               gutterInnerRef={gutterInnerRef}
               onGutterClick={handleGutterClick}
             />
             <textarea
               id="editor-textarea"
               ref={textareaRef}
               className={editorClassName}
               style={{
                 width: "100%",
                 height: "100%",
                 minHeight: "280px",
                 fontFamily: "inherit",
                 resize: "vertical",
                 lineHeight: "1.9",
                 position: "relative",
                 zIndex: 1,
                 backgroundColor: "transparent",
                 color: "transparent",
                 caretColor: "var(--text-primary, #fff)",
                 padding: "12px 12px 12px 40px", // left padding for gutter
                 boxSizing: "border-box",
               }}
               value={content}
               onChange={(e) => onChange(e.target.value)}
               onSelect={handleSelect}
               onKeyDown={handleKeyDown}
               onScroll={handleScroll}
               onKeyUp={updateCurrentScene}
               onMouseDown={updateCurrentScene}
               readOnly={readOnly}
               placeholder="ここに本文を入力してください。文章を選択するとインラインAI推敲ツールバーが表示されます。"
               data-testid="editor-textarea"
             />
             {/* ハイライトミラー（EditorPreview に分割） */}
             <EditorPreview
               mode="mirror"
               content={content}
               editorClassName={editorClassName}
               mirrorRef={mirrorRef}
             />
           </div>
         ) : (
           // ルビ・プレビュー（EditorPreview に分割）
           <EditorPreview mode="ruby" content={content} />
         )}

         {/* Step 33: インライン音声プレイヤー（EditorAudioSection に分割） */}
         <EditorAudioSection
           audioTrack={audioTrack}
           currentEpNum={currentEpNum}
         />

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
{hoveredNodeSummary && tooltipPos && (
          <SnippetTooltip
            summary={hoveredNodeSummary.summary}
            properties={hoveredNodeSummary.properties}
            position={tooltipPos}
          />
        )}
        {/* Step 9: クラッシュ復旧モーダル */}
        {isOpen && (
          <RecoveryModal
            isOpen={isOpen}
            snapshot={recoverySnapshot}
            onRestore={(recovered) => {
              onChange(recovered);
              dismiss();
            }}
            onDiscard={dismiss}
          />
        )}
      </>
    );
};