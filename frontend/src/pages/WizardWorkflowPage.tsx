import React, { useState, useCallback } from 'react';
import { Step1PlotInput } from '../components/wizard/Step1PlotInput';
import { Step2StructureReview, OutlineItem } from '../components/wizard/Step2StructureReview';
import { Step3InteractiveWriting } from '../components/wizard/Step3InteractiveWriting';
import { expandBeats, saveWizardBook, BeatItem, ExpandBeatsRequest, WizardBookData } from '../api/wizard';

type PlotData = {
  title: string;
  genre: string;
  synopsis: string;
  targetChapters: number;
  cheatScale: number;
  growthCurve: string;
  systemAssist: number;
  costSeverity: number;
  beats: BeatItem[];
};

export const WizardWorkflowPage: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);
  const [plotData, setPlotData] = useState<PlotData | null>(null);
  const [outlines, setOutlines] = useState<OutlineItem[]>([]);
  const [bookId, setBookId] = useState<number | null>(null);
  const [branchId, setBranchId] = useState<number>(1);
  const [currentEpisode, setCurrentEpisode] = useState(1);
  const [chapterContent, setChapterContent] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const convertBeatsToOutlines = (beats: BeatItem[]): OutlineItem[] => {
    return beats.map((beat) => ({
      episode: beat.episode,
      title: beat.title,
      outline: beat.outline,
      cliffhangerType: beat.cliffhanger_type as OutlineItem['cliffhangerType'],
      sensoryFocus: beat.sensory_focus || [],
      foreshadowingNotes: beat.foreshadowing_notes || '',
    }));
  };

  const handleStep1Complete = (data: PlotData) => {
    setPlotData(data);
    // Convert the API-generated beats into outline items for Step 2
    setOutlines(convertBeatsToOutlines(data.beats));
    setCurrentStep(2);
  };

  const handleStep2Confirm = async (confirmedOutlines: OutlineItem[]) => {
    if (!plotData) return;
    setIsSaving(true);
    setError(null);

    try {
      // Save the book data to DB and transition to Step 3
      const wizardData: WizardBookData = {
        title: plotData.title,
        genre: plotData.genre,
        synopsis: plotData.synopsis,
        target_chapters: plotData.targetChapters,
        cheat_scale: plotData.cheatScale,
        growth_curve: plotData.growthCurve,
        system_assist: plotData.systemAssist,
        cost_severity: plotData.costSeverity,
        beats: confirmedOutlines.map((outline) => ({
          episode: outline.episode,
          title: outline.title,
          outline: outline.outline,
          cliffhanger_type: outline.cliffhangerType || 'New Crisis',
          sensory_focus: outline.sensoryFocus || [],
          foreshadowing_notes: outline.foreshadowingNotes || '',
        })),
      };

      const result = await saveWizardBook(wizardData);
      setBookId(result.book_id);
      setBranchId(result.branch_id);
      setOutlines(confirmedOutlines);
      setCurrentStep(3);
      setCurrentEpisode(1);
      setChapterContent('');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '書籍データの保存に失敗しました';
      setError(message);
      // Still allow proceeding to Step 3 in offline/demo mode
      setCurrentStep(3);
      setCurrentEpisode(1);
      setChapterContent('');
    } finally {
      setIsSaving(false);
    }
  };

  const handleGenerateNext = useCallback(async () => {
    if (!bookId) return;
    setIsGenerating(true);
    try {
      // The SSE stream subscription inside Step3InteractiveWriting handles
      // real-time progress; when complete, the chapter content is updated
      setCurrentEpisode((prev) => prev + 1);
      setChapterContent('');
    } finally {
      setIsGenerating(false);
    }
  }, [bookId]);

  const handleRegenerate = useCallback(() => {
    setChapterContent('');
    setCurrentEpisode((prev) => prev);
  }, []);

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      {error && (
        <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-200 text-sm">
          {error}
        </div>
      )}

      {currentStep === 1 && <Step1PlotInput onNext={handleStep1Complete} />}
      {currentStep === 2 && (
        <Step2StructureReview
          outlines={outlines}
          onBack={() => setCurrentStep(1)}
          onConfirm={handleStep2Confirm}
          onUpdateOutlines={setOutlines}
          isSaving={isSaving}
        />
      )}
      {currentStep === 3 && (
        <Step3InteractiveWriting
          book_id={bookId ?? 0}
          ep_num={currentEpisode}
          branch_id={branchId}
          chapterTitle={outlines[currentEpisode - 1]?.title || '第1話'}
          chapterContent={chapterContent}
          isGenerating={isGenerating}
          onGenerateNext={handleGenerateNext}
          onRegenerate={handleRegenerate}
        />
      )}
    </div>
  );
};