import React, { useState } from "react";
import { BeatCard, BranchType } from "../../types/editor";
import { generateNextBeats } from "../../api/editor";

interface NextBeatsPanelProps {
  currentText: string;
  genre?: string;
  bookId?: number;
  onApplyBeat: (content: string, mode: "append" | "replace_all") => void;
  onToast?: (msg: string, type: "success" | "error" | "info") => void;
}

export const NextBeatsPanel: React.FC<NextBeatsPanelProps> = ({
  currentText,
  genre = "ハイファンタジー (R15)",
  bookId = 1,
  onApplyBeat,
  onToast,
}) => {
  const [beats, setBeats] = useState<BeatCard[]>([]);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    if (!currentText.trim()) {
      onToast?.("本文を入力してから次話・展開生成を実行してください", "info");
      return;
    }

    setLoading(true);
    try {
      const res = await generateNextBeats({
        book_id: bookId,
        current_text: currentText,
        genre,
      });
      setBeats(res.beats);
      onToast?.("✨ 3つの展開バリエーションを生成しました", "success");
    } catch (err: any) {
      onToast?.(`❌ 生成エラー: ${err.message || err}`, "error");
    } finally {
      setLoading(false);
    }
  };

  const getBranchBadge = (type: BranchType) => {
    switch (type) {
      case "royal":
        return <span style={{ color: "#38bdf8", fontSize: "0.75rem", fontWeight: 700 }}>⚔️ 王道・カタルシス</span>;
      case "twist":
        return <span style={{ color: "#f43f5e", fontSize: "0.75rem", fontWeight: 700 }}>⚡ サスペンス・急展開</span>;
      case "psychology":
        return <span style={{ color: "#c084fc", fontSize: "0.75rem", fontWeight: 700 }}>💬 心情・掛け合い</span>;
    }
  };

  return (
    <div style={{ marginTop: "24px" }} data-testid="next-beats-panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <div>
          <h3 style={{ fontSize: "1rem", color: "var(--accent-purple)", display: "flex", alignItems: "center", gap: "6px" }}>
            <span>🔀 Next Beats</span>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 400 }}>
              (3つの異なる展開から選ぶ・ブレンドする)
            </span>
          </h3>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          style={{ padding: "6px 14px", fontSize: "0.85rem" }}
          onClick={handleGenerate}
          disabled={loading}
          data-testid="btn-generate-beats"
        >
          {loading ? "⏳ 3分岐生成中..." : "🎲 次の展開を3案生成"}
        </button>
      </div>

      {beats.length > 0 && (
        <div className="beats-container">
          {beats.map((b) => (
            <div
              key={b.card_id}
              className={`beat-card beat-card--${b.branch_type}`}
              data-testid={`beat-card-${b.card_id}`}
            >
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                  {getBranchBadge(b.branch_type)}
                </div>
                <div className="beat-card-title">{b.title}</div>
                <div className="beat-card-summary">{b.summary}</div>
                <div className="beat-card-content">{b.content}</div>
                {b.hook_text && (
                  <div style={{ fontSize: "0.75rem", color: "var(--accent-cyan)", marginBottom: "10px", fontStyle: "italic" }}>
                    🎣 {b.hook_text}
                  </div>
                )}
              </div>

              <div style={{ display: "flex", gap: "6px", marginTop: "8px" }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ flex: 1, padding: "5px 8px", fontSize: "0.8rem" }}
                  onClick={() => {
                    onApplyBeat(b.content, "append");
                    onToast?.(`➕ 「${b.title}」を末尾に追記しました`, "success");
                  }}
                  data-testid={`btn-apply-beat-${b.card_id}`}
                >
                  ➕ 本文に追記
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
