import React, { useState, useEffect } from 'react';
import { InlineSuggestion } from '../../types/editorLayout';

interface InlineDiffSuggestionProps {
  suggestions: InlineSuggestion[];
  content: string;
  onAccept: (suggestionId: string) => void;
  onReject: (suggestionId: string) => void;
  onApplyAll?: () => void;
  className?: string;
}

export const InlineDiffSuggestion: React.FC<InlineDiffSuggestionProps> = ({
  suggestions,
  content,
  onAccept,
  onReject,
  onApplyAll,
  className = ''
}) => {
  const [appliedSuggestions, setAppliedSuggestions] = useState<Set<string>>(new Set());
  const [localContent, setLocalContent] = useState(content);

  // Content changes and re-process suggestions
  useEffect(() => {
    setLocalContent(content);
    setAppliedSuggestions(new Set());
  }, [content]);

  // Apply accepted suggestions to content
  useEffect(() => {
    let updatedContent = content;
    
    suggestions.forEach(suggestion => {
      if (appliedSuggestions.has(suggestion.id)) {
        if (suggestion.type === 'replace') {
          const start = Math.min(suggestion.startOffset, updatedContent.length);
          const end = Math.min(suggestion.endOffset, updatedContent.length);
          updatedContent = 
            updatedContent.substring(0, start) +
            suggestion.suggestedText +
            updatedContent.substring(end);
        } else if (suggestion.type === 'insert') {
          const position = Math.min(suggestion.startOffset, updatedContent.length);
          updatedContent = 
            updatedContent.substring(0, position) +
            suggestion.suggestedText +
            updatedContent.substring(position);
        } else if (suggestion.type === 'delete') {
          const start = Math.min(suggestion.startOffset, updatedContent.length);
          const end = Math.min(suggestion.endOffset, updatedContent.length);
          updatedContent = 
            updatedContent.substring(0, start) +
            updatedContent.substring(end);
        }
      }
    });

    setLocalContent(updatedContent);
  }, [appliedSuggestions, suggestions, content]);

  const renderHighlightedContent = () => {
    let lastIndex = 0;
    const elements: React.ReactNode[] = [];
    
    // Sort suggestions by start offset
    const sortedSuggestions = [...suggestions].sort((a, b) => a.startOffset - b.startOffset);
    
    sortedSuggestions.forEach((suggestion) => {
      if (appliedSuggestions.has(suggestion.id)) {
        // If suggestion is applied, skip the original text
        const end = Math.min(suggestion.endOffset, localContent.length);
        lastIndex = end;
      } else {
        // If suggestion is pending, show highlighted original text
        const start = Math.min(suggestion.startOffset, localContent.length);
        const end = Math.min(suggestion.endOffset, localContent.length);
        
        if (start > lastIndex) {
          elements.push(localContent.substring(lastIndex, start));
        }
        
        if (start < end) {
          elements.push(
            <span
              key={suggestion.id}
              className="inline-suggestion-item"
              data-suggestion-id={suggestion.id}
            >
              <span className="suggestion-original">{localContent.substring(start, end)}</span>
              <span className="suggestion-actions">
                <button
                  type="button"
                  className="suggestion-accept-btn"
                  onClick={() => onAccept(suggestion.id)}
                  title="採用"
                >
                  ✓
                </button>
                <button
                  type="button"
                  className="suggestion-reject-btn"
                  onClick={() => onReject(suggestion.id)}
                  title="破棄"
                >
                  ✖
                </button>
              </span>
            </span>
          );
        }
        
        lastIndex = end;
      }
    });
    
    // Add remaining content
    if (lastIndex < localContent.length) {
      elements.push(localContent.substring(lastIndex));
    }
    
    return elements;
  };

  const getStatusMessage = () => {
    const pending = suggestions.filter(s => !appliedSuggestions.has(s.id));
    const accepted = appliedSuggestions.size;
    
    if (pending.length === 0) {
      return '✅ すべての提案が処理されました';
    }
    
    if (accepted === 0) {
      return `🔍 ${pending.length}件の提案を待機中...`;
    }
    
    return `🔍 ${pending.length}件の提案を待機中... (${accepted}件の提案を適用済み)`;
  };

  if (suggestions.length === 0) {
    return null;
  }

  return (
    <div className={`inline-diff-suggestion ${className}`}>
      <div className="suggestion-header">
        <div className="suggestion-status">
          <span className="status-icon">📝</span>
          <span className="status-message">{getStatusMessage()}</span>
        </div>
        {suggestions.some(s => !appliedSuggestions.has(s.id)) && onApplyAll && (
          <button 
            className="apply-all-btn"
            onClick={onApplyAll}
          >
            ✨ すべて採用
          </button>
        )}
      </div>
      
      <div className="suggestion-content" style={{ position: 'relative' }}>
        <div 
          className="content-text"
          style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', lineHeight: '1.6' }}
        >
          {renderHighlightedContent()}
        </div>
      </div>
      
      <div className="suggestion-footer">
        <div className="suggestion-stats">
          {suggestions.map(suggestion => (
            <div key={suggestion.id} className="stat-item">
              <span className={`stat-type type-${suggestion.type}`}>{suggestion.type}</span>
              <span className={`stat-status status-${suggestion.status}`}>{suggestion.status}</span>
              {suggestion.reason && (
                <span className="stat-reason" title={suggestion.reason}>💭</span>
              )}
            </div>
          ))}
        </div>
        <div className="suggestion-legend">
          <span className="legend-item">
            <span className="legend-dot dot-replace"></span>
            置換
          </span>
          <span className="legend-item">
            <span className="legend-dot dot-insert"></span>
            挿入
          </span>
          <span className="legend-item">
            <span className="legend-dot dot-delete"></span>
            削除
          </span>
        </div>
      </div>
    </div>
  );
};

