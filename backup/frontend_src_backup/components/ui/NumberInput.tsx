interface NumberInputProps {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
}

export function NumberInput({ label, value, onChange, min, max, step, disabled }: NumberInputProps) {
  return (
    <div>
      <label className="block text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>
        {label}
      </label>
      <input
        type="number"
        value={value}
        onChange={(e) => {
          const raw = e.target.value;
          const parsed = step && step < 1 ? parseFloat(raw) : parseInt(raw, 10);
          onChange(Number.isNaN(parsed) ? (min ?? 0) : parsed);
        }}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
      />
    </div>
  );
}
