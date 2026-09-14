import React, { useState } from 'react';
import { ViralTitleRequest, ViralTitleResponse, TitleCandidate } from '../../types/marketing';
import { generateViralTitles } from '../../api/marketingApi';

interface ViralTitleGeneratorProps {
  initialGenre?: string;
  initialCoreTrope?: string;
  onSelectTitle?: (title: string, synopsis?: string) => void;
  onToast?: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export const ViralTitleGenerator: React.FC<ViralTitleGeneratorProps> = ({
  initialGenre = '異世界ファンタジー',
  initialCoreTrope = '',
  onSelectTitle,
  onToast,
}) => {
  const [genre, setGenre] = useState(initialGenre);
  const [coreTrope, setCoreTrope] = useState(initialCoreTrope);
  const [protagonistName, setProtagonistName] = useState('主人公');
  const [protagonistCheat, setProtagonistCheat] = useState('');
  const [antagonistOrOppression, setAntagonistOrOppression] = useState('');
  const [targetAudience, setTargetAudience] = useState('カクヨム読者');

  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ViralTitleResponse | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<TitleCandidate | null>(null);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!coreTrope.trim()) {
      onToast?.('核となる設定・ざまぁ/チート展開を入力してください', 'error');
      return;
    }

    setIsLoading(true);
    try {
      const req: ViralTitleRequest = {
        genre,
        core_trope: coreTrope,
        protagonist_name: protagonistName,
        protagonist_cheat: protagonistCheat,
        antagonist_or_oppression: antagonistOrOppression,
        target_audience: targetAudience,
        num_candidates: 30,
      };
      const data = await generateViralTitles(req);
      setResult(data);
      if (data.top_recommendations && data.top_recommendations.length > 0) {
        setSelectedCandidate(data.top_recommendations[0] ?? null);
      } else if (data.all_candidates && data.all_candidates.length > 0) {
        setSelectedCandidate(data.all_candidates[0] ?? null);
      }
      onToast?.(`CTR分析完了！${data.total_generated}案を生成・採点しました`, 'success');
    } catch (err: any) {
      console.error('Failed to generate viral titles:', err);
      onToast?.(`タイトル生成エラー: ${err.message || '通信に失敗しました'}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleApplyTitle = (candidate: TitleCandidate) => {
    if (onSelectTitle) {
      const synopsis = candidate.synopsis_snippet || result?.recommended_synopsis || '';
      onSelectTitle(candidate.title, synopsis);
      onToast?.(`タイトル「${candidate.title}」を採用しました！`, 'success');
    }
  };

  return (
    <div style={{ padding: '1.5rem', background: '#1e1e24', color: '#f3f4f6', borderRadius: '12px', minHeight: '600px' }}>
      <header style={{ marginBottom: '1.5rem', borderBottom: '1px solid #374151', paddingBottom: '1rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0, color: '#f9fafb' }}>
          🎯 カクヨム特化 CTR最大化タイトル生成エンジン
        </h2>
        <p style={{ color: '#9ca3af', fontSize: '0.875rem', marginTop: '0.25rem' }}>
          ランキング上位の構文パターンと感情トリガー（追放/逆転/ざまぁ）を解析し、30案をリアルタイム採点。
        </p>
      </header>

      {/* Input Form */}
      <form onSubmit={handleGenerate} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem', color: '#d1d5db' }}>
            ジャンル
          </label>
          <select
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
            style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#2d3748', color: '#fff', border: '1px solid #4a5568' }}
          >
            <option value="異世界ファンタジー">異世界ファンタジー</option>
            <option value="現代ファンタジー">現代ファンタジー</option>
            <option value="恋愛・ラブコメ">恋愛・ラブコメ</option>
            <option value="SF・現代ドラマ">SF・現代ドラマ</option>
          </select>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem', color: '#d1d5db' }}>
            核となる展開・ざまぁ/チート (必須)
          </label>
          <input
            type="text"
            placeholder="例: Sランク追放されたが実は神鑑定士だった"
            value={coreTrope}
            onChange={(e) => setCoreTrope(e.target.value)}
            required
            style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#2d3748', color: '#fff', border: '1px solid #4a5568' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem', color: '#d1d5db' }}>
            主人公チート・固有能力
          </label>
          <input
            type="text"
            placeholder="例: 万物分解と無限進化"
            value={protagonistCheat}
            onChange={(e) => setProtagonistCheat(e.target.value)}
            style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#2d3748', color: '#fff', border: '1px solid #4a5568' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.25rem', color: '#d1d5db' }}>
            追放者・抑圧要素
          </label>
          <input
            type="text"
            placeholder="例: 無能と罵った勇者パーティー"
            value={antagonistOrOppression}
            onChange={(e) => setAntagonistOrOppression(e.target.value)}
            style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#2d3748', color: '#fff', border: '1px solid #4a5568' }}
          />
        </div>

        <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
          <button
            type="submit"
            disabled={isLoading}
            style={{
              padding: '0.75rem 1.75rem',
              background: isLoading ? '#4b5563' : 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
              color: '#fff',
              fontWeight: 700,
              fontSize: '1rem',
              border: 'none',
              borderRadius: '8px',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
            }}
          >
            {isLoading ? '30案生成＆CTR採点中...' : '🚀 30案を生成・採点する'}
          </button>
        </div>
      </form>

      {/* Results View */}
      {result && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '1.5rem', marginTop: '1.5rem' }}>
          {/* Candidates List */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <h3 style={{ fontSize: '1.125rem', fontWeight: 600, margin: 0 }}>
                生成結果 ({result.total_generated} 案 - スコア順)
              </h3>
              <span style={{ fontSize: '0.875rem', color: '#10b981' }}>
                ⭐ 80点以上: 高CTR期待値
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '550px', overflowY: 'auto', paddingRight: '0.5rem' }}>
              {result.all_candidates.map((cand, idx) => {
                const isSelected = selectedCandidate?.title === cand.title;
                const isGold = cand.score >= 80;
                const isSilver = cand.score >= 70 && cand.score < 80;

                return (
                  <div
                    key={idx}
                    onClick={() => setSelectedCandidate(cand)}
                    style={{
                      padding: '1rem',
                      borderRadius: '8px',
                      background: isSelected ? '#1e293b' : '#111827',
                      border: isSelected ? '2px solid #3b82f6' : '1px solid #374151',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease-in-out',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                          {isGold && (
                            <span style={{ background: '#f59e0b', color: '#000', fontSize: '0.75rem', fontWeight: 800, padding: '2px 6px', borderRadius: '4px' }}>
                              GOLD CTR
                            </span>
                          )}
                          {isSilver && (
                            <span style={{ background: '#9ca3af', color: '#000', fontSize: '0.75rem', fontWeight: 800, padding: '2px 6px', borderRadius: '4px' }}>
                              SILVER
                            </span>
                          )}
                          <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
                            {cand.length}文字 {cand.syntax_match ? '✓構文一致' : ''}
                          </span>
                        </div>
                        <div style={{ fontSize: '1rem', fontWeight: 600, color: '#f3f4f6', lineHeight: 1.4 }}>
                          {cand.title}
                        </div>
                      </div>

                      <div style={{ textAlign: 'right', minWidth: '60px' }}>
                        <div style={{ fontSize: '1.25rem', fontWeight: 800, color: isGold ? '#fbbf24' : '#60a5fa' }}>
                          {cand.score}
                          <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>点</span>
                        </div>
                      </div>
                    </div>

                    {cand.high_ctr_keywords.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.5rem' }}>
                        {cand.high_ctr_keywords.map((kw, kwIdx) => (
                          <span key={kwIdx} style={{ fontSize: '0.7rem', background: '#374151', color: '#93c5fd', padding: '1px 6px', borderRadius: '4px' }}>
                            #{kw}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Details & Synopsis Preview */}
          <div style={{ background: '#111827', padding: '1.25rem', borderRadius: '8px', border: '1px solid #374151', height: 'fit-content' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 600, margin: '0 0 0.75rem 0', color: '#f9fafb' }}>
              選定タイトル詳細
            </h4>

            {selectedCandidate ? (
              <div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#60a5fa', marginBottom: '0.75rem', lineHeight: 1.4 }}>
                  {selectedCandidate.title}
                </div>

                <div style={{ background: '#1f2937', padding: '0.75rem', borderRadius: '6px', marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.8rem', color: '#9ca3af', marginBottom: '0.25rem' }}>CTR評価コメント:</div>
                  <div style={{ fontSize: '0.85rem', color: '#e5e7eb', lineHeight: 1.4 }}>
                    {selectedCandidate.critique}
                  </div>
                </div>

                <div style={{ marginBottom: '1.25rem' }}>
                  <div style={{ fontSize: '0.8rem', color: '#9ca3af', marginBottom: '0.25rem' }}>
                    推奨3行あらすじ（ファーストビュー最適化）:
                  </div>
                  <div style={{
                    fontSize: '0.85rem',
                    color: '#d1d5db',
                    background: '#0f172a',
                    padding: '0.75rem',
                    borderRadius: '6px',
                    borderLeft: '3px solid #3b82f6',
                    whiteSpace: 'pre-wrap',
                    lineHeight: 1.5,
                  }}>
                    {selectedCandidate.synopsis_snippet || result.recommended_synopsis || 'あらすじ準備中...'}
                  </div>
                </div>

                {onSelectTitle && (
                  <button
                    type="button"
                    onClick={() => handleApplyTitle(selectedCandidate)}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      background: '#10b981',
                      color: '#ffffff',
                      fontWeight: 700,
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '0.95rem',
                    }}
                  >
                    ✨ このタイトルとあらすじを採用する
                  </button>
                )}
              </div>
            ) : (
              <div style={{ color: '#6b7280', fontSize: '0.875rem' }}>
                左のリストからタイトルを選択してください
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
