import { Tooltip } from '@/components/Tooltip';
import type { Book, Plot } from '@/types';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { StatusMessage } from '@/components/ui/StatusMessage';
import { useBookStore } from '@/store/useBookStore';
import { useAppActions } from '@/hooks/useAppActions';
import { useUIStore } from '@/store/useUIStore';

export default function PlotsTab() {
  const { selectedBook, plots } = useBookStore();
  const { handleExpandPlots } = useAppActions((_) => {}); // we don't need setLoading here
  const { setGlobalError } = useUIStore();

  // We could compute loading/error from store if we had them, but for simplicity we'll assume the data is already loaded.
  // In a real app, we would have loading/error states in the store.
  const plotsLoading = false;
  const plotsError = null;

  if (!selectedBook) {
    return <div className="text-center py-8">作品を選択してください。</div>;
  }

  return (
    <div className="animate-fade-in flex flex-col gap-8">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">プロット設計 - {selectedBook.title}</h2>
        <Button
          variant="default"
          onClick={handleExpandPlots}
        >
          プロットを自動生成
        </Button>
      </div>

      {plotsLoading && <LoadingState message="プロットを読み込み中..." />}
      {plotsError && <StatusMessage variant="destructive">プロットの読み込みに失敗しました。</StatusMessage>}
      {plots.length === 0 && (
        <EmptyState>
          <h3 className="font-semibold">まだプロットがありません</h3>
          <p className="text-sm text-muted-foreground">
            「プロットを自動生成」ボタンをクリックしてプロットを生成してください。
          </p>
        </EmptyState>
      )}
      {!plotsLoading && plots.length > 0 && (
        <div className="space-y-4">
          {plots.map((plot, index) => (
            <div key={plot.id} className="border rounded-lg p-4">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="font-semibold mb-2">エピソード {plot.episode_no}</h3>
                  <p className="text-sm text-muted-foreground mb-2">{plot.title}</p>
                  <div className="prose prose-sm max-w-none">
                    {plot.summary}
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <Tooltip
                    content="プロットの詳細情報を表示"
                    delay={500}
                  >
                    <Button variant="ghost" size="sm">
                      🔍 詳細
                    </Button>
                  </Tooltip>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}