import React, { useState, useEffect } from 'react';
import { BookScoreRadarChart } from './BookScoreRadarChart';
import { BookScoreTrendChart } from './BookScoreTrendChart';
import { PDCADirectiveCard } from './PDCADirectiveCard';
import { fetchChapterBookScore, fetchBookScoreHistory, fetchPDCACycles } from '../../api/quality';

interface QualityDashboardModalProps {
  bookId: number;
  initialChapter?: number | undefined;
  chapterNumber?: number | undefined;
  onClose: () => void;
}

export const QualityDashboardModal: React.FC<QualityDashboardModalProps> = ({
  bookId,
  initialChapter,
  chapterNumber,
  onClose,
}) => {
  const [chapter, setChapter] = useState(initialChapter ?? chapterNumber ?? 1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [currentScore, setCurrentScore] = useState<any>(null);
  const [history, setHistory] = useState<any>(null);
  const [pdcaCycles, setPdcaCycles] = useState<any[]>([]);

  const fetchData = async (chapNum: number) => {
    setLoading(true);
    setError(null);
    try {
      const [scoreRes, historyRes, pdcaRes] = await Promise.all([
        fetchChapterBookScore(bookId, chapNum),
        fetchBookScoreHistory(bookId),
        fetchPDCACycles(bookId, chapNum),
      ]);

      setCurrentScore(scoreRes);
      setHistory(historyRes);
      setPdcaCycles(pdcaRes);
    } catch (e: any) {
      setError(e.message || 'データの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(chapter);
  }, [chapter]);

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
        <div className="bg-white p-8 rounded-xl shadow-xl flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-gray-600 font-medium">品質データを解析中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
        <div className="bg-white p-8 rounded-xl shadow-xl max-w-md w-full text-center space-y-4">
          <div className="text-red-500 text-4xl">⚠️</div>
          <h3 className="text-lg font-bold text-gray-900">エラーが発生しました</h3>
          <p className="text-gray-600">{error}</p>
          <button 
            onClick={onClose}
            className="w-full py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium transition-colors"
          >
            閉じる
          </button>
        </div>
      </div>
    );
  }

  // Prepare Radar Data
  const currentRadar = {
    structure: currentScore?.structure_score || 0,
    coherency: currentScore?.coherency_score || 0,
    factual: currentScore?.factual_grounding_score || 0,
    visual: currentScore?.visual_textual_synergy_score || 0,
    reader: currentScore?.reader_experience_score || 0,
  };

  const benchmarkRadar = history?.benchmarks ? {
    structure: history.benchmarks.structure || 0,
    coherency: history.benchmarks.coherency || 0,
    factual: history.benchmarks.factual || 0,
    visual: history.benchmarks.visual || 0,
    reader: history.benchmarks.reader || 0,
  } : undefined;

  const previousScore = history?.history
    ?.filter((h: any) => h.chapter_number === chapter)
    .slice(0, -1).pop();

  const previousRadar = previousScore ? {
    structure: previousScore.structure_score || 0,
    coherency: previousScore.coherency_score || 0,
    factual: previousScore.factual_grounding_score || 0,
    visual: previousScore.visual_textual_synergy_score || 0,
    reader: previousScore.reader_experience_score || 0,
  } : undefined;

  const trendData = history?.history?.map((h: any) => ({
    chapter: h.chapter_number,
    score: h.overall_score,
  })) || [];

  const latestCycle = pdcaCycles[pdcaCycles.length - 1];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-slate-50 rounded-2xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col border border-slate-200">
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold text-slate-800">品質ダッシュボード</h2>
            <div className="flex items-center gap-2 bg-slate-100 rounded-lg px-3 py-1">
              <button 
                onClick={() => setChapter(Math.max(1, chapter - 1))}
                className="hover:text-blue-600 transition-colors"
              >
                ←
              </button>
              <span className="text-sm font-bold text-slate-700">第 {chapter} 章</span>
              <button 
                onClick={() => setChapter(chapter + 1)}
                className="hover:text-blue-600 transition-colors"
              >
                →
              </button>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 transition-colors text-2xl"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 grid grid-cols-12 gap-6">
          {/* Left Column: Scores & Radar */}
          <div className="col-span-12 lg:col-span-5 space-y-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
              <div className="flex justify-between items-end">
                <div>
                  <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Overall Score</div>
                  <div className="text-5xl font-black text-blue-600">{currentScore?.overall_score || '0.0'}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Trend</div>
                  <div className={`text-lg font-bold ${currentScore?.trend_3ch?.trend_slope && currentScore.trend_3ch.trend_slope >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {currentScore?.trend_3ch?.trend_slope ? `${currentScore.trend_3ch.trend_slope > 0 ? '+' : ''}${currentScore.trend_3ch.trend_slope}` : 'N/A'}
                  </div>
                </div>
              </div>

              <div className="flex justify-center">
                <BookScoreRadarChart 
                  scores={currentRadar}
                  previousScores={previousRadar}
                  benchmark={benchmarkRadar}
                  size={320}
                />
              </div>

              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-2 bg-slate-50 rounded-lg border border-slate-100">
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Structure</div>
                  <div className="text-sm font-bold text-slate-700">{currentScore?.structure_score}</div>
                </div>
                <div className="p-2 bg-slate-50 rounded-lg border border-slate-100">
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Coherency</div>
                  <div className="text-sm font-bold text-slate-700">{currentScore?.coherency_score}</div>
                </div>
                <div className="p-2 bg-slate-50 rounded-lg border border-slate-100">
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Factual</div>
                  <div className="text-sm font-bold text-slate-700">{currentScore?.factual_grounding_score}</div>
                </div>
              </div>
            </div>

            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
              <div className="text-sm font-bold text-slate-700">スコア推移</div>
              <BookScoreTrendChart 
                data={trendData} 
                width={400} 
                height={200} 
              />
            </div>
          </div>

          {/* Right Column: PDCA & Directives */}
          <div className="col-span-12 lg:col-span-7 space-y-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-bold text-slate-800">最新のPDCAサイクル</h3>
                {latestCycle && (
                  <div className="flex gap-2">
                    <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-bold rounded">
                      Cycle {latestCycle.cycle_number}
                    </span>
                    <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-bold rounded">
                      {latestCycle.converged ? 'Converged' : 'In Progress'}
                    </span>
                  </div>
                )}
              </div>

              {!latestCycle ? (
                <div className="py-12 text-center text-slate-400 italic">
                  PDCA履歴が見つかりません
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                      <div className="text-[10px] text-slate-400 font-bold uppercase">Initial</div>
                      <div className="text-lg font-bold text-slate-700">{latestCycle.initial_score}</div>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                      <div className="text-[10px] text-slate-400 font-bold uppercase">Final</div>
                      <div className="text-lg font-bold text-blue-600">{latestCycle.final_score}</div>
                    </div>
                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                      <div className="text-[10px] text-slate-400 font-bold uppercase">Delta</div>
                      <div className="text-lg font-bold text-green-600">+{latestCycle.score_delta}</div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">執筆指示 (Directives)</div>
                    <div className="grid grid-cols-1 gap-3">
                      {latestCycle.directives.map((dir: any, i: number) => (
                        <PDCADirectiveCard key={i} directive={dir} />
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
