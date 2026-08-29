import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { useBookStore } from '@/store/useBookStore';
import { useStoryCanvasStore } from '@/store/useStoryCanvasStore';
import { seedStoryCanvas } from '@/api';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';

export function StoryCanvasTab() {
  const { selectedBook } = useBookStore();
  const { nodes, edges, loading, setLoading } = useStoryCanvasStore();
  const { isExpertMode } = useUserSettingsStore();

  const handleSeed = async () => {
    if (!selectedBook) return;
    setLoading(true);
    try {
      await seedStoryCanvas(selectedBook.id);
    } finally {
      setLoading(false);
    }
  };

  if (!selectedBook) {
    return <div className="text-center py-8">作品を選択してください。</div>;
  }

  return (
    <div className="animate-fade-in flex flex-col gap-6 h-full">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold">ストーリーキャンバス - {selectedBook.title}</h2>
          <p className="text-xs text-muted-foreground mt-1">
            エピソード・キャラクター・構造を視覚的に編集
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="default" onClick={handleSeed} disabled={loading}>
            {loading ? '初期化中...' : '🌱 キャンバスを初期化 (Seed)'}
          </Button>
          {isExpertMode && (
            <span className="text-xs text-muted-foreground">Expert Mode</span>
          )}
        </div>
      </div>

      <div className="border rounded-lg p-4 bg-[var(--bg-muted)]/50 flex-1 min-h-[500px]">
        <div className="text-center text-muted-foreground py-12">
          🗺️ ストーリーキャンバス実装中...<br />
          ノード数: {nodes.length}、エッジ数: {edges.length}
        </div>
      </div>
    </div>
  );
}

export default StoryCanvasTab;