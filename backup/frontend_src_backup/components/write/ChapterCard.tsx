import { Chapter } from '@/types';

interface ChapterCardProps {
  chapter: Chapter;
  qualityScore?: number;
  killerPhrase?: string;
}

export function ChapterCard({ chapter, qualityScore, killerPhrase }: ChapterCardProps) {
  const ch = chapter;
  return (
    <div
      id={`chapter-${ch.ep_num}`}
      className="glass-panel"
      style={{ padding: '2rem' }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid var(--border)',
          paddingBottom: '0.75rem',
          marginBottom: '1rem',
        }}
      >
        <h4 style={{ fontSize: '1.15rem' }}>
          第{ch.ep_num}話: {ch.title}
        </h4>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          {new Date(ch.created_at).toLocaleDateString()}
        </span>
      </div>
      {killerPhrase && (
        <div
          style={{
            fontSize: '0.8rem',
            padding: '0.25rem 0.5rem',
            background: 'rgba(239,68,68,0.15)',
            borderRadius: '4px',
            marginBottom: '0.5rem',
            display: 'inline-block',
          }}
        >
          🔥 キラーフレーズ: {killerPhrase}
        </div>
      )}
      {qualityScore !== undefined && (
        <div style={{ marginBottom: '0.5rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
            品質スコア: {Math.round(qualityScore * 100)}%
          </div>
          <div style={{ height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px' }}>
            <div
              style={{
                width: `${qualityScore * 100}%`,
                height: '100%',
                borderRadius: '2px',
                background:
                  qualityScore > 0.8
                    ? '#22c55e'
                    : qualityScore > 0.5
                      ? '#eab308'
                      : '#ef4444',
              }}
            />
          </div>
        </div>
      )}
      <p
        style={{
          fontSize: '0.85rem',
          color: 'var(--text-secondary)',
          background: 'rgba(255,255,255,0.02)',
          padding: '0.75rem 1rem',
          borderRadius: '6px',
          borderLeft: '3px solid var(--accent-indigo)',
          marginBottom: '1rem',
        }}
      >
        <strong>あらすじ: </strong>
        {ch.summary}
      </p>
      <div
        style={{
          fontSize: '0.95rem',
          lineHeight: 1.8,
          color: '#e5e7eb',
          maxHeight: '400px',
          overflowY: 'auto',
          whiteSpace: 'pre-wrap',
          padding: '0.5rem',
          fontFamily: '"Noto Serif JP", serif',
        }}
      >
        {ch.content}
      </div>
    </div>
  );
}
