import { ManuscriptCountResult, ManuscriptTargetPreset } from '../types/manuscript';

// ルビタグ除去: <ruby>漢字<rt>よみ</rt></ruby> → "漢字"
const RUBY_TAG_REGEX = /<ruby>([^<]+)<rt>[^<]+<\/rt><\/ruby>/g;
// 媒介記号除去: 《》《〈〉》等
const MEDIAL_REGEX = /[《》〈〉「」『』【】〔〕]/g;

export function countManuscript(htmlOrText: string): ManuscriptCountResult {
  // 1. 本文文字数: HTMLタグ全除去 + 媒介記号除去 + 空白正規化
  const plainText = htmlOrText
    .replace(RUBY_TAG_REGEX, '$1')  // ルビ本体のみ残す
    .replace(/<[^>]+>/g, '')        // 残りタグ除去
    .replace(MEDIAL_REGEX, '')      // 媒介記号除去
    .replace(/\s+/g, '')            // 空白除去
    .length;

  // 2. ルビ込み: HTMLタグ除去のみ (ルビ読み含む)
  const withRubyText = htmlOrText
    .replace(/<ruby>([^<]+)<rt>([^<]+)<\/rt><\/ruby>/g, '$1($2)') // "漢字(よみ)"
    .replace(/<[^>]+>/g, '')
    .replace(/\s+/g, '')
    .length;

  // 3. 出版用: 本文文字数を 400字詰め換算
  const publishingPages = plainText / 400;
  const pages = Math.ceil(publishingPages);
  const lines = Math.ceil(plainText / 40);
  const readingTimeMinutes = Math.ceil(plainText / 400);

  return {
    body: plainText,
    withRuby: withRubyText,
    publishing: Number(publishingPages.toFixed(1)),
    pages,
    lines,
    readingTimeMinutes,
  };
}

// 目標判定
export function checkTarget(result: ManuscriptCountResult, preset: ManuscriptTargetPreset) {
  const ratio = result.body / preset.targetChars;
  const isOver = result.body > preset.targetChars;
  return {
    ratio: Number(ratio.toFixed(2)),
    isOver,
    isWarning: ratio >= preset.warningThreshold && !isOver && !preset.maxPages,
    isMaxOver: preset.maxPages ? result.pages > preset.maxPages : false,
    remainingChars: Math.max(0, preset.targetChars - result.body),
  };
}