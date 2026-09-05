import React, { useState } from "react";
import { useNovelContext } from "../context/NovelContext";
import { useNovelExport } from "../hooks/useNovelExport";
import { Editor } from "./editor/Editor";
import { AiSuggestions } from "./editor/AiSuggestions";
import { promoteToStudio } from "../api/easyMode";

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
    currentChapterText,
    setCurrentChapterText,
    generationState,
    applySuggestion,
    syncGenerationToEditor,
  } = useNovelContext();

  const [validationError, setValidationError] = useState("");
  const [promoting, setPromoting] = useState(false);

  const { exporting, downloadExportPackage } = useNovelExport(
    (msg) => onExportMessage?.(msg),
    (errMsg) => onExportMessage?.(errMsg)
  );

  // 単一本文ソース化: 編集対象は currentChapterText に統一
  const displayOutput = output !== undefined ? output : currentChapterText;
  const displaySuggestions = suggestions !== undefined ? suggestions : generationState.suggestions;

  const validateAndExport = async () => {
    if (selectedBookId < 1 || !Number.isInteger(selectedBookId)) {
      setValidationError("1以上の整数を入力してください");
      return;
    }
    setValidationError("");
    await downloadExportPackage(selectedBookId, {
      title: `${character.name}の冒険譚`,
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

      <div className="form-group" style={{ marginBottom: "16px" }}>
        <label className="label">作品 ID (book_id)</label>
        <input
          className="input"
          type="number"
          min={1}
          value={selectedBookId}
          onChange={(e) => {
            const val = Number.parseInt(e.target.value, 10);
            if (val > 0) {
              setSelectedBookId(val);
              setValidationError("");
            } else {
              setValidationError("1以上の整数を入力してください");
            }
          }}
          placeholder="1以上の整数"
        />
        {validationError && (
          <span style={{ color: "var(--accent-danger, #ef4444)", fontSize: "0.85rem" }}>
            {validationError}
          </span>
        )}
      </div>

      <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
        <button
          type="button"
          className="btn btn-export"
          style={{ flex: 1 }}
          onClick={validateAndExport}
          disabled={exporting}
          data-testid="btn-export-zip"
        >
          {exporting ? "📦 パッケージ生成中..." : "📦 納品パッケージ (ZIP) ダウンロード"}
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
    </section>
  );
}
