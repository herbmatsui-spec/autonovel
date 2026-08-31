import { useState } from "react";
import { generateContent, pollGenerationStatus } from "../api/easyMode";

interface GeneratePanelProps {
  onGenerated: (output: string, suggestions: string[]) => void;
  onMessage: (message: string) => void;
}

const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS = 30_000;

export default function GeneratePanel({ onGenerated, onMessage }: GeneratePanelProps) {
  const [genre, setGenre] = useState("ファンタジー (R15)");
  const [characterName, setCharacterName] = useState("アルト");
  const [personality, setPersonality] = useState("熱血・正義感が強い");
  const [ability, setAbility] = useState("古代魔導剣術");
  const [currentChapterText, setCurrentChapterText] = useState(
    "薄暗いダンジョンの中、15歳の青年アルトは古代の剣を手に取った。"
  );
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState("");

  const handleGenerate = async () => {
    setLoading(true);
    onMessage("");
    setStatusText("生成リクエストを送信中...");
    try {
      const response = await generateContent({
        chapter_history: [currentChapterText],
        current_chapter: currentChapterText,
        character_params: { name: characterName, personality, ability, genre },
        content_length_limit: 2000,
      });

      // 非同期タスク ID の取得 (APIレスポンスまたは提案文字列から)
      const taskId =
        response.task_id ||
        response.suggestions
          .join("\n")
          .match(/(?:ステータスを\s*)?\/easy_mode\/status\/([^\s]+)/)?.[1];

      if (taskId) {
        setStatusText("タスクステータスをポーリング中...");
        const result = await pollUntilDone(taskId);
        setStatusText("");
        onGenerated(result.output || "生成が完了しました。", result.suggestions || []);
        onMessage("✨ 本文のAI生成が完了しました。");
      } else {
        // 即時レスポンスの場合
        onGenerated(response.output || "生成が完了しました。", response.suggestions || []);
        onMessage("✨ 本文のAI生成が完了しました。");
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "不明なエラーが発生しました";
      onMessage(`❌ エラー: ${message}`);
      setStatusText("");
    } finally {
      setLoading(false);
    }
  };

  const pollUntilDone = async (taskId: string) => {
    const deadline = Date.now() + POLL_TIMEOUT_MS;
    while (Date.now() < deadline) {
      const status = await pollGenerationStatus(taskId);
      if (status.status === "completed") {
        return normalizeResult(status.result);
      }
      if (status.status === "failed") {
        throw new Error("生成タスクが失敗しました");
      }
      setStatusText(`ステータス: ${status.status}`);
      await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
    }
    throw new Error("生成タイムアウト");
  };

  const normalizeResult = (result: unknown) => {
    if (typeof result === "string") {
      try {
        return JSON.parse(result);
      } catch {
        return { output: result, suggestions: [] as string[] };
      }
    }
    return (result ?? {}) as { output?: string; suggestions?: string[] };
  };

  return (
    <section className="card">
      <h2 style={{ fontSize: "1.2rem", marginBottom: "16px", color: "#a78bfa" }}>
        ⚙️ 制作設定
      </h2>

      <div className="form-group">
        <label className="label">作品ジャンル・レーティング</label>
        <select className="select" value={genre} onChange={(e) => setGenre(e.target.value)}>
          <option value="ファンタジー (R15)">ハイファンタジー (R15)</option>
          <option value="ダークファンタジー (R15)">ダークファンタジー (R15)</option>
          <option value="異世界転生 (R15)">異世界転生・バトル (R15)</option>
        </select>
      </div>

      <div className="form-group">
        <label className="label">主人公の名前</label>
        <input
          className="input"
          value={characterName}
          onChange={(e) => setCharacterName(e.target.value)}
        />
      </div>

      <div className="form-group">
        <label className="label">性格・特徴</label>
        <input
          className="input"
          value={personality}
          onChange={(e) => setPersonality(e.target.value)}
        />
      </div>

      <div className="form-group">
        <label className="label">特殊能力・スキル</label>
        <input
          className="input"
          value={ability}
          onChange={(e) => setAbility(e.target.value)}
        />
      </div>

      <div className="form-group">
        <label className="label">執筆対象の冒頭 / 前話プロンプト</label>
        <textarea
          className="textarea"
          rows={4}
          value={currentChapterText}
          onChange={(e) => setCurrentChapterText(e.target.value)}
        />
      </div>

      {statusText && (
        <div style={{ marginBottom: "12px", fontSize: "0.9rem", color: "var(--text-muted)" }}>
          {statusText}
        </div>
      )}

      <button
        className="btn btn-primary"
        style={{ width: "100%" }}
        onClick={handleGenerate}
        disabled={loading}
      >
        {loading ? "🪄 執筆中..." : "🪄 かんたん執筆開始"}
      </button>
    </section>
  );
}
