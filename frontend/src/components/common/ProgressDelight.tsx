import React, { useState, useEffect } from 'react';
import { useNovelContext } from '../../context/NovelContext';

interface ProgressDelightProps {
  isVisible: boolean;
  onComplete?: () => void;
}

interface ThinkingStep {
  id: string;
  title: string;
  description: string;
  progress: number;
  icon: string;
  isComplete: boolean;
}

const defaultThinkingSteps: ThinkingStep[] = [
  {
    id: 'character-grief',
    title: '🧠 主人公の心理的葛藤を設計中',
    description: 'キャラクターの感情的な衝突と動機を深く掘り下げ、中盤の転落ポイントを作成します',
    progress: 25,
    icon: '🧠',
    isComplete: false,
  },
  {
    id: ' Foreshadowing',
    title: '⚡ 伏線の整合性を過去ログと照合中',
    description: '前回までのエピソードとの物語の整合性を確認し、重要な伏線を再確認します',
    progress: 50,
    icon: '⚡',
    isComplete: false,
  },
  {
    id: ' Climax',
    title: '✍️ クライマックスのカタルシスを描写中',
    description: '物語の最高潮となる場面を描写し、読者の感情を最大限に高めます',
    progress: 80,
    icon: '✍️',
    isComplete: false,
  },
  {
    id: ' polish',
    title: '✨ 誤字脱字と文体リズムを最終推敲中',
    description: '文章の微調整を行い、テンポとリズムを最適化します',
    progress: 95,
    icon: '✨',
    isComplete: false,
  },
];

