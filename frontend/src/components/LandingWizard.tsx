import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useEasyModeStore } from '@/store/useEasyModeStore';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { useAppActions } from '@/hooks/useAppActions';
import { getPlanningOptions } from '@/api';
import type { PlanningOptions } from '@/types/api';
import { toast } from 'sonner';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';

export default function LandingWizard() {
  const {
    setEasyGenre,
    easyKeywords,
    setEasyKeywords,
    setEasyArchetype,
  } = useEasyModeStore();

  const { apiKey } = useUserSettingsStore();
  const { setPendingEasyMode } = useWorkspaceStore();
  const { handleCreateEasyMode } = useAppActions((_) => {});
  const [options, setOptions] = useState<PlanningOptions | null>(null);
  const [selectedGenreKey, setSelectedGenreKey] = useState<string | null>(null);
  const [apiKeyLocal, setApiKeyLocal] = useState(apiKey);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    setApiKeyLocal(apiKey);
  }, [apiKey]);

  useEffect(() => {
    if (!options) {
      getPlanningOptions()
        .then((data) => {
          if (data.easy_genres && Object.keys(data.easy_genres).length > 0) {
            setOptions(data);
            const firstKey = Object.keys(data.easy_genres)[0];
            setSelectedGenreKey(firstKey);
            if (data.easy_genres[firstKey]) {
              setEasyGenre(data.easy_genres[firstKey].genre);
              const rawArch = data.easy_genres[firstKey].archetype;
              setEasyArchetype(rawArch);
            }
          }
        })
        .catch((err) => {
          console.error('Failed to load planning options:', err);
          toast.error('ジャンル情報の読み込みに失敗しました。');
        });
    }
  }, [options, setEasyGenre, setEasyArchetype]);

  const hasApiKey = apiKeyLocal.trim().length >= 10;

  const handleGenreCardClick = (key: string) => {
    setSelectedGenreKey(key);
    const genreData = options?.easy_genres?.[key];
    if (genreData) {
      setEasyGenre(genreData.genre);
      setEasyArchetype(genreData.archetype);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasApiKey) {
      toast.error('有効なAPIキーを入力してください。');
      return;
    }
    if (!options) {
      toast.error('ジャンル情報の読み込み中です。');
      return;
    }
    setIsSubmitting(true);
    setPendingEasyMode(true);
    handleCreateEasyMode()
      .then(() => {
        toast.success('生成を開始しました！進捗は画面下で確認できます。');
      })
      .catch((err) => {
        console.error('Easy mode generation failed:', err);
        toast.error('生成の開始に失敗しました。');
        setPendingEasyMode(false);
      })
      .finally(() => {
        setIsSubmitting(false);
      });
  };

  const genreOptions = options ? Object.keys(options.easy_genres) : [];

  return (
    <div className="min-h-[100vh] bg-[var(--bg-main)] flex flex-col">
      <div className="flex h-[4rem] items-center justify-between px-4 bg-[var(--bg-sidebar)] border-b border-[var(--border)]">
        <div className="flex items-center space-x-3">
          <div className="h-8 w-8 bg-[var(--accent)] rounded-full flex items-center justify-center">
            <span className="text-white font-bold">🎌</span>
          </div>
          <h1 className="text-xl font-bold">AutoNovel</h1>
        </div>
        <div className="flex items-center space-x-4">
          <Button
            variant="outline"
            onClick={() => {
              // TODO: maybe show a menu?
            }}
          >
            {hasApiKey ? (
              <>
                <span className="mr-2">API Key: {apiKeyLocal.slice(0, 4)}...</span>
              </>
            ) : (
              <span className="text-muted-foreground">API Key 未設定</span>
            )}
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-6">
          <div className="border-b border-[var(--border)] pb-4">
            <h2 className="text-2xl font-bold">⚡ かんたんモードで小説を作る</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              ジャンルを選んでボタンを押すだけ。あとは AI が企画・プロット・本文まで自動で書きます。
            </p>
          </div>

          {/* ジャンル選択カード */}
          <div className="space-y-4">
            <h3 className="font-semibold mb-2">ジャンルを選択</h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {genreOptions.map((key) => {
                const genreData = options?.easy_genres?.[key];
                const isSelected = selectedGenreKey === key;
                return (
                  <button
                    key={key}
                    onClick={() => handleGenreCardClick(key)}
                    className={`w-full aspect-[16/9] flex flex-col items-center justify-center border rounded-lg p-4 ${
                      isSelected
                        ? 'border-[var(--accent)] bg-[var(--accent)]/20 text-[var(--accent)]'
                        : 'border-[var(--border)] hover:bg-[var(--bg-muted)]'
                    }`}
                  >
                    <div className="text-2xl font-bold mb-2">{genreData?.genre ?? key}</div>
                    <div className="text-sm text-center">{genreData?.archetype ?? ''}</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* キーワード（任意） */}
          <div className="space-y-4">
            <h3 className="font-semibold mb-2">キーワード（任意）</h3>
            <Input
              value={easyKeywords}
              onChange={(e) => setEasyKeywords(e.target.value)}
              placeholder="例: 追放, 復讐, チート"
              className="w-full"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              物語の核となる要素をカンマで区切って入力します。未入力の場合はジャンルから自動で決めます。
            </p>
          </div>

          {/* 詳細設定（折りたたみ） */}
          <div className="space-y-4">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full flex items-center justify-between px-4 py-2 text-sm font-semibold text-[var(--text-secondary)] hover:bg-[var(--bg-muted)] rounded"
            >
              <span>🔧 詳細設定</span>
              <span className={`transition-transform ${showAdvanced ? 'rotate-180' : ''}`}>▾</span>
            </button>
            {showAdvanced && (
              <div className="mt-4 space-y-4 border-t border-[var(--border)] pt-4">
                {/* We'll implement a simplified version of the advanced settings from EasyModeDialog.
                  For now, we'll just show a placeholder. */}
                <div className="space-y-4">
                  <h3 className="font-semibold mb-2">詳細設定（実装中）</h3>
                  <p className="text-sm text-muted-foreground">
                    ここに詳細設定（文体、目標話数、官能表現、挿絵等）が入ります。
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* APIキー入力エリア */}
        <div className="mt-6 pt-4 border-t border-[var(--border)]">
          <h3 className="font-semibold mb-2">APIキー設定</h3>
          <div className={`rounded-lg border p-4 ${hasApiKey ? 'border-emerald-700/50 bg-emerald-950/20' : 'border-amber-600/60 bg-amber-950/20'}`}>
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-sm font-bold ${hasApiKey ? 'text-emerald-200' : 'text-amber-200'}`}>
                {hasApiKey ? '✅ Gemini APIキー（設定済み）' : '⚠️ Gemini APIキーが必要です'}
              </span>
            </div>
            <Input
              type="password"
              value={apiKeyLocal}
              onChange={(e) => setApiKeyLocal(e.target.value)}
              placeholder="AIza...  （Google AI Studio で無料取得）"
              className="w-full text-xs px-3 py-2 rounded bg-slate-950 text-white font-medium border border-slate-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              aria-label="Gemini APIキーを入力"
            />
            {!hasApiKey && (
              <p className="mt-2 text-[0.7rem] text-amber-300/90">
                取得は無料です → <span className="font-mono">aistudio.google.com/app/apikey</span>
              </p>
            )}
          </div>
        </div>

        {/* 生成ボタン */}
        <div className="mt-6">
          <Button
            variant="default"
            onClick={handleSubmit}
            disabled={isSubmitting || !hasApiKey || !options}
            className="w-full"
          >
            {isSubmitting ? '生成中...' : hasApiKey && options ? '🚀 生成開始' : 'APIキーまたはジャンル情報が必要'}
          </Button>
          <p className="mt-2 text-[0.7rem] text-muted-foreground">
            生成には数十秒〜数分かかることがあります。進捗は画面下で確認でき、完成した小説は「作品一覧」に表示されます。
          </p>
        </div>
      </div>
    </div>
  );
}