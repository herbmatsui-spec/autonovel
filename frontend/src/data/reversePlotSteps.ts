import { ReversePlotStep } from '../types/reversePlot';

export const REVERSE_PLOT_STEPS: ReversePlotStep[] = [
  {
    step: 1,
    title: '最終話で読者に残したい感情',
    question: 'この作品を読み終わった時、読者に何を感じてほしい？',
    options: [
      { label: '爽快感・達成感', value: 'triumph', example: '主人公が最強になって世界を救う' },
      { label: '切なさ・余韻', value: 'bittersweet', example: '大切な人を失うが、希望を残す' },
      { label: '衝撃・どんでん返し', value: 'twist', example: '真犯人は最も信頼していた仲間' },
      { label: '温かさ・癒やし', value: 'heartwarming', example: '傷ついた心が少しずつ癒える' },
    ],
    aiHint: '選択に応じて、ラストシーンのテンプレートと感情ペイオフを自動提案します'
  },
  {
    step: 2,
    title: '主人公が払う最大の代償',
    question: '願いを叶えるために、主人公は何を失う？',
    options: [
      { label: '大切な人の命', value: 'life', example: '恋人を守るために自分が犠牲になる' },
      { label: '人間性・記憶', value: 'humanity', example: '力を得る代わりに感情を失う' },
      { label: '地位・名誉', value: 'status', example: '真実を暴くために追放される' },
      { label: '平穏な日常', value: 'peace', example: '戦いを選び、二度と戻れない' },
    ],
    aiHint: '代償の重さに合わせて、中盤の試練（猪肚）の強度と tension 曲線を自動調整'
  },
  {
    step: 3,
    title: '物語を動かす核心の衝突',
    question: 'この作品の「エンジン」になる対立構造は？',
    options: [
      { label: '理想 vs 現実', value: 'ideal_vs_reality', example: '正義を貫くか、汚い手で勝つか' },
      { label: '過去 vs 未来', value: 'past_vs_future', example: '復讐を果たすか、新しい道を選ぶか' },
      { label: '個 vs 組織', value: 'individual_vs_org', example: '国家権力に孤独に立ち向かう' },
      { label: '愛 vs 義務', value: 'love_vs_duty', example: '恋人を守るか、使命を果たすか' },
    ],
    aiHint: '選択した衝突型に合わせたアーク構成テンプレートを適用'
  },
  {
    step: 4,
    title: '読者を惹きつける最初のフック',
    question: '第1話の冒頭で、何を起こす？',
    options: [
      { label: '異世界転生・能力覚醒', value: 'isekai_awakening', example: '目覚めたら最強スキルを持っていた' },
      { label: '日常の崩壊・事件発生', value: 'daily_break', example: '平穏な朝、家族が何者かに攫われる' },
      { label: '秘密の発見・謎の提示', value: 'mystery_hook', example: '古い手紙から、世界の真実を知る' },
      { label: '運命的出会い', value: 'fated_meeting', example: '最強の敵と、最悪のタイミングで出会う' },
    ],
    aiHint: 'フックから第1〜3話の詳細プロットを自動生成'
  },
];

export const EMOTIONAL_GOAL_TO_CATHARSIS = {
  triumph: { type: '大カタルシス', tensionPeak: 95, pattern: 'explosion' },
  bittersweet: { type: '中カタルシス', tensionPeak: 80, pattern: 'wave' },
  twist: { type: 'スパイク型', tensionPeak: 90, pattern: 'spike' },
  heartwarming: { type: '小カタルシス連鎖', tensionPeak: 70, pattern: 'gradual' },
};

export const CONFLICT_TO_ARC_TEMPLATE = {
  ideal_vs_reality: { arcs: 3, pattern: 'thesis_antithesis_synthesis' },
  past_vs_future: { arcs: 4, pattern: 'confrontation_resolution' },
  individual_vs_org: { arcs: 3, pattern: 'escalation_breakthrough' },
  love_vs_duty: { arcs: 4, pattern: 'dilemma_sacrifice' },
};

export const HOOK_TO_EP1_TEMPLATE = {
  isekai_awakening: { tension: 40, beats: ['awakening', 'discovery', 'first_use'] },
  daily_break: { tension: 60, beats: ['peace', 'incident', 'decision'] },
  mystery_hook: { tension: 50, beats: ['discovery', 'investigation', 'clue'] },
  fated_meeting: { tension: 55, beats: ['encounter', 'conflict', 'realization'] },
};