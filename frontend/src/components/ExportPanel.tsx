import { useState } from "react";
import { exportPackage } from "../api/easyMode";

interface ExportPanelProps {
  output: string;
  suggestions: string[];
  onExportMessage: (message: string) => void;
}

export default function ExportPanel({ output, suggestions, onExportMessage }: ExportPanelProps) {
  const [exporting, setExporting] = useState(false);
  const [bookIdInput, setBookIdInput] = useState("1");
  const [validationError, setValidationError] = useState("");

  const validateBookId = (raw: string): number | null => {
    const trimmed = raw.trim();
    if (!/^[1-9]\d*$/.test(trimmed)) {
      setValidationError("1以上の整数を入力してください");
      return null;
    }
    setValidationError("");
    return Number.parseInt(trimmed, 10);
  };

  const handleExport = async () => {
    const bookId = validateBookId(bookIdInput);
    if (bookId === null) return;

    setExporting(true);
    onExportMessage("");
    try {
      const { zipBlob, filename } = await exportPackage(bookId);
      const url = window.URL.createObjectURL(zipBlob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      onExportMessage(`📦 納品パッケージ (${filename}) をダウンロードしました！`);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "不明なエラーが発生しました";
      onExportMessage(`❌ ダウンロードエラー: ${message}`);
    } finally {
      setExporting(false);
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
        <h2 style={{ fontSize: "1.2rem", color: "#38bdf8" }}>📖 執筆プレビュー</h2>
      </div>

      <div className="form-group" style={{ marginBottom: "16px" }}>
        <label className="label">作品 ID (book_id)</label>
        <input
          className="input"
          type="number"
          min={1}
          value={bookIdInput}
          onChange={(e) => setBookIdInput(e.target.value)}
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
        onClick={handleExport}
        disabled={exporting}
      >
        {exporting ? "📦 パッケージ生成中..." : "📦 納品パッケージ (ZIP) ダウンロード"}
      </button>

      <div className="output-area" style={{ flex: 1 }}>
        {output || "「🪄 かんたん執筆開始」を押すと、AIがファンタジー作品の続きを生成します。"}
      </div>

      {suggestions.length > 0 && (
        <div style={{ marginTop: "16px" }}>
          <span className="label">💡 次話へのAI提案</span>
          <div className="chips">
            {suggestions.map((s, idx) => (
              <span className="chip" key={idx}>
                {s}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
