export type EditorFontFamily = 'serif' | 'sans';
export type EditorFontSize = 'small' | 'medium' | 'large';

export interface EditorSettings {
  fontFamily: EditorFontFamily;
  fontSize: EditorFontSize;
  lineHeight: number;
}