export const ProgressDelight: React.FC<ProgressDelightProps> = ({
  isVisible,
  onComplete,
}) => {
  const {
    currentEpNum,
    selectedBook,
    character,
  } = useNovelContext();

  const [steps, setSteps] = useState<ThinkingStep[]>(defaultThinkingSteps);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [startTime, setStartTime] = useState<number | null>(null);

  useEffect(() => {
    if (!isVisible) {
      // Reset when not visible
      setSteps(defaultThinkingSteps.map((step, index) => ({
        ...step,
        isComplete: index < currentStepIndex,
        progress: index < currentStepIndex ? 100 : step.progress,
      })));
      setCurrentStepIndex(0);
      setIsAnimating(false);
      setStartTime(null);
    }
  }, [isVisible]);

  useEffect(() => {
    if (!isVisible || !startTime) return;

    const totalDuration = 60000; // 1話生成の60秒
    const elapsed = Date.now() - startTime;
    const progressPercent = Math.min((elapsed / totalDuration) * 100, 100);

    setSteps(prev => prev.map((step, index) => {
      if (index === 0 && progressPercent >= 25) {
        return { ...step, isComplete: true, progress: 25 };
      }
      if (index === 1 && progressPercent >= 50) {
        return { ...step, isComplete: true, progress: 50 };
      }
      if (index === 2 && progressPercent >= 80) {
        return { ...step, isComplete: true, progress: 80 };
      }
      if (index === 3 && progressPercent >= 95) {
        return { ...step, isComplete: true, progress: 95 };
      }
      return step;
    }));

    if (progressPercent >= 100 && onComplete) {
      onComplete();
    }
  }, [startTime, isVisible, onComplete]);

  const handleStart = () => {
    setStartTime(Date.now());
    setIsAnimating(true);
  };

  const getThemeClasses = () => {
    return 'progress-delight';
  };

  if (!isVisible) return null;

  return (
    <div className={getThemeClasses()} style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(10, 14, 23, 0.95)',
      backdropFilter: 'blur(8px)',
      zIndex: 2000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '800px',
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: 'var(--radius-lg)',
        padding: '40px',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5)',
        textAlign: 'center'
      }}>
        {!startTime ? (
          <div>
            <h2 style={{
              fontSize: '2rem',
              fontWeight: 700,
              color: 'var(--accent-purple)',
              marginBottom: '16px'
            }}>
              📖 {selectedBook?.title || "小説"} {currentEpNum}話 生成中...
            </h2>
            <p style={{
              fontSize: '1.1rem',
              color: 'var(--text-muted)',
              marginBottom: '32px',
              lineHeight: 1.6
            }}>
              1話あたり30～60秒の生成時間を、物語の執筆プロセスに変えて楽しみながら待ってください。<br />
              物語が完成するまでお楽しみに...
            </p>
            <div style={{ marginTop: '32px' }}>
              <button
                onClick={handleStart}
                style={{
                  padding: '16px 32px',
                  borderRadius: '8px',
                  border: 'none',
                  backgroundColor: 'var(--accent-purple)',
                  color: 'white',
                  fontSize: '1.1rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  boxShadow: '0 4px 20px var(--accent-glow)'
                }}
              >
                🎭 生成プロセスを開始
              </button>
            </div>
          </div>
        ) : (
          <div>
            <h3 style={{
              fontSize: '1.5rem',
              fontWeight: 700,
              color: 'var(--accent-cyan)',
              marginBottom: '32px'
            }}>
              物語があなたのために生まれています...
            </h3>

            <div style={{ marginBottom: '32px' }}>
              {steps.map((step, index) => (
                <div
                  key={step.id}
                  style={{
                    marginBottom: '24px',
                    padding: '20px',
                    backgroundColor: step.isComplete ?
                      'rgba(16, 185, 129, 0.15)' :
                      index === currentStepIndex ?
                      'rgba(139, 92, 246, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    borderRadius: '8px',
                    border: step.isComplete ?
                      '1px solid rgba(16, 185, 129, 0.5)' :
                      index === currentStepIndex ?
                      '2px solid var(--accent-purple)' : '1px solid var(--border-color)',
                    transition: 'all 0.3s ease',
                    opacity: step.isComplete ? 1 : (index === currentStepIndex ? 1 : 0.6)
                  }}
                >
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                    marginBottom: step.isComplete || index === currentStepIndex ? '12px' : '0'
                  }}>
                    <span style={{ fontSize: '2rem' }}>{step.icon}</span>
                    <div style={{ flex: 1, textAlign: 'left' }}>
                      <h4 style={{
                        fontSize: '1.1rem',
                        fontWeight: 700,
                        color: step.isComplete ? '#10b981' :
                               index === currentStepIndex ? 'var(--accent-purple)' : 'var(--text-muted)',
                        margin: 0,
                        marginBottom: '4px'
                      }}>
                        {step.title}
                      </h4>
                      <p style={{
                        fontSize: '0.95rem',
                        color: 'var(--text-muted)',
                        margin: 0,
                        lineHeight: 1.5
                      }}>
                        {step.description}
                      </p>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      {step.isComplete ? (
                        <span style={{ color: '#10b981', fontWeight: 600, fontSize: '1.2rem' }}>✓</span>
                      ) : index === currentStepIndex ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{ width: '24px', height: '24px' }}>
                            <div style={{
                              width: '100%',
                              height: '100%',
                              borderRadius: '50%',
                              border: '2px solid var(--accent-purple)',
                              borderTopColor: 'transparent',
                              animation: 'spin 1s linear infinite'
                            }} />
                          </div>
                          <span style={{ color: 'var(--accent-purple)', fontSize: '0.9rem' }}>処理中...</span>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>{step.progress}%</span>
                      )}
                    </div>
                  </div>

                  {index === currentStepIndex && !step.isComplete && (
                    <div style={{ marginTop: '16px' }}>
                      <div style={{
                        width: '100%',
                        height: '6px',
                        backgroundColor: 'rgba(255, 255, 255, 0.1)',
                        borderRadius: '3px',
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          width: `${step.progress}%`,
                          height: '100%',
                          backgroundColor: 'var(--accent-purple)',
                          transition: 'width 0.5s ease'
                        }} />
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div style={{ marginTop: '32px' }}>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                進行状況: {steps.filter(s => s.isComplete).length}/{steps.length} 完了
              </p>
              <div style={{
                width: '100%',
                height: '8px',
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                borderRadius: '4px',
                marginTop: '8px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${(steps.filter(s => s.isComplete).length / steps.length) * 100}%`,
                  height: '100%',
                  backgroundColor: '#10b981',
                  transition: 'width 0.5s ease'
                }} />
              </div>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};