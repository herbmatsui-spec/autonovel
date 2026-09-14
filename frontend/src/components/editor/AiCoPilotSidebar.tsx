import React, { useState, useEffect } from 'react';
import { GraphEvidenceNode, ConsistencyIssue } from '../../types/editor';
import { useNovelContext } from '../../context/NovelContext';

interface AiCoPilotSidebarProps {
  bookId?: number;
  currentText: string;
  onToast?: (msg: string, type?: "success" | "error" | "info") => void;
  onOpenAuditReport?: () => void;
}

interface AIPersona {
  name: string;
  avatar: string;
  role: string;
  specialty: string;
  voice: string;
}

interface Message {
  id: string;
  type: 'ai' | 'user';
  content: string;
  timestamp: Date;
  suggestions?: string[];
  evidence?: GraphEvidenceNode[];
  isAiThinking?: boolean;
}

const defaultPersona: AIPersona = {
  name: '真央（まお）',
  avatar: '🧠',
  role: '専属編集者',
  specialty: '物語の構成とキャラクター一貫性',
  voice: '温かく、具体的'
};

export const AiCoPilotSidebar: React.FC<AiCoPilotSidebarProps> = ({
  bookId,
  currentText,
  onToast,
  onOpenAuditReport,
}) => {
  const {
    selectedBookId,
    currentEpNum,
    character,
    lineScores,
    activeHighlight,
  } = useNovelContext();

  const [messages, setMessages] = useState<Message[]>(() => {
    const initialMessage: Message = {
      id: '1',
      type: 'ai',
      content: `こんにちは！${character.name || '主人公'}の${currentEpNum || 1}話をお読みしました。まず最初に、冒頭の掴みについてお伝えしたいです。あなたが書いたこの最初のシーンの雰囲気は本当に素晴らしく、読者の興味を引くことに成功しています！`,
      timestamp: new Date(),
      suggestions: [
        "敵との戦闘シーンを1つ追加して緊張感を高める",
        "環境描写で世界の雰囲気をさらに深く描写する",
        "最初の会話でキャラクターの個性をさらに明確にする"
      ],
      evidence: [],
      isAiThinking: false,
    };
    return [initialMessage];
  });

  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [confidenceScore, setConfidenceScore] = useState(87);
  const [qualityMetrics, setQualityMetrics] = useState({
    tension: 7.2,
    eroticDensity: 3.8,
    pacing: 6.5,
    consistency: 8.9,
  density: 5.2,
  originality: 7.1,
  });

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('ja-JP', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    const aiResponse: Message = {
      id: (Date.now() + 1).toString(),
      type: 'ai',
      content: '...,',
      timestamp: new Date(),
      isAiThinking: true,
    };

    setMessages(prev => [...prev, aiResponse]);

    try {
      const response = await fetch('/api/ai/coach', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          book_id: bookId || selectedBookId,
          chapter: currentEpNum,
          current_text: currentText,
          user_query: inputValue,
          character_context: {
            name: character.name,
            personality: character.personality,
            genre: character.genre,
          },
        }),
      });

      const data = await response.json();

      const finalAiMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: data.response || '...に関する洞察を得ました！',
        timestamp: new Date(),
        suggestions: data.suggestions || [],
        evidence: data.evidence || [],
        isAiThinking: false,
      };

      setMessages(prev => prev.map(msg =>
        msg.id === aiResponse.id ? finalAiMessage : msg
      ));

      if (data.suggestions && data.suggestions.length > 0) {
        onToast?.(`✨ ${data.suggestions[0]}`, 'success');
      }

    } catch (error) {
      console.error('AIコーチからの応答取得に失敗:', error);
      
      const errorAiMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: '技術的な問題が発生しました。もう一度お試しください。',
        timestamp: new Date(),
        isAiThinking: false,
      };

      setMessages(prev => prev.map(msg =>
        msg.id === aiResponse.id ? errorAiMessage : msg
      ));
    }

    setIsTyping(false);
  };

  const getMetricColor = (value: number, type: string) => {
    if (type === 'consistency' || type === 'originality') {
      if (value >= 7) return '#10b981';
      if (value >= 5) return '#fbbf24';
      return '#ef4444';
    }
    
    if (type === 'tension' || type === 'pacing') {
      if (value >= 7) return '#8b5cf6';
      if (value >= 4) return '#06b6d4';
      return '#10b981';
    }
    
    if (type === 'eroticDensity' || type === 'density') {
      if (value >= 5) return '#f43f5e';
      if (value >= 3) return '#eab308';
      return '#10b981';
    }
    
    return '#9ca3af';
  };

  const getMetricLabel = (metric: string) => {
    const labels: Record<string, string> = {
      tension: '緊張感',
      eroticDensity: '官能的密度',
      pacing: 'テンポ',
      consistency: '一貫性',
      density: '物語の密度',
      originality: '独創性'
    };
    return labels[metric] || metric;
  };

  return (
    <div className="ai-copilot-sidebar" style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: 'var(--bg-card)',
      border: '1px solid var(--border-color)',
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden'
    }}>
      <div className="ai-copilot-sidebar__header" style={{
        padding: '20px',
        borderBottom: '1px solid var(--border-color)',
        backgroundColor: 'rgba(139, 92, 246, 0.1)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            backgroundColor: 'var(--accent-purple)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '24px'
          }}>
            {defaultPersona.avatar}
          </div>
          <div>
            <h3 style={{
              fontSize: '1.1rem',
              fontWeight: 700,
              color: 'var(--accent-purple)',
              margin: 0,
              marginBottom: '4px'
            }}>
              {defaultPersona.name}
            </h3>
            <p style={{
              fontSize: '0.85rem',
              color: 'var(--text-muted)',
              margin: 0
            }}>
              {defaultPersona.role} • {defaultPersona.specialty}
            </p>
          </div>
        </div>

        <div style={{ marginTop: '16px' }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '8px'
          }}>
            <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>総合信頼度</span>
            <span style={{
              fontSize: '1.1rem',
              fontWeight: 700,
              color: confidenceScore >= 80 ? '#10b981' :
                     confidenceScore >= 60 ? '#fbbf24' : '#ef4444'
            }}>
              {confidenceScore}%
            </span>
          </div>
          <div style={{
            width: '100%',
            height: '8px',
            backgroundColor: 'rgba(255,255,255,0.1)',
            borderRadius: '4px',
            overflow: 'hidden'
          }}>
            <div style={{
              width: `${confidenceScore}%`,
              height: '100%',
              backgroundColor: confidenceScore >= 80 ? '#10b981' :
                             confidenceScore >= 60 ? '#fbbf24' : '#ef4444',
              transition: 'width 0.3s ease'
            }} />
          </div>
        </div>
      </div>

      <div className="ai-copilot-sidebar__metrics" style={{
        padding: '16px',
        borderBottom: '1px solid var(--border-color)',
        backgroundColor: 'rgba(0,0,0,0.2)'
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '12px'
        }}>
          {Object.entries(qualityMetrics).map(([key, value]) => (
            <div
              key={key}
              style={{
                padding: '12px',
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: '8px',
                border: `1px solid ${getMetricColor(value, key)}30`
              }}
            >
              <div style={{
                fontSize: '0.75rem',
                color: 'var(--text-muted)',
                marginBottom: '4px'
              }}>
                {getMetricLabel(key)}
              </div>
              <div style={{
                fontSize: '1.2rem',
                fontWeight: 700,
                color: getMetricColor(value, key)
              }}>
                {value.toFixed(1)}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="ai-copilot-sidebar__messages" style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px'
      }}>
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.type}`}
            style={{
              marginBottom: '16px',
              display: 'flex',
              flexDirection: message.type === 'ai' ? 'row' : 'row-reverse',
              alignItems: 'flex-start',
              gap: '8px'
            }}
          >
            <div
              className={`message__avatar ${message.type}`}
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                backgroundColor: message.type === 'ai' ? 'var(--accent-purple)' : 'var(--accent-cyan)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '18px',
                flexShrink: 0
              }}
            >
              {message.type === 'ai' ? defaultPersona.avatar : '👤'}
            </div>

            <div
              className={`message__content ${message.type}`}
              style={{
                maxWidth: '70%',
                padding: '12px 16px',
                borderRadius: '12px',
                fontSize: '0.9rem',
                lineHeight: 1.5,
                backgroundColor: message.type === 'ai' ?
                  'rgba(139, 92, 246, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                border: message.type === 'ai' ?
                  '1px solid var(--accent-purple)' : '1px solid var(--accent-cyan)',
                color: 'var(--text-main)'
              }}
            >
              <div style={{ marginBottom: '8px' }}>
                {message.isAiThinking ? (
                  <span style={{ color: 'var(--accent-purple)', fontStyle: 'italic' }}>考え中...</span>
                ) : (
                  <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{message.content}</p>
                )}
              </div>

              {message.suggestions && message.suggestions.length > 0 && (
                <div className="message__suggestions" style={{ marginTop: '12px' }}>
                  <div style={{
                    fontSize: '0.8rem',
                    color: 'var(--accent-purple)',
                    fontWeight: 600,
                    marginBottom: '6px'
                  }}>
                    💡 提案:
                  </div>
                  <ul style={{
                    margin: 0,
                    paddingLeft: '20px',
                    fontSize: '0.85rem',
                    color: 'var(--text-muted)'
                  }}>
                    {message.suggestions.map((suggestion, index) => (
                      <li key={index} style={{ marginBottom: '4px' }}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}

              {message.evidence && message.evidence.length > 0 && (
                <div className="message__evidence" style={{ marginTop: '12px' }}>
                  <div style={{
                    fontSize: '0.8rem',
                    color: 'var(--accent-cyan)',
                    fontWeight: 600,
                    marginBottom: '6px'
                  }}>
                    📊 証拠:
                  </div>
                  <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '6px'
                  }}>
                    {message.evidence.map((evidence) => (
                      <span
                        key={evidence.id}
                        style={{
                          padding: '4px 8px',
                          backgroundColor: 'rgba(56, 189, 248, 0.15)',
                          border: '1px solid var(--accent-cyan)',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          color: 'var(--accent-cyan)'
                        }}
                      >
                        {evidence.label}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="message__timestamp" style={{
                fontSize: '0.7rem',
                color: 'var(--text-muted)',
                marginTop: '8px',
                textAlign: message.type === 'ai' ? 'left' : 'right'
              }}>
                {formatTime(message.timestamp)}
              </div>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="message ai" style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '16px' }}>
            <div className="message__avatar ai" style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              backgroundColor: 'var(--accent-purple)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '18px'
            }}>
              {defaultPersona.avatar}
            </div>
            <div style={{ padding: '12px 16px', backgroundColor: 'rgba(139, 92, 246, 0.15)', borderRadius: '12px', border: '1px solid var(--accent-purple)' }}>
              <span style={{ color: 'var(--accent-purple)', fontStyle: 'italic' }}>思考中...</span>
            </div>
          </div>
        )}
      </div>

      <div className="ai-copilot-sidebar__input" style={{
        padding: '16px',
        borderTop: '1px solid var(--border-color)',
        backgroundColor: 'var(--bg-secondary)'
      }}>
        <div style={{
          display: 'flex',
          gap: '8px',
          alignItems: 'center',
          marginBottom: '12px'
        }}>
          <select
            value={defaultPersona.voice}
            onChange={(e) => {
              console.log('Voice changed:', e.target.value);
            }}
            style={{
              padding: '6px 10px',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-card)',
              color: 'var(--text-main)',
              fontSize: '0.85rem'
            }}
          >
            <option value="温かく">温かく</option>
            <option value="率直に">率直に</option>
            <option value="ユーモア">ユーモア</option>
            <option value="分析的">分析的</option>
          </select>
          <button
            onClick={onOpenAuditReport}
            style={{
              padding: '6px 12px',
              borderRadius: '6px',
              border: '1px solid var(--accent-danger)',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              color: 'var(--accent-danger)',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 600
            }}
          >
            🔍 矛盾診断を開く
          </button>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="AI編集者に質問または修正を依頼..."
            style={{
              flex: 1,
              padding: '10px 14px',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-card)',
              color: 'var(--text-main)',
              fontSize: '0.9rem',
              outline: 'none'
            }}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isTyping}
            style={{
              padding: '10px 20px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: inputValue.trim() && !isTyping ? 'var(--accent-purple)' : 'var(--border-color)',
              color: inputValue.trim() && !isTyping ? 'white' : 'var(--text-muted)',
              cursor: inputValue.trim() && !isTyping ? 'pointer' : 'not-allowed',
              fontSize: '0.9rem',
              fontWeight: 600,
              transition: 'all 0.2s ease'
            }}
          >
            {isTyping ? '⏳' : '📤'}
          </button>
        </div>

        <div style={{ marginTop: '12px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          💡 例: "敵の動機を深掘りしてください", "3ページ目をよりテンポよく書いてください", "キャラクターの語尾を統一してください"
        </div>
      </div>
    </div>
  );
};