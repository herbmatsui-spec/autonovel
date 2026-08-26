# タブモジュラ化のロールバック手順書

## 概要
このドキュメントは、タブのモジュラ化と遅延ロードの変更をロールバックする手順を説明します。

## 前提条件
- Gitがインストールされていること
- リポジトリへのアクセス権があること

## ロールバック手順

1. **ブランチの特定**
   - タブモジュラ化の変更が含まれるコミットハッシュを特定します。
   - 例: `git log --oneline --grep="tab-modularization"` または `git log --oneline --grep="Implement lazy‑loaded tab routing"`

2. **一時ブランチの作成（オプション）**
   - 現在の状態を保存するために、一時ブランチを作成します。
   ```bash
   git checkout -b backup-before-rollback
   ```

3. **コミットの取り消し**
   - 特定のコミットを取り消すには、`git revert` を使用します（推奨）。
   複数のコミットがある場合は、最新のコミットから順に revert します。
   ```bash
   git revert <commit-hash>
   ```
   - または、変更を完全に元に戻す場合は、以前のコミットにリセットします（注意：これは公開履歴を書き換えます）。
   ```bash
   git reset --hard <commit-hash-before-change>
   git push --force-with-lease  # 必要に応じて
   ```

4. **特定ファイルの手動ロールバック（コミットが特定できない場合）**
   以下のファイルを以前の状態に戻します：
   - `frontend/src/App.tsx` を元の状態に戻す（ルーティングを削除し、以前のコンポーネントインポートと条件レンダリングを復元）
   - `frontend/src/router.tsx` を削除
   - `frontend/src/components/layout/AppLayout.tsx` を削除
   - `frontend/src/components/Sidebar.tsx` を元の状態に戻す（useProjectStoreのactiveTabを使用するように戻す）
   - `frontend/src/components/layout/Header.tsx` を元の状態に戻す（useProjectStoreからactiveTabを取得するように戻す）
   - `frontend/src/components/layout/PageHeader.tsx` を元の状態に戻す（同様に）
   - `frontend/src/store/useProjectStore.ts` を元の状態に戻す（activeTabとsetActiveTabを復元）
   - 各タブコンポーネント（LandingTab, BooksTab, PlotsTab, WriteTab, AnalyticsTab, PlanningTab, StyleLabTab, AuditTab, ImportTab, MonitorTab, StrategyTab）を元のpropsベースの実装に戻す
   - `frontend/src/hooks/useAppActions.ts` と `frontend/src/hooks/useBookDetails.ts` を元のシグニチャに戻す
   - `frontend/src/vite.config.ts` の manualChunks 設定を元に戻す
   - `frontend/src/package.json` と `package-lock.json` から react-router-dom の依存を削除し、以前のバージョンに戻す

5. **依存関係のインストール**
   ```bash
   cd frontend
   npm install
   ```

6. **ビルドとテスト**
   ```bash
   npm run build
   npm test
   ```

7. **変更のプッシュ**
   ```bash
   git push origin <branch-name>
   ```

## 検証
- アプリケーションが正常に起動し、タブ切替が以前の通り動作することを確認してください。
- コンソールにエラーがないことを確認してください。
- ネットワークタブで不要なチャンクが読み込まれていないことを確認してください。

## 注意事項
- 本番環境に適用する前に、ステージング環境で十分にテストしてください。
- データベーススキーマやバックエンドAPIに変更がないことを確認してください（このロールバックはフロントエンドのみに影響します）。