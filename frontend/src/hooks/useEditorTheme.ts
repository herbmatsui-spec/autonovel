import { useState, useEffect } from "react";
import { EditorThemeConfig } from "../types/editorLayout";

export const useEditorTheme = () => {
  const [theme, setTheme] = useState<EditorThemeConfig['theme']>('dark');
  const [fontFamily, setFontFamily] = useState<EditorThemeConfig['fontFamily']>('serif');
  const [fontSize, setFontSize] = useState<EditorThemeConfig['fontSize']>('medium');
  const [lineHeight, setLineHeight] = useState<EditorThemeConfig['lineHeight']>('normal');
  const [showManuscriptGrid, setShowManuscriptGrid] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('autonovel.editorThemeConfig');
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as Partial<EditorThemeConfig>;
        if (parsed.theme) setTheme(parsed.theme);
        if (parsed.fontFamily) setFontFamily(parsed.fontFamily);
        if (parsed.fontSize) setFontSize(parsed.fontSize);
        if (parsed.lineHeight) setLineHeight(parsed.lineHeight);
        if (parsed.showManuscriptGrid !== undefined) setShowManuscriptGrid(parsed.showManuscriptGrid);
      } catch (e) {
        console.error('Failed to parse theme config from localStorage', e);
      }
    }
  }, []);

  const updateTheme = (newConfig: Partial<EditorThemeConfig>) => {
    if (newConfig.theme) setTheme(newConfig.theme);
    if (newConfig.fontFamily) setFontFamily(newConfig.fontFamily);
    if (newConfig.fontSize) setFontSize(newConfig.fontSize);
    if (newConfig.lineHeight) setLineHeight(newConfig.lineHeight);
    if (newConfig.showManuscriptGrid !== undefined) setShowManuscriptGrid(newConfig.showManuscriptGrid);
  };

  return {
    theme,
    fontFamily,
    fontSize,
    lineHeight,
    showManuscriptGrid,
    updateTheme,
  };
};