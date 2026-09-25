import { describe, it, expect } from 'vitest';
import { countManuscript, checkTarget, ManuscriptCountResult, ManuscriptTargetPreset } from '@/utils/manuscriptCount.ts';

describe('countManuscript', () => {
  it('プレーンテキスト「あいうえお」 → body=5, withRuby=5, publishing=0.0', () => {
    const result = countManuscript('あいうえお');
    expect(result.body).toBe(5);
    expect(result.withRuby).toBe(5);
    expect(result.publishing).toBe(0.0);
    expect(result.pages).toBe(1);
    expect(result.lines).toBe(1);
    expect(result.readingTimeMinutes).toBe(1);
  });

  it('ルビ付き `<ruby>漢字<rt>かんじ</rt></ruby>` → body=2, withRuby=7', () => {
    const result = countManuscript('<ruby>漢字<rt>かんじ</rt></ruby>');
    expect(result.body).toBe(2);
    expect(result.withRuby).toBe(7);
    expect(result.publishing).toBe(0.0);
    expect(result.pages).toBe(1);
    expect(result.lines).toBe(1);
    expect(result.readingTimeMinutes).toBe(1);
  });

  it('混在: 「吾輩《わがはい》は<ruby>猫<rt>ねこ</rt></ruby>である」 → body=11, withRuby=17', () => {
    const result = countManuscript('吾輩《わがはい》は<ruby>猫<rt>ねこ</rt></ruby>である');
    expect(result.body).toBe(11);
    expect(result.withRuby).toBe(17);
    expect(result.publishing).toBe(0.0);
    expect(result.pages).toBe(1);
    expect(result.lines).toBe(1);
    expect(result.readingTimeMinutes).toBe(1);
  });

  it('改行・空白混在 → 正規化後カウント', () => {
    const result = countManuscript('あ い  うえ   お\n\n');
    expect(result.body).toBe(5);
    expect(result.withRuby).toBe(5);
    expect(result.publishing).toBe(0.0);
    expect(result.pages).toBe(1);
    expect(result.lines).toBe(1);
    expect(result.readingTimeMinutes).toBe(1);
  });

  it('空文字 → 全ゼロ', () => {
    const result = countManuscript('');
    expect(result.body).toBe(0);
    expect(result.withRuby).toBe(0);
    expect(result.publishing).toBe(0);
    expect(result.pages).toBe(0);
    expect(result.lines).toBe(0);
    expect(result.readingTimeMinutes).toBe(0);
  });

  it('400字境界: 399字→1.0ページ, 400字→1.0ページ, 401字→2.0ページ', () => {
    const text399 = 'あ'.repeat(399);
    const result399 = countManuscript(text399);
    expect(result399.body).toBe(399);
    expect(result399.publishing).toBe(1.0);
    expect(result399.pages).toBe(1);
    expect(result399.lines).toBe(10); // ceil(399/40) = 10
    expect(result399.readingTimeMinutes).toBe(1); // ceil(399/400) = 1

    const text400 = 'あ'.repeat(400);
    const result400 = countManuscript(text400);
    expect(result400.body).toBe(400);
    expect(result400.publishing).toBe(1.0);
    expect(result400.pages).toBe(1);
    expect(result400.lines).toBe(10);
    expect(result400.readingTimeMinutes).toBe(1);

    const text401 = 'あ'.repeat(401);
    const result401 = countManuscript(text401);
    expect(result401.body).toBe(401);
    expect(result401.publishing).toBe(1.0);
    expect(result401.pages).toBe(2);
    expect(result401.lines).toBe(11); // ceil(401/40) = 11
    expect(result401.readingTimeMinutes).toBe(2); // ceil(401/400) = 2
  });

  it('目標判定: 12000字目標に 10800字→warning, 12001字→over (warning false when over)', () => {
    const preset: ManuscriptTargetPreset = {
      id: 'test',
      label: 'テスト',
      targetPages: 30,
      targetChars: 12000,
      warningThreshold: 0.9,
    };

    const result10800 = countManuscript('あ'.repeat(10800));
    const check10800 = checkTarget(result10800, preset);
    expect(check10800.ratio).toBe(0.9);
    expect(check10800.isWarning).toBe(true);
    expect(check10800.isOver).toBe(false);
    expect(check10800.isMaxOver).toBe(false);
    expect(check10800.remainingChars).toBe(1200);

    const result12001 = countManuscript('あ'.repeat(12001));
    const check12001 = checkTarget(result12001, preset);
    expect(check12001.ratio).toBe(1);
    expect(check12001.isOver).toBe(true);
    expect(check12001.isWarning).toBe(false); // warning only when not over
    expect(check12001.isMaxOver).toBe(false);
    expect(check12001.remainingChars).toBe(0);
  });
});