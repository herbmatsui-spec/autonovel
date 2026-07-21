export function AuditTab() {
  return (
    <div className="animate-fade-in flex flex-col gap-8">
      <div>
        <h3 style={{ fontSize: '1.2rem', color: '#fff' }}>⚖️ 品質監査</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          AIによる作品品質の自動監査と改善提案を行います。
        </p>
      </div>
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        <p>品質監査機能は現在開発中です。次期リリースで実装予定です。</p>
      </div>
    </div>
  );
}
