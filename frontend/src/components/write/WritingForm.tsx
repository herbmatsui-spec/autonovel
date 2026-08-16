import { NumberInput } from '../ui/NumberInput';

interface WritingFormProps {
  writeFrom: number;
  setWriteFrom: (val: number) => void;
  writeTo: number;
  setWriteTo: (val: number) => void;
  writePassion: number;
  setWritePassion: (val: number) => void;
  onSubmit: () => void;
  onRefineErotic: (params: { intensity: number; platform_preset: string }) => void;
  disabled: boolean;
  genre: string;
  setGenre: (val: string) => void;
  title: string;
  setTitle: (val: string) => void;
  wordCount: number;
  setWordCount: (val: number) => void;
  platform: string;
  setPlatform: (val: string) => void;
}

export function WritingForm({
  writeFrom,
  setWriteFrom,
  writeTo,
  setWriteTo,
  writePassion,
  setWritePassion,
  onSubmit,
  onRefineErotic,
  disabled,
  genre,
  setGenre,
  title,
  setTitle,
  wordCount,
  setWordCount,
  platform,
  setPlatform,
}: WritingFormProps) {
  return (
    <div className="glass-panel p-6">
      <h3 className="text-xl mb-4">✍️ エピソード自動執筆の実行</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        <div>
          <label htmlFor="writing-title" className="block text-xs mb-1">タイトル</label>
          <input
            id="writing-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full"
            disabled={disabled}
          />
        </div>
        <div>
          <label htmlFor="writing-genre" className="block text-xs mb-1">ジャンル</label>
          <select
            id="writing-genre"
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
            className="w-full"
            disabled={disabled}
          >
            <option value="fantasy">ファンタジー</option>
            <option value="slice_of_life">日常系</option>
            <option value="mystery">ミステリー</option>
            <option value="drama">ドラマ</option>
            <option value="comedy">コメディ</option>
          </select>
        </div>
        <div>
          <NumberInput
            label="1話あたり文字数"
            value={wordCount}
            onChange={setWordCount}
            min={500}
            max={10000}
            step={500}
            disabled={disabled}
          />
        </div>
        <div>
          <label htmlFor="writing-platform" className="block text-xs mb-1">プラットフォーム</label>
          <select
            id="writing-platform"
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="w-full"
            disabled={disabled}
          >
            <option value="kindle">Kindle</option>
            <option value="kakuyomu">カクヨム</option>
            <option value="naru">narou</option>
          </select>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <NumberInput
          label="執筆開始エピソード"
          value={writeFrom}
          onChange={setWriteFrom}
          min={1}
          disabled={disabled}
        />
        <NumberInput
          label="執筆終了エピソード"
          value={writeTo}
          onChange={setWriteTo}
          min={1}
          disabled={disabled}
        />
        <NumberInput
          label="パッション度 (0.0 ~ 1.0)"
          value={writePassion}
          onChange={setWritePassion}
          min={0}
          max={1}
          step={0.05}
          disabled={disabled}
        />
      </div>
      <div className="flex gap-4">
        <button className="btn btn-primary flex-1" onClick={onSubmit} disabled={disabled}>
          ⚡ 自動執筆ワークフロー実行
        </button>
        <button
          className="btn btn-secondary flex-1 border-rose-500 text-rose-500 hover:bg-rose-500/10"
          onClick={() => onRefineErotic({ intensity: 5, platform_preset: 'standard' })}
          disabled={disabled}
        >
          🔞 官能表現を洗練
        </button>
      </div>
    </div>
  );
}
