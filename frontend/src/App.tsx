import { useState } from "react";
import GeneratePanel from "./components/GeneratePanel";
import ExportPanel from "./components/ExportPanel";

export default function App() {
  const [output, setOutput] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [message, setMessage] = useState("");

  const getToastClass = (msg: string): string => {
    if (msg.startsWith("❌")) return "toast toast--error";
    if (msg.startsWith("✨") || msg.startsWith("📦")) return "toast toast--success";
    return "toast toast--info";
  };

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
        <div className={getToastClass(message)}>
          {message}
        </div>
      )}

      <main className="main-grid">
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
