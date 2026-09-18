import { ManuscriptTargetPreset } from '../types/manuscript';

export const MANUSCRIPT_PRESETS: ManuscriptTargetPreset[] = [
  {
    id: 'shousetsu-gekkan',
    label: '小説現代・新人賞 (400字×30枚)',
    targetPages: 30,
    targetChars: 12000,
    warningThreshold: 0.9,
  },
  {
    id: 'shousetsu-subaru',
    label: '小説すばる・新人賞 (400字×50枚)',
    targetPages: 50,
    targetChars: 20000,
    warningThreshold: 0.9,
  },
  {
    id: 'dengeki-bunko',
    label: '電撃文庫・大賞 (400字×100枚)',
    targetPages: 100,
    targetChars: 40000,
    warningThreshold: 0.85,
    maxPages: 100,
  },
  {
    id: 'kakuyomu',
    label: 'カクヨム・コンテスト (10万字以内)',
    targetPages: 250,
    targetChars: 100000,
    warningThreshold: 0.9,
    maxPages: 250,
  },
  {
    id: 'narou',
    label: '小説家になろう・長編 (文字数自由)',
    targetPages: 0,
    targetChars: 0,
    warningThreshold: 1,
  },
  {
    id: 'custom',
    label: 'カスタム設定…',
    targetPages: 0,
    targetChars: 0,
    warningThreshold: 0.9,
  },
];
