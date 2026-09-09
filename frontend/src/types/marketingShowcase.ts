export interface BookShowcaseData {
  title: string;
  author: string;
  content: string; // 縦書きで表示される本文
  theme: ReaderTheme;
}

export interface MarketingPromoData {
  title: string;
  tagline: string; // 一行あらすじ
  catchcopy: string; // 魅力的な煽り文句
  hashtags: string[]; // ハッシュタグ列挙
}

export type ReaderTheme = 'light' | 'sepia' | 'dark';