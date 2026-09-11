import { ChapterItem } from "../types";

export const reorderChapters = (chapters: ChapterItem[], fromIndex: number, toIndex: number): ChapterItem[] => {
  if (fromIndex < 0 || fromIndex >= chapters.length || toIndex < 0 || toIndex >= chapters.length) {
    return chapters;
  }
  const reordered = [...chapters];
const movedArray = reordered.splice(fromIndex, 1);
   const moved = movedArray[0];
   if (!moved) return chapters; // Should not happen due to earlier bounds check
   reordered.splice(toIndex, 0, moved);

  // Update ep_num and title
  return reordered.map((chapter, index) => {
    const epNum = index + 1;
    return {
      ...chapter,
      ep_num: epNum,
      title: `第${epNum}話: ${chapter.title.replace(/^第\d+話[:：]?/, "")}`,
    };
  });
};