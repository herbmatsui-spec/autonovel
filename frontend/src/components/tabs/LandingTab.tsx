import type { TabId } from '../../store/useProjectStore';
import { useEffect, useState } from 'react';
import { checkBackendHealth } from '../../api';
import { useUserSettingsStore } from '../../store/useUserSettingsStore';
import { useNavigate } from 'react-router-dom';
import { useUIStore } from '../../store/useUIStore';

interface LandingTabProps {
  // Props are no longer needed; kept for compatibility but unused.
  // We'll remove them in future refactor.
  // setActiveTab: (tab: TabId) => void;
  // setCreateModalOpen: (open: boolean) => void;
  // setIsExpertMode: (val: boolean) => void;
}

export default function LandingTab(_props: LandingTabProps) {
  const { apiKey } = useUserSettingsStore();
  const { setCreateModalOpen, setIsExpertMode } = useUIStore();
  const navigate = useNavigate();
  const [health, setHealth] = useState<{ status: string; database: string; worker: string } | null>(null);

  useEffect(() => {
    checkBackendHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const hasApiKey = apiKey.trim().length >= 10;

  return (
    <div className="flex flex-col gap-6">
      {/* Hero */}
      <div className="text-center py-12 glass-sm rounded-xl">
        <h2 className="text-3xl font-extrabold gradient-text mb-3">
          ⚔️ 異世界小説生成プラットフォーム
        </h2>
        <p className="text-lg text-muted-foreground">
          AIがあなたのストーリーを紡ぎ出す
        </p>
        <div className="flex flex-wrap justify-center gap-4 mt-6">
          {!hasApiKey && (
            <Button
              variant="destructive"
              onClick={() => {
                // Navigate to settings? We'll just show a toast for now.
                toast.warning('APIキーを設定してください。');
              }}
            >
              APIキーを設定
            </Button>
          )}
          {hasApiKey && (
            <>
              <Button
                variant="default"
                onClick={() => {
                  setCreateModalOpen(true);
                }}
              >
                新規作成
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  navigate('/books');
                }}
              >
                作品一覧を見る
              </Button>
            </>
          )}
        </div>
        {health && (
          <div className="mt-4 flex flex-wrap justify-center gap-4 text-xs">
            <div>📡 バックエンド: {health.status}</div>
            <div>🗄️ データベース: {health.database}</div>
            <div>👷 ワーカー: {health.worker}</div>
          </div>
        )}
      </div>
      {/* Features */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <FeatureTile
          icon="📚"
          title="作品管理"
          description="シリーズ・エピソード・キャラクターを柔軟に管理"
        />
        <FeatureTile
          icon="🎨"
          title="プロット生成"
          description="AIがプロットを自動生成し、人間が調整"
        />
        <FeatureTile
          icon="✍️"
          title="執筆支援"
          description="ストリーミングでリアルタイムに本文を生成"
        />
        <FeatureTile
          icon="📈"
          title="品質分析"
          description="プロットの整合性やキャラクターの弧を自動評価"
        />
        <FeatureTile
          icon="🔊"
          title="音声変換"
          description="完成した作品をナレーション音声に変換"
        />
        <FeatureTile
          icon="🌍"
          title="多言語対応"
          description="翻訳・ローカライズでグローバル展開"
        />
      </div>
      {/* CTA */}
      <div className="flex justify-center mt-8">
        <Button
          variant={hasApiKey ? 'default' : 'destructive'}
          onClick={hasApiKey ? () => setCreateModalOpen(true) : () => toast.warning('APIキーを設定してください。')}
          className="w-full max-w-xs"
        >
          {hasApiKey ? '今すぐ始める' : 'APIキーを設定'}
        </Button>
      </div>
    </div>
  );
}

interface FeatureTileProps {
  icon: string;
  title: string;
  description: string;
}

function FeatureTile({ icon, title, description }: FeatureTileProps) {
  return (
    <div className="glass-sm rounded-xl p-6 flex flex-col items-center text-center">
      <div className="text-4xl mb-3">{icon}</div>
      <h3 className="font-semibold mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}