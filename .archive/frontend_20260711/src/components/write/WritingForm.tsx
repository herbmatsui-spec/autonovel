import { NumberInput } from '../ui/NumberInput';

interface WritingFormProps {
  writeFrom: number;
  setWriteFrom: (val: number) => void;
  writeTo: number;
  setWriteTo: (val: number) => void;
  writePassion: number;
  setWritePassion: (val: number) => void;
  onSubmit: () => void;
  disabled: boolean;
}

export function WritingForm({
  writeFrom,
  setWriteFrom,
  writeTo,
  setWriteTo,
  writePassion,
  setWritePassion,
  onSubmit,
  disabled,
}: WritingFormProps) {
  return (
    <div className="glass-panel p-6">
      <h3 className="text-xl mb-4">✍️ エピソード自動執筆の実行</h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <NumberInput
          label="執筆開始エピソード"
          value={writeFrom}
          onChange={setWriteFrom}
          min={1}
        />
        <NumberInput
          label="執筆終了エピソード"
          value={writeTo}
          onChange={setWriteTo}
          min={1}
        />
        <NumberInput
          label="パッション度 (0.0 ~ 1.0)"
          value={writePassion}
          onChange={setWritePassion}
          min={0}
          max={1}
          step={0.05}
        />
      </div>
      <button className="btn btn-primary" onClick={onSubmit} disabled={disabled}>
        ⚡ 自動執筆ワークフロー実行
      </button>
    </div>
  );
}
