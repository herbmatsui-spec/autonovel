import { Book, Plot, Chapter, Bible, TaskStatus, OptimizationHistory, PendingPatch, PromptVersion, NarrativeMetricTrend } from '../types/api';

export const mockBooks: Book[] = [
  {
    id: 1,
    title: '検証用書籍 1',
    genre: 'ファンタジー',
    concept: '魔法と剣の世界',
    synopsis: 'ある日突然魔法に目覚めた少年の物語',
    target_eps: 10,
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 2,
    title: '検証用書籍 2',
    genre: 'SF',
    concept: 'サイバーパンク都市',
    synopsis: 'AIが支配する世界での反乱',
    target_eps: 15,
    created_at: '2024-02-01T00:00:00Z',
  },
];

export const mockPlots: Plot[] = [
  {
    id: 101,
    book_id: 1,
    episode_num: 1,
    title: '始まりの街',
    summary: '主人公が魔法に目覚める',
    content: '詳細なプロット内容...',
    status: 'completed',
  },
  {
    id: 102,
    book_id: 1,
    episode_num: 2,
    title: '旅立ち',
    summary: '街を出て冒険へ向かう',
    content: '詳細なプロット内容...',
    status: 'pending',
  },
];

export const mockChapters: Chapter[] = [
  {
    id: 201,
    book_id: 1,
    ep_num: 1,
    title: '第一章：目覚め',
    content: '本文テキスト...',
    summary: '概要テキスト...',
    killer_phrase: 'ここが俺の始まりだ',
    ai_insight: '読者の期待感を煽る導入',
    world_state: {},
    trinity_review_log: {},
    created_at: '2024-01-02T00:00:00Z',
  },
];

export const mockBible: Bible = {
  book_id: 1,
  characters: [
    { name: '主人公', role: '主役', traits: ['勇敢', '天然'], description: '魔法の素質がある少年' },
    { name: '導き手', role: '師匠', traits: ['厳格', '博識'], description: '元大魔導師' },
  ],
  world_setting: '魔法が一般的ではない世界',
  key_items: ['古の杖'],
};

export const mockTaskStatuses: Record<'success' | 'running' | 'failed', TaskStatus> = {
  success: {
    task_id: 'task-success',
    is_running: false,
    current_step: 5,
    total_steps: 5,
    message: '完了しました',
    logs: ['Step 1: OK', 'Step 2: OK', 'Step 3: OK', 'Step 4: OK', 'Step 5: OK'],
  },
  running: {
    task_id: 'task-running',
    is_running: true,
    current_step: 2,
    total_steps: 5,
    message: '処理中です...',
    logs: ['Step 1: OK', 'Step 2: Processing...'],
  },
  failed: {
    task_id: 'task-failed',
    is_running: false,
    current_step: 3,
    total_steps: 5,
    message: 'エラーが発生しました',
    logs: ['Step 1: OK', 'Step 2: OK', 'Step 3: ERROR - Timeout'],
  },
};

export const mockOptHistory: OptimizationHistory[] = [
  {
    id: 1,
    book_id: 1,
    timestamp: '2024-01-03T00:00:00Z',
    change_summary: 'プロットの整合性を修正',
    metrics_before: { quality: 70, coherence: 60 },
    metrics_after: { quality: 85, coherence: 80 },
  },
];

export const mockPendingPatches: PendingPatch[] = [
  {
    id: 501,
    book_id: 1,
    target_ep: 1,
    current_content: '元の内容',
    proposed_content: '修正後の内容',
    reason: '描写の具体化',
    status: 'pending',
  },
];

export const mockPromptVersions: PromptVersion[] = [
  {
    id: 1001,
    book_id: 1,
    version_tag: 'v1.0',
    prompt_text: 'あなたは小説家です...',
    created_at: '2024-01-01T00:00:00Z',
  },
];

export const mockMetricTrends: NarrativeMetricTrend[] = [
  {
    episode_num: 1,
    metrics: { quality: 80, tension: 60, eroticism: 20 },
  },
  {
    episode_num: 2,
    metrics: { quality: 85, tension: 70, eroticism: 30 },
  },
];
