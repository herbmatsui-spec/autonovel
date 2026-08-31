import React, { useState } from "react";
import GeneratePanel from "./components/GeneratePanel";
import ExportPanel from "./components/ExportPanel";

export default function App() {
  const [output, setOutput] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [message, setMessage] = useState("");

  return (
    <div className="container">
      <header className="header">
        <div>
          <h1 className="brand-title">AutoNovel かんたん制作</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "4px" }}>
            AIと一緒にR15ファンタジー作品を制作・即座にZIP納品
          </p>
        </div>
        <span className="badge-r15">R15 ファンタジー対応</span>
      </header>

      {message && (
        <div
          style={{
            padding: "12px 16px",
            background: "rgba(139, 92, 246, 0.15)",
            border: "1px solid var(--accent-purple)",
            borderRadius: "var(--radius-md)",
            marginBottom: "20px",
            fontSize: "0.95rem",
          }}
        >
          {message}
        </div>
      )}

      <main style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: "24px" }}>
        <GeneratePanel
          onGenerated={(out, sug) => {
            setOutput(out);
            setSuggestions(sug);
          }}
          onMessage={setMessage}
        />
        <ExportPanel output={output} suggestions={suggestions} onExportMessage={setMessage} />
      </main>
    </div>
  );
}
