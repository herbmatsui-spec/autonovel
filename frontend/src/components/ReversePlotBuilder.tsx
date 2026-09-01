import React, { useState } from 'react';
import { REVERSE_PLOT_STEPS } from '../data/reversePlotSteps';
import { ReversePlotAnswers, GeneratedPlotStructure } from '../types/reversePlot';
import { generateReversePlot } from '../api/reversePlot';

interface ReversePlotBuilderProps {
  onComplete: (structure: GeneratedPlotStructure) => void;
  onCancel: () => void;
  targetEpisodes: number;
  genre: string;
}

const STEP_KEYS = ['emotionalGoal', 'sacrifice', 'coreConflict', 'openingHook'] as const;

export const ReversePlotBuilder: React.FC<ReversePlotBuilderProps> = ({
  onComplete,
  onCancel,
  targetEpisodes,
  genre,
}) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [answers, setAnswers] = useState<Partial<ReversePlotAnswers>>({});
  const [generating, setGenerating] = useState(false);
  const [preview, setPreview] = useState<GeneratedPlotStructure | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleOptionSelect = (value: string) => {
    const key = STEP_KEYS[currentStep - 1];
    setAnswers(prev => ({ ...prev, [key]: value }));
    setError(null);
  };

  const handleNext = async () => {
    if (currentStep < 4) {
      setCurrentStep(prev => prev + 1);
    } else {
      await generatePlotStructure();
    }
  };

  const handleBack = () => {
    setCurrentStep(prev => prev - 1);
  };

  const generatePlotStructure = async () => {
    setGenerating(true);
    setError(null);
    try {
      const data = await generateReversePlot(answers, targetEpisodes, genre);
      setPreview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '不明なエラー');
    } finally {
      setGenerating(false);
    }
  };

  const step = REVERSE_PLOT_STEPS[currentStep - 1];
  const currentKey = STEP_KEYS[currentStep - 1];
  const selectedValue = answers[currentKey];

  return (
    <div className="reverse-plot-builder card" data-testid="reverse-plot-builder">
      <div className="progress-bar">
        {REVERSE_PLOT_STEPS.map((s, i) => (
          <div key={s.step} className={`step ${i + 1 <= currentStep ? 'active' : ''}`}>
            <div className="step-number">{s.step}</div>
            <div className="step-title">{s.title}</div>
          </div>
        ))}
      </div>

      <div className="step-content">
        <h3 style={{ marginBottom: '8px', fontSize: '1.1rem' }}>{step.title}</h3>
        <p style={{ color: 'var(--text-muted)', marginBottom: '16px', lineHeight: 1.5 }}>{step.question}</p>
        <div style={{ fontSize: '0.85rem', color: 'var(--accent-primary)', marginBottom: '16px', padding: '8px 12px', background: 'rgba(167, 139, 250, 0.1)', borderRadius: '6px' }}>
          💡 {step.aiHint}
        </div>

        <div className="options-grid">
          {step.options.map(opt => (
            <button
              key={opt.value}
              type="button"
              className={`option-card ${selectedValue === opt.value ? 'selected' : ''}`}
              onClick={() => handleOptionSelect(opt.value)}
              disabled={generating}
              data-testid={`option-${opt.value}`}
            >
              <div style={{ fontWeight: 600, marginBottom: '8px' }}>{opt.label}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>{opt.example}</div>
            </button>
          ))}
        </div>

        {error && (
          <div style={{ marginTop: '16px', padding: '12px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid var(--accent-danger)', borderRadius: '6px', color: 'var(--accent-danger)', fontSize: '0.85rem' }}>
            {error}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '24px' }}>
        <button 
          type="button"
          onClick={handleBack} 
          disabled={currentStep === 1 || generating}
          className="btn btn-secondary"
        >
          ← 戻る
        </button>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button type="button" onClick={onCancel} className="btn btn-secondary" disabled={generating}>
            キャンセル
          </button>
          {currentStep < 4 ? (
            <button type="button" onClick={handleNext} className="btn btn-primary" disabled={!selectedValue || generating} data-testid="btn-next-step">
              次へ →
            </button>
          ) : (
            <button type="button" onClick={handleNext} className="btn btn-primary" disabled={generating} data-testid="btn-generate-plot">
              {generating ? '⏳ 生成中...' : '🔮 プロット構造を生成'}
            </button>
          )}
        </div>
      </div>

      {preview && (
        <div className="preview-section" style={{ marginTop: '24px', padding: '16px', background: 'var(--card-bg, #1f1f23)', borderRadius: '8px', border: '1px solid var(--border-color)' }} data-testid="reverse-plot-preview">
          <h4 style={{ marginBottom: '12px', color: 'var(--accent-cyan)' }}>✨ 生成されたプロット構造</h4>
          
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
            {preview.arcs.map(arc => (
              <div key={arc.arc_num} style={{ background: 'rgba(255,255,255,0.05)', padding: '8px 12px', borderRadius: '6px', fontSize: '0.85rem' }}>
                <strong>{arc.title}</strong>: {arc.summary} ({arc.start_ep}〜{arc.end_ep}話)
              </div>
            ))}
          </div>

          <div style={{ maxHeight: '220px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
            {preview.episodes.map(ep => (
              <div key={ep.ep_num} style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 12px', borderRadius: '6px', fontSize: '0.8rem' }}>
                <span style={{ fontWeight: 700, color: ep.is_catharsis ? 'var(--accent-cyan)' : 'inherit' }}>
                  第{ep.ep_num}話: {ep.title}
                </span>
                <span style={{ marginLeft: '8px', color: 'var(--text-muted)' }}>{ep.one_line_summary}</span>
                {ep.is_catharsis && <span style={{ marginLeft: '8px', color: '#fbbf24' }}>⭐ カタルシス</span>}
              </div>
            ))}
          </div>

          <button type="button" onClick={() => onComplete(preview)} className="btn btn-primary" style={{ width: '100%', padding: '10px' }} data-testid="btn-confirm-plot">
            ✅ この構造を確定して執筆に反映
          </button>
        </div>
      )}
    </div>
  );
};