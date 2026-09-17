import React, { useState } from 'react';
import { Step1PlotInput } from '../components/wizard/Step1PlotInput';
import { Step2StructureReview, OutlineItem } from '../components/wizard/Step2StructureReview';
import { Step3InteractiveWriting } from '../components/wizard/Step3InteractiveWriting';

export const WizardWorkflowPage: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);
  const [plotData, setPlotData] = useState<any>(null);
  const [outlines, setOutlines] = useState<OutlineItem[]>([]);
  const [currentEpisode, setCurrentEpisode] = useState(1);
  const [chapterContent, setChapterContent] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleStep1Complete = (data: any) => {
    setPlotData(data);
    // 五感タグ・クリフハンガーを含むモック章立て生成
    setOutlines([
      {
        episode: 1,
        title: 'プロローグ: 始まりの予兆',
        outline: '主人公の平穏な日常と異変の胎動',
        cliffhangerType: 'Shocking Truth',
        sensoryFocus: ['sight', 'sound'],
      },
      {
        episode: 2,
        title: '旅立ちの朝',
        outline: '村を離れ最初の試練に直面する',
        cliffhangerType: 'New Crisis',
        sensoryFocus: ['smell', 'touch'],
        foreshadowingNotes: '謎のペンダント',
      },
    ]);
    setCurrentStep(2);
  };

  const handleStep2Confirm = () => {
    setCurrentStep(3);
    setChapterContent('第一話本文のサンプル。ここに対話型で執筆された章が表示されます。');
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      {currentStep === 1 && <Step1PlotInput onNext={handleStep1Complete} />}
      {currentStep === 2 && (
        <Step2StructureReview
          outlines={outlines}
          onBack={() => setCurrentStep(1)}
          onConfirm={handleStep2Confirm}
        />
      )}
      {currentStep === 3 && (
        <Step3InteractiveWriting
          currentEpisode={currentEpisode}
          chapterTitle={outlines[currentEpisode - 1]?.title || '第1話'}
          chapterContent={chapterContent}
          isGenerating={isGenerating}
          onGenerateNext={() => {
            setCurrentEpisode((prev) => prev + 1);
            setChapterContent(`第${currentEpisode + 1}話の本文を生成しました。`);
          }}
          onRegenerate={() => {
            setChapterContent((prev) => prev + "\n[リテイク完了]");
          }}
        />
      )}
    </div>
  );
};