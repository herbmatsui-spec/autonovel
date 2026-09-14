export type WorkspaceLayoutMode = 'studio' | 'split' | 'zen';

export interface EditorThemeConfig {
  theme: 'dark' | 'paper' | 'sepia' | 'cyberpunk';
  fontFamily: 'serif' | 'sans' | 'mincho';
  fontSize: 'small' | 'medium' | 'large' | 'huge';
  lineHeight: 'tight' | 'normal' | 'relaxed';
  showManuscriptGrid: boolean;
}

export interface EditorFocusState {
  isZenMode: boolean;
  hideToolbars: boolean;
  dimBackground: boolean;
  targetWordCount: number;
  currentWordCount: number;
}

export interface InlineSuggestion {
  id: string;
  originalText: string;
  suggestedText: string;
  startOffset: number;
  endOffset: number;
  type: 'replace' | 'insert' | 'delete';
  status: 'pending' | 'accepted' | 'rejected';
  reason?: string;
}

export interface ZenModeConfig {
  enabled: boolean;
  autoHideCursor: boolean;
  showWordCount: boolean;
  targetWordCount: number;
  backgroundDim: number;
}

export interface EditorKeybindings {
  zenMode: string;
  aiContinue: string;
  aiProofread: string;
  toggleTheme: string;
  toggleManuscriptGrid: string;
}