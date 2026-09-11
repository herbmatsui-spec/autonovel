import React, { useState } from "react";
import { useNovelContext } from "../context/NovelContext";
import { useNovelExport } from "../hooks/useNovelExport";
import { Editor } from "./editor/Editor";
import { AiSuggestions } from "./editor/AiSuggestions";
import { promoteToStudio } from "../api/easyMode";
import { BookItem } from "../types";
import { BookShowcaseModal } from "./showcase/BookShowcaseModal";

interface ExportPanelProps {
  output?: string;
  suggestions?: string[];
  onExportMessage?: (message: string) => void;
  onPromoteToStudio?: () => void;
}

export default function ExportPanel({
  output,
  suggestions,
  onExportMessage,
  onPromoteToStudio,
}: ExportPanelProps) {
  const {
    character,
    selectedBookId,
    setSelectedBookId,
    selectedBook,
    currentChapterText,
    setCurrentChapterText,
    generationState,
    applySuggestion,
    syncGenerationToEditor,
  } = useNovelContext();

const [validationError, setValidationError] = useState("");
   const [promoting, setPromoting] = useState(false);
   const [showBookShowcase, setShowBookShowcase] = useState(false);

   const { exporting, downloadExportPackage } = useNovelExport(
    (msg) => onExportMessage?.(msg),
    (errMsg) => onExportMessage?.(errMsg)
  );

  // 単一本文ソース化: 編集対象は currentChapterText に統一
  const displayOutput = output !== undefined ? output : currentChapterText;
  const displaySuggestions = suggestions !== undefined ? suggestions : generationState.suggestions;

  const validateAndExport = async () => {
    if (!selectedBook) {
      setValidationError("作品が選択されていません");
      return;
    }
    setValidationError("");
    await downloadExportPackage(selectedBook.id, {
      title: selectedBook.title,
      genre: character.genre,
      current_text: displayOutput,
      character: character,
    });
  };

  const handlePromote = async () => {
    setPromoting(true);
    try {
      // 画面の最新テキストをエディタ本文にも同期
      syncGenerationToEditor(displayOutput);
      const res = await promoteToStudio({ book_id: selectedBookId.toString() });
      if (res.success) {
        onExportMessage?.("✨ 上級者 Studio へ昇格しました！世界観設定がナレッジグラフに統合されました。");
        // redirect_url を URL バーに反映 (将来 router 追加時のフックポイント)
        const target = `${res.redirect_url}?token=${encodeURIComponent(res.state_token)}`;
        if (typeof window !== "undefined" && window.history?.pushState) {
          window.history.pushState({ bookId: selectedBookId, token: res.state_token }, "", target);
          window.dispatchEvent(new PopStateEvent("popstate"));
        }
        onPromoteToStudio?.();
      }
    } catch (err: any) {
      onExportMessage?.(`❌ 昇格エラー: ${err.message || err}`);
    } finally {
      setPromoting(false);
    }
  };

const handleShowBookShowcase = () => {
     if (!selectedBook) {
       onExportMessage?.("作品が選択されていません");
       return;
     }
     setShowBookShowcase(true);
   };


return (
    <section className="card" style={{ display: "flex", flexDirection: "column" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
        }}
      >
        <h2 style={{ fontSize: "1.2rem", color: "var(--accent-secondary, #38bdf8)" }}>
          📖 執筆プレビュー & エディタ
        </h2>
      </div>

      {selectedBook ? (
        <div
          className="export-panel__book-badge"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "12px",
            padding: "12px 16px",
            backgroundColor: "var(--bg-card, #18181b)",
            border: "1px solid var(--border-color, #27272a)",
            borderRadius: "12px",
            marginBottom: "16px",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "1.25rem", fontWeight: 600, color: "var(--text-main)" }}>
                {selectedBook.title}
              </span>
              <span
                style={{
                  fontSize: "0.7rem",
                  padding: "2px 8px",
                  borderRadius: "9999px",
                  backgroundColor: "var(--accent-primary, #a78bfa)",
                  color: "white",
                  fontWeight: 600,
                }}
              >
                ID: {selectedBook.id}
              </span>
            </div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              ジャンル: {selectedBook.genre} | 目標: {selectedBook.target_eps}話 | 作成: {new Date(selectedBook.created_at).toLocaleDateString("ja-JP")}
            </div>
          </div>
        </div>
      ) : (
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            padding: "12px 16px",
            backgroundColor: "var(--bg-card, #18181b)",
            border: "1px dashed var(--border-color, #27272a)",
            borderRadius: "12px",
            marginBottom: "16px",
            color: "var(--text-muted)",
          }}
        >
          ⚠️ 作品が選択されていません。ヘッダーの「本棚」から作品を選択または作成してください。
        </div>
      )}

<div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
         <button
           type="button"
           className="btn btn-export"
           style={{ flex: 1 }}
           onClick={validateAndExport}
           disabled={exporting || !selectedBook}
           data-testid="btn-export-zip"
         >
           {exporting ? "📦 パッケージ生成中..." : "📦 納品パッケージ (ZIP) ダウンロード"}
         </button>

         <button
           type="button"
           className="btn btn-primary"
           style={{ padding: "8px 14px", fontSize: "0.85rem", whiteSpace: "nowrap", marginLeft: "8px" }}
           onClick={handleShowBookShowcase}
           disabled={!selectedBook}
           title="縦書き装丁プレビューと宣伝カードを表示"
           data-testid="btn-show-book-showcase"
         >
           📖 縦書き装丁プレビュー & 宣伝カード
         </button>

         <button
           type="button"
           className="btn btn-primary"
           style={{ padding: "8px 14px", fontSize: "0.85rem", whiteSpace: "nowrap" }}
           onClick={handlePromote}
           disabled={promoting}
           title="設定をGraphRAGナレッジ化し、Studioモードへ引き継ぎます"
           data-testid="btn-promote-studio"
         >
           {promoting ? "⏳ 昇格中..." : "🚀 Studioへ昇格"}
         </button>
       </div>

      <div style={{ flex: 1, minHeight: "240px" }}>
        <Editor
          content={displayOutput}
          onChange={setCurrentChapterText}
        />
      </div>

<AiSuggestions
         suggestions={displaySuggestions}
         onApplySuggestion={applySuggestion}
       />
       
{/* 書籍ショーケースモーダル */}
        {showBookShowcase && selectedBook && (
          <BookShowcaseModal
            onClose={() => setShowBookShowcase(false)}
            bookData={{
              title: selectedBook.title,
              author: character.name || "不明な作者",
              content: displayOutput
            }}
          />
        )}
     </section>
   );
 }