const styles = {
  'inline-diff-suggestion': {
    border: '1px solid var(--border-color)',
    borderRadius: 'var(--radius-md)',
    padding: '16px',
    margin: '8px 0',
    backgroundColor: 'var(--bg-card)',
    fontSize: '0.9rem'
  },
  'suggestion-header': {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
    paddingBottom: '8px',
    borderBottom: '1px solid var(--border-color)'
  },
  'suggestion-status': {
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  'status-icon': {
    fontSize: '1.2rem'
  },
  'status-message': {
    color: 'var(--text-muted)',
    fontSize: '0.85rem'
  },
  'apply-all-btn': {
    padding: '6px 12px',
    backgroundColor: 'var(--accent-purple)',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '0.85rem',
    fontWeight: 600,
    transition: 'all 0.2s ease'
  },
  'suggestion-content': {
    minHeight: '60px',
    padding: '12px',
    backgroundColor: 'rgba(0,0,0,0.2)',
    borderRadius: '8px',
    border: '1px dashed var(--border-color)'
  },
  'inline-suggestion-item': {
    position: 'relative',
    display: 'inline-block',
    margin: '0 -2px',
    padding: '2px 4px',
    borderRadius: '4px',
    backgroundColor: 'rgba(139, 92, 246, 0.2)',
    border: '1px solid var(--accent-purple)',
    animation: 'pulse 2s infinite'
  },
  'suggestion-original': {
    color: 'var(--text-muted)',
    textDecoration: 'line-through',
    marginRight: '8px'
  },
  'suggestion-actions': {
    display: 'inline-flex',
    gap: '4px',
    verticalAlign: 'middle'
  },
  'suggestion-accept-btn': {
    backgroundColor: 'var(--accent-success)',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    width: '20px',
    height: '20px',
    cursor: 'pointer',
    fontSize: '0.7rem',
    fontWeight: 600,
    transition: 'all 0.2s ease'
  },
  'suggestion-reject-btn': {
    backgroundColor: 'var(--accent-danger)',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    width: '20px',
    height: '20px',
    cursor: 'pointer',
    fontSize: '0.7rem',
    fontWeight: 600,
    transition: 'all 0.2s ease'
  },
  'suggestion-footer': {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '12px',
    paddingTop: '12px',
    borderTop: '1px solid var(--border-color)'
  },
  'suggestion-stats': {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap'
  },
  'stat-item': {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 8px',
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: '4px',
    fontSize: '0.75rem'
  },
  'stat-type': {
    padding: '2px 6px',
    borderRadius: '3px',
    fontWeight: 600
  },
  'type-replace': {
    backgroundColor: 'rgba(239, 68, 68, 0.2)',
    color: '#f87171'
  },
  'type-insert': {
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    color: '#34d399'
  },
  'type-delete': {
    backgroundColor: 'rgba(107, 114, 128, 0.2)',
    color: '#9ca3af'
  },
  'stat-status': {
    padding: '2px 6px',
    borderRadius: '3px',
    fontSize: '0.7rem'
  },
  'status-pending': {
    backgroundColor: 'rgba(245, 158, 11, 0.2)',
    color: '#fbbf24'
  },
  'status-accepted': {
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    color: '#34d399'
  },
  'status-rejected': {
    backgroundColor: 'rgba(239, 68, 68, 0.2)',
    color: '#f87171'
  },
  'stat-reason': {
    cursor: 'help',
    opacity: 0.7,
    fontSize: '0.8rem'
  },
  'suggestion-legend': {
    display: 'flex',
    gap: '12px',
    fontSize: '0.75rem',
    color: 'var(--text-muted)'
  },
  'legend-item': {
    display: 'flex',
    alignItems: 'center',
    gap: '4px'
  },
  'legend-dot': {
    width: '8px',
    height: '8px',
    borderRadius: '50%'
  },
  'dot-replace': {
    backgroundColor: '#ef4444'
  },
  'dot-insert': {
    backgroundColor: '#10b981'
  },
  'dot-delete': {
    backgroundColor: '#9ca3af'
  },
  '@keyframes pulse': {
    '0%, 100%': { opacity: 1 },
    '50%': { opacity: 0.6 }
  }
};