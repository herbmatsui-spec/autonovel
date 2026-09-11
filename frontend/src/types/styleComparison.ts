export interface StyleComparisonScene {
  id: "action" | "dialogue" | "psychology";
  title: string;
  standardText: string;
  styledTextMap: Record<string, string>; // style_idごとの変換後サンプル
}

export interface StyleTuningParams {
  kemeritsu: number; // 1-5
  bodyStop: number; // 0-100
  metaphor: number; // 0-100
}

export interface CustomStyleLibraryItem {
  id: string;
  name: string;
  params: StyleTuningParams;
}