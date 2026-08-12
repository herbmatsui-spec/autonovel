# Stray Directory Report

## 新しいフォルダー/
- パス: `新しいフォルダー/manual_processor/`
- 内容: `config/`, `src/`, `tests/` を含むが、kaku-hegemony (Autonovel) プロジェクト本体とは無関係の独立ツールと思われる。
- 判定: 迷子ファイル・不要ディレクトリとして削除対象。

## backup/
- `backup/frontend_src_backup/`
- `backup/streamlit_app_backup/`
- 判定: 旧フロントエンド/Streamlit のバックアップ。現在の正規実装は `frontend/` (React) および `src/` であるため削除対象。

## archive/ と .archive/
- `archive/` を正規のアーカイブディレクトリとし、`.archive/` は統合・削除対象。

## claude2.code-workspace_dir/
- 単一の `test.txt` のみを含む作業用ディレクトリ。削除対象。

## .kilo/worktrees/tabby-child/
- 古い worktree の残骸。削除対象。
