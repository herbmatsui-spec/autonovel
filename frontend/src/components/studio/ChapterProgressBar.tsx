import React from "react";
import { useNovelContext } from "../../context/NovelContext";

export const ChapterProgressBar: React.FC = () => {
  const {
    chapters,
    targetEpisodes,
    contentLengthLimit,
  } = useNovelContext();

  const totalTargetChars = targetEpisodes * contentLengthLimit;
  const totalWrittenChars = chapters.reduce((sum, chapter) => {
    return sum + (chapter.content?.length ?? 0);
  }, 0);
  const completedChapters = chapters.filter(
    (chapter) => chapter.status === "completed"
  ).length;
  const progressPercent =
    totalTargetChars > 0 ? (totalWrittenChars / totalTargetChars) * 100 : 0;

  return (
    <div style={{ marginBottom: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
        <span>
          📊 全 {targetEpisodes} 話中 {completedChapters} 話脱稿
        </span>
        <span>
          総文字数 {totalWrittenChars.toLocaleString()} 字
        </span>
      </div>
      <div>
        <span>
          (目標 {totalTargetChars.toLocaleString()} 字 -
          {progressPercent.toFixed(1)}%)
        </span>
      </div>
      <div
        style={{
          height: "8px",
          backgroundColor: "var(--bg-input)",
          borderRadius: "4px",
          overflow: "hidden",
          marginTop: "8px",
        }}
      >
        <div
          style={{
            width: `${progressPercent}%`,
            height: "100%",
            backgroundImage:
              "linear-gradient(90deg, #38bdf8, #8b5cf6)",
            transition: "width 0.3s ease",
          }}
        ></div>
      </div>
    </div>
  );
};