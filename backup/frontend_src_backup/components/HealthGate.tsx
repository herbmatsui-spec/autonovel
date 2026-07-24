import { useEffect, useState } from 'react';
import { checkBackendHealth } from '../api';
import type { HealthStatus } from '../types';

interface HealthGateProps {
  children: React.ReactNode;
}

export function HealthGate({ children }: HealthGateProps) {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);

  const checkHealth = async () => {
    try {
      const status = await checkBackendHealth();
      setHealth(status);
    } catch (e) {
      setHealth(null);
    } finally {
      setLoading(false);
      setRetrying(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10_000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">システムを初期化中...</p>
        </div>
      </div>
    );
  }

  if (!health || health.status !== 'ok') {
    return (
      <div className="flex items-center justify-center h-screen bg-[var(--bg-main)]">
        <div className="glass-panel max-w-lg w-full mx-4 p-8 text-center">
          <h1 className="text-2xl font-bold mb-2">⚠️ システムステータス（バックエンド未接続）</h1>
          <p className="text-sm text-muted-foreground mb-6">
            バックエンドサーバーに接続できません。サーバーが起動しているか確認してください。
          </p>

          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="glass-sm p-3 rounded-lg text-center">
              <div className={`w-3 h-3 rounded-full mx-auto mb-1 ${health?.status === 'ok' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
              <div className="text-xs text-muted-foreground">API Server</div>
              <div className="text-xs font-mono font-semibold">{health?.status ?? 'offline'}</div>
            </div>
            <div className="glass-sm p-3 rounded-lg text-center">
              <div className={`w-3 h-3 rounded-full mx-auto mb-1 ${health?.database === 'ok' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
              <div className="text-xs text-muted-foreground">Database</div>
              <div className="text-xs font-mono font-semibold">{health?.database ?? 'offline'}</div>
            </div>
            <div className="glass-sm p-3 rounded-lg text-center">
              <div className={`w-3 h-3 rounded-full mx-auto mb-1 ${health?.worker === 'ok' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
              <div className="text-xs text-muted-foreground">Worker</div>
              <div className="text-xs font-mono font-semibold">{health?.worker ?? 'offline'}</div>
            </div>
          </div>

          <button
            onClick={() => {
              setRetrying(true);
              checkHealth();
            }}
            disabled={retrying}
            className="btn btn-primary w-full"
          >
            {retrying ? '接続確認中...' : '🔄 再接続を試行'}
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}