# 最終チェックリスト

以下の項目を確認して、リリース前に最終チェックを行います。

1. **ビルド確認**
   - `npm run build` がエラー無しで完了する。
   - `docker build` が成功し、expectedイメージタグが作成される。

2. **テスト実行**
   - `npm test`（React）と `pytest`（バックエンド）がすべて成功。

3. **CORS 設定**
   - `CORS_ORIGINS` が正しく設定され、ブラウザから API へのアクセスで 200 が返る。
   - `curl -H "Origin: http://localhost:3000" -I http://localhost:8000/api/ping` の結果に `Access-Control-Allow-Origin` が存在。

4. **データフロー**
   - 生成タスクが開始→進捗→完了まで、UI にステータスが表示される。
   - タスク停止ボタンで `stopTask` が正しく呼ばれ、サーバーが `204` を返す。

5. **セキュリティ**
   - API キーは環境変数に格納されており、コード内にハードコーディングされていない。

6. **ドキュメント**
   - `docs/CORS_CONFIG.md`, `docs/DEPLOY.md`, `docs/FINAL_CHECKLIST.md` が最新で整合性が取れている。

7. **ログ**
   - `app.log` にはエラーログのみが残っていることを確認。

✔️ すべて合格ならリリース可。

---

### 注意点
- デプロイクラスターでインスタンスを再起動した際に環境変数が引き継がれるか確認。
- CI/CD パイプラインで `docker push` しているイメージ名と `docker run` で指定しているタグが一致しているか確認。
