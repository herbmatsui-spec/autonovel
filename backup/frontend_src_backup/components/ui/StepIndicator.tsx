interface StepIndicatorProps {
  steps: { label: string; icon?: string }[];
  currentStep: number;
}

export function StepIndicator({ steps, currentStep }: StepIndicatorProps) {
  return (
    <div className="flex items-center justify-between mb-6">
      {steps.map((step, index) => {
        const isActive = index === currentStep;
        const isCompleted = index < currentStep;

        return (
          <div key={index} className="flex flex-col items-center flex-1">
            <div className="flex items-center w-full">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : isCompleted
                    ? 'bg-emerald-500 text-white'
                    : 'bg-muted text-muted-foreground'
                }`}
              >
                {isCompleted ? '✓' : index + 1}
              </div>
              {index < steps.length - 1 && (
                <div
                  className={`h-0.5 flex-1 mx-1 ${
                    isCompleted ? 'bg-emerald-500' : 'bg-muted'
                  }`}
                />
              )}
            </div>
            <span
              className={`text-2xs mt-1 text-center ${
                isActive ? 'text-primary font-semibold' : 'text-muted-foreground'
              }`}
            >
              {step.icon && <span className="mr-0.5">{step.icon}</span>}
              {step.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}