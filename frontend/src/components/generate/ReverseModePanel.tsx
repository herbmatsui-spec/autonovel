import React from "react";
import { ReversePlotBuilder } from "../ReversePlotBuilder";
import type { GeneratedPlotStructure } from "../../types/reversePlot";

interface ReverseModePanelProps {
  targetEpisodes: number;
  genre: string;
  llmConfig: any;
  onTargetEpisodesChange: (value: number) => void;
  onComplete: (structure: GeneratedPlotStructure) => void;
  onCancel: () => void;
}

export default function ReverseModePanel({
  targetEpisodes,
  genre,
  llmConfig,
  onTargetEpisodesChange,
  onComplete,
  onCancel,
}: ReverseModePanelProps) {
  return (
    <ReversePlotBuilder
      onComplete={onComplete}
      onCancel={onCancel}
      targetEpisodes={targetEpisodes}
      genre={genre}
      llmConfig={llmConfig}
      onTargetEpisodesChange={onTargetEpisodesChange}
    />
  );
}