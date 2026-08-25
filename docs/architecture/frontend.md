# フロントエンドアーキテクチャ

## 概要
このドキュメントは、AutoNovelのフロントエンドアーキテクチャを説明します。

## テクノロジースタック
- React 18
- TypeScript
- Vite
- Tailwind CSS
- Zustand (状態管理)
- React Router v6 (ルーティング)
- Axios (API通信)

## ディレクトリ構造
```
frontend/src/
├── components/           # 再利用可能なUIコンポーネント
│   ├── layout/           # レイアウトコンポーネント (Header, Sidebar, etc.)
│   ├── tabs/             # 各タブページコンポーネント
│   ├── ui/               # 基本UIコンポーネント (Button, Input, etc.)
│   ├── write/            # 執筆関連コンポーネント
│   ├── ...               # その他のコンポーネント
├── hooks/                # カスタムフック
├── store/                # Zustandストア
├── api/                  # APIクライアント
├── utils/                # ユーティリティ関数
├── routes/               # ルーティング設定
└── App.tsx               # ルートコンポーネント
```

## ルーティング
- React Router v6 を使用し、`frontend/src/router.tsx` でルートを定義
- 各タブは遅延ロード (`React.lazy`) され、`Suspense` でラップされる
- ルート一覧:
  - `/landing` - ホームページ
  - `/books` - 作品一覧
  - `/plots` - プロット設計
  - `/write` - 執筆画面
  - `/analytics` - 品質＆販促分析
  - `/planning` - 企画立案
  - `/style-lab` - 文体ラボ
  - `/audit` - 品質監査
  - `/monitor` - 進捗モニター
  - `/strategy` - 戦略分析
  - `/import` - インポート

## 状態管理
- Zustand を使用し、`src/store` ディレクトリにストアを分割
  - `useBookStore.ts` - 書籍、章、プロット、聖書などのデータ
  - `useUIStore.ts` - UI状態 (モーダルオープン状況、エラーなど)
  - `useTaskStore.ts` - バックグラウンドタスクの状態
  - `useWritingStore.ts` - 執筆パラメータ
  - `useUserSettingsStore.ts` - ユーザー設定 (APIキー、モデルタイプなど)
  - `useEasyModeStore.ts` - イージーモードの設定
- ストアはコンポーネントからフックを使ってアクセス

## データフェッチ
- API通信は `src/api/` ディレクトリの関数を通じて行われる
- カスタムフック (例: `useBooks`, `useBookDetails`) がデータフェッチと状態更新をラップ
- ローディング状態とエラー状態はストアまたはフック内で管理

## スタイルシステム
- Tailwind CSS を使用し、`tailwind.config.js` でデザイントークンを定義
- コンポーネントは `src/components/ui/` にある基本コンポーネントを組み合わせて構築
- ダークモードは `useThemeStore` (または CSS カスタムプロパティ) で実装予定

## アクセシビリティ
- 基本的なアクセシビリティを考慮し、ARIAラベル、キーボードナビゲーション、フォーカス管理を実装
- axe-core を使用した自動テストをCIに組み込み

## パフォーマンス最適化
- コードスプリッティングにより、初期バンドルサイズを削減
- 遅延ロードにより、必要なタブのみをロード
- React.memo と useCallback, useMemo を適切に使用して再レンダリングを防止