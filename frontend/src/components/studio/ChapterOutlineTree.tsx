import React, { useState } from "react";
import { useNovelContext } from "../../context/NovelContext";
import { ChapterItem } from "../../types";

interface ChapterOutlineTreeProps {
  onSelectChapter?: (epNum: number) => void;
}

export const ChapterOutlineTree: React.FC<ChapterOutlineTreeProps> = ({ onSelectChapter }) => {
  const { chapters, setChapters, currentEpNum, setCurrentEpNum } = useNovelContext();
  const [editingEpNum, setEditingEpNum] = useState<number | null>(null);
  const [editingTitle, setEditingTitle] = useState("");

  const handleSelect = (epNum: number) => {
    setCurrentEpNum(epNum);
    onSelectChapter?.(epNum);
  };

  const handleAddChapter = () => {
    const nextEpNum = chapters.length > 0 ? Math.max(...chapters.map((c) => c.ep_num)) + 1 : 1;
    const newChapter: ChapterItem = {
      ep_num: nextEpNum,
      title: `第${nextEpNum}話 新たな展開`,
      summary: "プロット目標を設定してください",
      content: `【第${nextEpNum}話】\n\n`,
      is_catharsis: false,
      status: "draft",
    };
    setChapters((prev) => [...prev, newChapter]);
    setCurrentEpNum(nextEpNum);
  };

  const handleStartEdit = (ch: ChapterItem, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingEpNum(ch.ep_num);
    setEditingTitle(ch.title);
  };

  const handleSaveTitle = (epNum: number, e?: React.FormEvent) => {
    e?.preventDefault();
    if (editingTitle.trim()) {
      setChapters((prev) =>
        prev.map((c) => (c.ep_num === epNum ? { ...c, title: editingTitle.trim() } : c))
      );
    }
    setEditingEpNum(null);
  };

  const handleDeleteChapter = (epNum: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (chapters.length <= 1) return;
    const nextChapters = chapters.filter((c) => c.ep_num !== epNum);
    setChapters(nextChapters);
    if (currentEpNum === epNum && nextChapters.length > 0) {
      setCurrentEpNum(nextChapters[0].ep_num);
    }
  };

  const handleToggleCatharsis = (epNum: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setChapters((prev) =>
      prev.map((c) => (c.ep_num === epNum ? { ...c, is_catharsis: !c.is_catharsis } : c))
    );
  };

  const activeChapter = chapters.find((c) => c.ep_num === currentEpNum);

  return (
    <div className="chapter-outline-tree" data-testid="chapter-outline-tree" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ fontSize: "0.95rem", color: "var(--accent-cyan)", fontWeight: 700, margin: 0 }}>
          📑 章・プロット一覧 ({chapters.length}話)
        </h3>
        <button
          type="button"
          className="inline-ai-btn"
          style={{ padding: "3px 8px", fontSize: "0.75rem" }}
          onClick={handleAddChapter}
          title="次の章を追加"
          data-testid="btn-add-chapter"
        >
          ➕ 章追加
        </button>
      </div>

      {/* 現在執筆中の章のプロット目標カード */}
      {activeChapter && (
        <div
          style={{
            background: "rgba(56, 189, 248, 0.08)",
            border: "1px solid rgba(56, 189, 248, 0.25)",
            borderRadius: "6px",
            padding: "8px 10px",
            fontSize: "0.78rem",
            lineHeight: "1.4",
          }}
          data-testid="active-chapter-goal"
        >
          <div style={{ fontWeight: 700, color: "var(--accent-secondary, #38bdf8)", marginBottom: "2px" }}>
            🎯 執筆中: {activeChapter.title}
            {activeChapter.is_catharsis && <span style={{ marginLeft: "6px", color: "#fbbf24" }}>⭐ カタルシス</span>}
          </div>
          <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
            {activeChapter.summary || "サマリー未設定"}
          </div>
        </div>
      )}

      {/* 章リスト */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "6px",
          maxHeight: "260px",
          overflowY: "auto",
          paddingRight: "2px",
        }}
      >
        {chapters.map((ch) => {
          const isActive = ch.ep_num === currentEpNum;
          const isEditing = editingEpNum === ch.ep_num;

          return (
            <div
              key={ch.ep_num}
              onClick={() => handleSelect(ch.ep_num)}
              style={{
                background: isActive ? "rgba(139, 92, 246, 0.25)" : "rgba(255, 255, 255, 0.03)",
                border: `1px solid ${isActive ? "var(--accent-purple, #8b5cf6)" : "rgba(255, 255, 255, 0.08)"}`,
                borderRadius: "6px",
                padding: "8px 10px",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              data-testid={`chapter-item-${ch.ep_num}`}
            >
              {isEditing ? (
                <form
                  onSubmit={(e) => handleSaveTitle(ch.ep_num, e)}
                  style={{ display: "flex", gap: "4px", alignItems: "center" }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <input
                    className="input"
                    style={{ padding: "3px 6px", fontSize: "0.78rem", flex: 1 }}
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    autoFocus
                    onBlur={() => handleSaveTitle(ch.ep_num)}
                    data-testid="input-edit-chapter-title"
                  />
                  <button type="submit" className="inline-ai-btn" style={{ padding: "2px 6px", fontSize: "0.7rem" }}>
                    ✓
                  </button>
                </form>
              ) : (
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontWeight: isActive ? 700 : 500, fontSize: "0.82rem", color: isActive ? "#f3f4f6" : "var(--text-muted)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {ch.title}
                  </span>
                  <div style={{ display: "flex", gap: "4px", alignItems: "center", marginLeft: "4px" }}>
                    <button
                      type="button"
                      style={{ background: "transparent", border: "none", color: ch.is_catharsis ? "#fbbf24" : "var(--text-muted)", cursor: "pointer", fontSize: "0.75rem", padding: "1px 3px" }}
                      onClick={(e) => handleToggleCatharsis(ch.ep_num, e)}
                      title={ch.is_catharsis ? "カタルシス解除" : "カタルシス回に設定"}
                    >
                      {ch.is_catharsis ? "⭐" : "☆"}
                    </button>
                    <button
                      type="button"
                      style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: "0.75rem", padding: "1px 3px" }}
                      onClick={(e) => handleStartEdit(ch, e)}
                      title="タイトル編集"
                      data-testid={`btn-edit-title-${ch.ep_num}`}
                    >
                      ✏️
                    </button>
                    {chapters.length > 1 && (
                      <button
                        type="button"
                        style={{ background: "transparent", border: "none", color: "rgba(239, 68, 68, 0.7)", cursor: "pointer", fontSize: "0.75rem", padding: "1px 3px" }}
                        onClick={(e) => handleDeleteChapter(ch.ep_num, e)}
                        title="章を削除"
                        data-testid={`btn-delete-chapter-${ch.ep_num}`}
                      >
                        🗑️
                      </button>
                    )}
                  </div>
                </div>
              )}

              {ch.summary && (
                <div
                  style={{
                    fontSize: "0.72rem",
                    color: "var(--text-muted)",
                    marginTop: "2px",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {ch.summary}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

