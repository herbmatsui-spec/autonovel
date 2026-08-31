import React from "react";
import { useNovelContext } from "../../context/NovelContext";

export const Sidebar: React.FC = () => {
  const { character, setCharacter, selectedBookId, setSelectedBookId } = useNovelContext();

  return (
    <aside className="card" style={{ height: "fit-content" }}>
      <h2 style={{ fontSize: "1.1rem", marginBottom: "14px", color: "var(--accent-primary)" }}>
        📜 作品・主人公プロファイル
      </h2>

      <div className="form-group">
        <label className="label">作品 ID (Book ID)</label>
        <input
          className="input"
          type="number"
          min={1}
          value={selectedBookId}
          onChange={(e) => setSelectedBookId(Number(e.target.value) || 1)}
        />
      </div>

      <div className="form-group">
        <label className="label">作品ジャンル</label>
        <select
          className="select"
          value={character.genre}
          onChange={(e) => setCharacter((prev) => ({ ...prev, genre: e.target.value }))}
        >
          <option value="ハイファンタジー (R15)">ハイファンタジー (R15)</option>
          <option value="ダークファンタジー (R15)">ダークファンタジー (R15)</option>
          <option value="異世界転生・バトル (R15)">異世界転生・バトル (R15)</option>
          <option value="SF・サイバーパンク (R15)">SF・サイバーパンク (R15)</option>
        </select>
      </div>

      <div className="form-group">
        <label className="label">主人公の名前</label>
        <input
          className="input"
          value={character.name}
          onChange={(e) => setCharacter((prev) => ({ ...prev, name: e.target.value }))}
        />
      </div>

      <div className="form-group">
        <label className="label">性格・行動指針</label>
        <input
          className="input"
          value={character.personality}
          onChange={(e) => setCharacter((prev) => ({ ...prev, personality: e.target.value }))}
        />
      </div>

      <div className="form-group">
        <label className="label">能力・固有スキル</label>
        <input
          className="input"
          value={character.ability}
          onChange={(e) => setCharacter((prev) => ({ ...prev, ability: e.target.value }))}
        />
      </div>
    </aside>
  );
};
