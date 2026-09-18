import React, { useState } from 'react';
import { BeatItem } from '../../api/wizard';

export interface OutlineItem {
  episode: number;
  title: string;
  outline: string;
  cliffhangerType?: 'New Crisis' | 'Shocking Truth' | 'Quiet Foreshadowing';
  sensoryFocus?: string[];
  foreshadowingNotes?: string;
}

interface Step2Props {
  outlines: OutlineItem[];
  onBack: () => void;
  onConfirm: (outlines: OutlineItem[]) => void;
  onUpdateOutlines?: (outlines: OutlineItem[]) => void;
  isSaving?: boolean;
}

const CLIFFHANGER_TYPES: Array<'New Crisis' | 'Shocking Truth' | 'Quiet Foreshadowing'> = [
  'New Crisis',
  'Shocking Truth',
  'Quiet Foreshadowing',
];

const SENSORY_OPTIONS = [
  'visual',
  'auditory',
  'olfactory',
  'tactile',
  'gustatory',
  'metaphor',
];

export const Step2StructureReview: React.FC<Step2Props> = ({ 
  outlines: initialOutlines, 
  onBack, 
  onConfirm,
  onUpdateOutlines,
  isSaving = false,
}) => {
  const [outlines, setOutlines] = useState<OutlineItem[]>(initialOutlines);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [isDirty, setIsDirty] = useState(false);

  const handleOutlineChange = (index: number, field: keyof OutlineItem, value: string | string[]) => {
    const newOutlines = [...outlines];
    newOutlines[index] = { ...newOutlines[index], [field]: value };
    setOutlines(newOutlines);
    setIsDirty(true);
    onUpdateOutlines?.(newOutlines);
  };

  const handleAddBeat = () => {
    const newEpisode = outlines.length + 1;
    const newBeat: OutlineItem = {
      episode: newEpisode,
      title: `第${newEpisode}話: 新しいエピソード`,
      outline: 'ここにあらすじを入力してください',
      cliffhangerType: 'New Crisis',
      sensoryFocus: ['visual'],
      foreshadowingNotes: '',
    };
    const newOutlines = [...outlines, newBeat];
    setOutlines(newOutlines);
    setIsDirty(true);
    onUpdateOutlines?.(newOutlines);
  };

  const handleDeleteBeat = (index: number) => {
    if (outlines.length <= 1) return;
    const newOutlines = outlines.filter((_, i) => i !== index).map((item, i) => ({
      ...item,
      episode: i + 1,
    }));
    setOutlines(newOutlines);
    setIsDirty(true);
    onUpdateOutlines?.(newOutlines);
  };

  const handleMoveUp = (index: number) => {
    if (index === 0) return;
    const newOutlines = [...outlines];
    [newOutlines[index], newOutlines[index - 1]] = [newOutlines[index - 1], newOutlines[index]];
    newOutlines.forEach((item, i) => { item.episode = i + 1; });
    setOutlines(newOutlines);
    setIsDirty(true);
    onUpdateOutlines?.(newOutlines);
  };

  const handleMoveDown = (index: number) => {
    if (index === outlines.length - 1) return;
    const newOutlines = [...outlines];
    [newOutlines[index], newOutlines[index + 1]] = [newOutlines[index + 1], newOutlines[index]];
    newOutlines.forEach((item, i) => { item.episode = i + 1; });
    setOutlines(newOutlines);
    setIsDirty(true);
    onUpdateOutlines?.(newOutlines);
  };

  const getCliffhangerStyle = (type?: string) => {
    switch (type) {
      case 'Shocking Truth': return 'bg-red-900 text-red-200 border border-red-700';
      case 'New Crisis': return 'bg-amber-900 text-amber-200 border border-amber-700';
      default: return 'bg-purple-900 text-purple-200 border border-purple-700';
    }
  };

  return (
    <div className="wizard-step step2-container p-6 bg-slate-900 text-white rounded-xl shadow-lg">
      <h2 className="text-2xl font-bold mb-2 text-emerald-400">Step 2: 全章構成と五感ビート・引きの確認</h2>
      <p className="text-slate-400 mb-4 text-sm">
        読者の離脱を防ぐ「クリフハンガー3分類」と「五感タグ配分」です。確認して執筆へ進みましょう。
      </p>

      <div className="flex gap-2 mb-4">
        <button
          onClick={handleAddBeat}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded text-sm font-medium transition-colors"
        >
          + ビートを追加
        </button>
        {isDirty && (
          <span className="text-xs text-amber-400 self-center px-2">
            未保存の変更があります
          </span>
        )}
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto pr-2 mb-6">
        {outlines.map((item, index) => (
          <div key={item.episode} className="p-3.5 bg-slate-800 border border-slate-700 rounded-lg flex flex-col gap-2">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sky-300">第{item.episode}話:</span>
                <input
                  type="text"
                  value={item.title}
                  onChange={(e) => handleOutlineChange(index, 'title', e.target.value)}
                  className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-sky-500 w-64"
                />
                <div className="flex gap-1">
                  <button
                    onClick={() => handleMoveUp(index)}
                    disabled={index === 0}
                    className="p-1 text-sky-400 hover:text-sky-300 disabled:opacity-30 disabled:cursor-not-allowed"
                    title="上に移動"
                  >
                    ↑
                  </button>
                  <button
                    onClick={() => handleMoveDown(index)}
                    disabled={index === outlines.length - 1}
                    className="p-1 text-sky-400 hover:text-sky-300 disabled:opacity-30 disabled:cursor-not-allowed"
                    title="下に移動"
                  >
                    ↓
                  </button>
                  <button
                    onClick={() => handleDeleteBeat(index)}
                    disabled={outlines.length <= 1}
                    className="p-1 text-red-400 hover:text-red-300 disabled:opacity-30 disabled:cursor-not-allowed"
                    title="削除"
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div className="flex gap-2 items-center">
                {item.cliffhangerType && (
                  <select
                    value={item.cliffhangerType}
                    onChange={(e) => handleOutlineChange(index, 'cliffhangerType', e.target.value as 'New Crisis' | 'Shocking Truth' | 'Quiet Foreshadowing')}
                    className={`text-xs px-2 py-0.5 rounded font-medium border ${getCliffhangerStyle(item.cliffhangerType)}`}
                  >
                    {CLIFFHANGER_TYPES.map((type) => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                )}
                {item.foreshadowingNotes && (
                  <span className="text-xs px-2 py-0.5 bg-sky-900 text-sky-200 rounded border border-sky-700">
                    伏線: {item.foreshadowingNotes}
                  </span>
                )}
              </div>
            </div>
            
            <textarea
              value={item.outline}
              onChange={(e) => handleOutlineChange(index, 'outline', e.target.value)}
              rows={2}
              className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-sky-500 resize-none"
              placeholder="あらすじを入力..."
            />
            
            <div className="flex flex-wrap gap-1">
              <span className="text-xs text-slate-400 self-center mr-2">五感描写:</span>
              {SENSORY_OPTIONS.map((sense) => (
                <label key={sense} className="inline-flex items-center gap-1 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={item.sensoryFocus?.includes(sense) || false}
                    onChange={(e) => {
                      const current = item.sensoryFocus || [];
                      const newFocus = e.target.checked
                        ? [...current, sense]
                        : current.filter((s) => s !== sense);
                      handleOutlineChange(index, 'sensoryFocus', newFocus);
                    }}
                    className="accent-emerald-500"
                  />
                  <span className="text-xs text-emerald-400">#{sense}</span>
                </label>
              ))}
            </div>
            
            <div className="flex gap-2">
              <span className="text-xs text-slate-400 self-center">伏線メモ:</span>
              <input
                type="text"
                value={item.foreshadowingNotes || ''}
                onChange={(e) => handleOutlineChange(index, 'foreshadowingNotes', e.target.value)}
                className="flex-1 bg-slate-700 border border-slate-600 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-sky-500"
                placeholder="伏線メモ（任意）"
              />
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-4">
        <button
          onClick={onBack}
          className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 rounded font-semibold transition-colors"
        >
          ← 戻ってプロットを修正
        </button>
        <button
          onClick={() => onConfirm(outlines)}
          disabled={isSaving}
          className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-900 disabled:cursor-not-allowed rounded font-semibold transition-colors"
        >
          {isSaving ? '保存中...' : '構成を確定して執筆を開始する →'}
        </button>
      </div>
    </div>
  );
};