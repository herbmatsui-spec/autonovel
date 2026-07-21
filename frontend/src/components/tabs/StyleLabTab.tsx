export function StyleLabTab() {
  return (
    <div className="animate-fade-in flex flex-col gap-8">
      <div>
        <h3 style={{ fontSize: '1.2rem', color: '#fff' }}>🧬 文体ラボ</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          文章のスタイル分析と最適化機能を提供します。
        </p>
      </div>
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        <p>文体ラボ機能は現在開発中です。次期リリースで実装予定です。</p>
      </div>
    </div>
  );
}
