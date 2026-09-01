import React, { useState } from 'react';
import { REVERSE_PLOT_STEPS } from '../data/reversePlotSteps';
import { ReversePlotAnswers, GeneratedPlotStructure } from '../types/reversePlot';

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
      const response = await fetch('/api/plots/reverse-generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers, targetEpisodes, genre }),
      });
      
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || '生成に失敗しました');
      }
      
      const data = await response.json();
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
    <div className="reverse-plot-builder card">
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
        <div style={{ fontSize: '0.85rem', color: 'var(--accent-primary)', marginBottom: '16px', padding: '8px 12px', background: 'var(--accent-primary-bg)', borderRadius: '6px' }}>
          💡 {step.aiHint}
        </div>

        <div className="options-grid">
          {step.options.map(opt => (
            <button
              key={opt.value}
              className={`option-card ${selectedValue === opt.value ? 'selected' : ''}`}
              onClick={() => handleOptionSelect(opt.value)}
              disabled={generating}
            >
              <div style={{ fontWeight: 600, marginBottom: '8px' }}>{opt.label}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>{opt.example}</div>
            </button>
          ))}
        </div>

        {error && (
          <div style={{ marginTop: '16px', padding: '12px', background: 'var(--accent-danger-bg)', border: '1px solid var(--accent-danger)', borderRadius: '6px', color: 'var(--accent-danger)', fontSize: '0.85rem' }}>
            {error}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '24px' }}>
        <button 
          onClick={handleBack} 
          disabled={currentStep === 1 || generating}
          className="btn btn-secondary"
        >
          ← 戻る
        </button>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={onCancel} className="btn btn-secondary" disabled={generating}>
            キャンセル
          </button>
          {currentStep < 4 ? (
            <button onClick={handleNext} className="btn btn-primary" disabled={!selectedValue || generating}>
              次へ →
            </button>
          ) : (
            <button onClick={handleNext} className="btn btn-primary" disabled={generating}>
              {generating ? '生成中...' : 'プロット構造を生成'}
            </button>
          )}
        </div>
      </div>

      {preview && (
        <div className="preview-section" style={{ marginTop: '24px', padding: '16px', background: 'var(--card-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <h4 style={{ marginBottom: '12px' }}>生成されたプロット構造</h4>
          <pre style={{ fontSize: '0.75rem', maxHeight: '300px', overflow: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {JSON.stringify(preview, null, 2)}
          </pre>
          <button onClick={() => onComplete(preview)} className="btn btn-primary" style={{ marginTop: '12px', width: '100%' }}>
            この構造で確定
          </button>
        </div>
      )}
    </div>
  );
};