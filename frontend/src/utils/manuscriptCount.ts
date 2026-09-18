import { ManuscriptCountResult, ManuscriptTargetPreset } from '../types/manuscript';

// ルビタグ除去: <ruby>漢字<rt>よみ</rt></ruby> → "漢字"
const RUBY_TAG_REGEX = /<ruby>([^<]+)<rt>[^<]+<\/rt><\/ruby>/g;
// 媒介記号除去: 《》《〈〉》等
const MEDIAL_REGEX = /[《》〈〉「」『』【】〔〕]/g;

export function countManuscript(htmlOrText: string): ManuscriptCountResult {
// DEBUG: log for specific input
  if (htmlOrText.includes('<ruby>猫<rt>ねこ</rt></ruby>')) {
    console.log('Input:', htmlOrText);
    const afterRubyReplace = htmlOrText.replace(RUBY_TAG_REGEX, '$1');
    console.log('After ruby replace (base):', afterRubyReplace);
    const afterTagReplace = afterRubyReplace.replace(/<[^>]+>/g, '');
    console.log('After tag replace:', afterTagReplace);
    const afterMedialReplace = afterTagReplace.replace(MEDIAL_REGEX, '');
    console.log('After medial replace:', afterMedialReplace);
    const afterWhitespaceReplace = afterMedialReplace.replace(/\s+/g, '');
    console.log('After whitespace replace:', afterWhitespaceReplace);
    console.log('Body length:', afterWhitespaceReplace.length);
    // Log char codes for body
    const bodyChars = [...afterWhitespaceReplace];
    bodyChars.forEach((ch, idx) => {
      console.log(`${idx}: '${ch}' (${ch.charCodeAt(0)})`);
    });
    
    // withRuby
    const withRubyReplace = htmlOrText.replace(/<ruby>([^<]+)<rt>([^<]+)<\/rt><\/ruby>/g, '$1($2)');
    console.log('WithRuby replace:', withRubyReplace);
    const withRubyAfterTag = withRubyReplace.replace(/<[^>]+>/g, '');
    console.log('WithRuby after tag replace:', withRubyAfterTag);
    const withRubyAfterWhitespace = withRubyAfterTag.replace(/\s+/g, '');
    console.log('WithRuby after whitespace replace:', withRubyAfterWhitespace);
    console.log('WithRuby length:', withRubyAfterWhitespace.length);
    // Log char codes for withRuby
    const wChars = [...withRubyAfterWhitespace];
    wChars.forEach((ch, idx) => {
      console.log(`${idx}: '${ch}' (${ch.charCodeAt(0)})`);
    });
  }

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
  return {
    ratio: Number(ratio.toFixed(2)),
    isOver: result.body > preset.targetChars,
    isWarning: ratio >= preset.warningThreshold && !preset.maxPages,
    isMaxOver: preset.maxPages ? result.pages > preset.maxPages : false,
    remainingChars: Math.max(0, preset.targetChars - result.body),
  };
}