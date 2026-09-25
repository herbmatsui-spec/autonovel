import React from 'react';
import { NextBeatsPanel } from '../editor/NextBeatsPanel';

interface NextEpisodeSuggestionPanelProps {
  currentText: string;
  genre?: string;
  bookId?: number;
  onApplyBeat: (content: string, mode: 'append' | 'replace_all') => void;
  onToast?: (msg: string, type: 'success' | 'error' | 'info') => void;
}

export const NextEpisodeSuggestionPanel: React.FC<NextEpisodeSuggestionPanelProps> = (props) => {
  return <NextBeatsPanel {...props} />;
};

export default NextEpisodeSuggestionPanel;
