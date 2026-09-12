import React from "react";

interface WizardStepProps {
  stepNumber: number;
  totalSteps: number;
  title: string;
  description: string;
  onNext: () => void;
  onSkip: () => void;
  targetElementId?: string;
}

export const WizardStep: React.FC<WizardStepProps> = ({
  stepNumber,
  totalSteps,
  title,
  description,
  onNext,
  onSkip,
  targetElementId,
}) => {
  return (
    <div className="wizard-overlay">
      <div className="wizard-panel">
        <div className="wizard-header">
          <span className="wizard-step-count">Step {stepNumber} / {totalSteps}</span>
          <button className="wizard-skip-btn" onClick={onSkip}>
            スキップ
          </button>
        </div>
        <div className="wizard-body">
          <h3 className="wizard-title">{title}</h3>
          <p className="wizard-description">{description}</p>
        </div>
        <div className="wizard-footer">
          <button className="wizard-next-btn" onClick={onNext}>
            次へ進む →
          </button>
        </div>
      </div>
      {targetElementId && (
        <div 
          className="wizard-highlight" 
          style={{ 
            // The actual positioning will be handled by CSS/JS based on the targetElementId
            // For now, we provide the marker.
          }} 
          data-target={targetElementId} 
        />
      )}
    </div>
  );
};
