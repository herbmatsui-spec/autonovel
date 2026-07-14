import { Chapter } from '@/types';

interface ChapterCardProps {
  chapter: Chapter;
}

export function ChapterCard({ chapter }: ChapterCardProps) {
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
