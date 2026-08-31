import React, { useState } from "react";
import { useNovelContext } from "../context/NovelContext";
import { useNovelExport } from "../hooks/useNovelExport";
import { Editor } from "./editor/Editor";
import { AiSuggestions } from "./editor/AiSuggestions";

interface ExportPanelProps {
  output?: string;
  suggestions?: string[];
  onExportMessage?: (message: string) => void;
}

export default function ExportPanel({
  output,
  suggestions,
  onExportMessage,
}: ExportPanelProps) {
  const {
    generationState,
    setGenerationState,
    selectedBookId,
    setSelectedBookId,
    applySuggestion,
  } = useNovelContext();

  const [validationError, setValidationError] = useState("");

  const { exporting, downloadExportPackage } = useNovelExport(
    (msg) => onExportMessage?.(msg),
    (errMsg) => onExportMessage?.(errMsg)
  );

  const displayOutput = output !== undefined ? output : generationState.currentOutput;
  const displaySuggestions = suggestions !== undefined ? suggestions : generationState.suggestions;

  const validateAndExport = async () => {
    if (selectedBookId < 1 || !Number.isInteger(selectedBookId)) {
      setValidationError("1以上の整数を入力してください");
      return;
    }
    setValidationError("");
    await downloadExportPackage(selectedBookId);
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

      <button
        className="btn btn-export"
        style={{ width: "100%", marginBottom: "16px" }}
        onClick={validateAndExport}
        disabled={exporting}
      >
        {exporting ? "📦 パッケージ生成中..." : "📦 納品パッケージ (ZIP) ダウンロード"}
      </button>

      <div style={{ flex: 1, minHeight: "240px" }}>
        <Editor
          content={displayOutput}
          onChange={(val) =>
            setGenerationState((prev) => ({ ...prev, currentOutput: val }))
          }
        />
      </div>

      <AiSuggestions
        suggestions={displaySuggestions}
        onApplySuggestion={applySuggestion}
      />
    </section>
  );
}
