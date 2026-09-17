# AutoNovel 健全化・商用化マスターロードマップ (SSOT)

本ドキュメントは、AutoNovel プロジェクトの品質健全化および商用化に向けた単一の情報源（Single Source of Truth）です。  
過去の細分化された計画書群（P0〜P10等）はすべて `plans/archive/v4_legacy/` に集約・退避されました。

---

## 🎯 ロードマップ概要

```
[Phase 0: 止血と身軽化] ───────► [Phase 1: コア救命] ───────► [Phase 2: エージェント軽量化] ───────► [Phase 3: 環境統一・公開]
・新機能凍結                    ・Stripe Webhook修正          ・8オーディター集約              ・PostgreSQL一本化
・デッドコード71モジュール物理削除・LangGraph Checkpointer修正  ・PDCAループ1回制限              ・MVPローンチ
・CIゲート/カバレッジ正常化     ・失敗テスト56件解消          ・Easy Mode磨き上げ
```

---

## 📋 フェーズ別詳細

### 【Phase 0: 止血と身軽化（Stabilization & Dead Code Purge）】（現在実行中）
- **ゴール**: 認知負荷の激減、デッドコードの完全排除、CI/テストベースラインの正常化
- **主要タスク**:
  1. 作業ツリーのセーブポイントコミット作成 & 専用ブランチ運用
  2. `plans/` ディレクトリのアーカイブ整理とマスターロードマップ一本化
  3. `pyproject.toml` omit 指定のデッドモジュール（71ファイル・3,680行）の物理削除
  4. レイヤー二重化の温床となっている下位互換スタブ・エイリアスファイルの整理
  5. `pyproject.toml` のカバレッジ閾値を実力値（55%）に一時調整し、テスト破損を正確に捕捉
  6. CI（GitHub Actions）の是正と全テスト実行によるベースライン確定

### 【Phase 1: コア救命（Core Stabilization & Bugfix）】
- **ゴール**: 主要ユースケースと決済のE2E完走、テストのALL GREEN達成
- **主要タスク**:
  1. **Stripe Webhook 500クラッシュ修正**: `billing_webhook.py` のコルーチン `await` 漏れ修正
  2. **LangGraph執筆ループ修正**: `writing_langgraph.py` の Checkpointer `configurable` 引数修正
  3. **認証ミドルウェア修正**: JWT / RBAC のテスト失敗解消
  4. **GraphRAG / AGE テスト修正**: ハイブリッド検索の不整合解消
  5. **テスト 56〜69件の失敗をゼロにする**

### 【Phase 2: エージェント軽量化（Agent Streamlining）】
- **ゴール**: 1話あたりの生成コストを数十円以内、レイテンシを1分以内に圧縮
- **主要タスク**:
  1. **8専門オーディターの統廃合**: 8回の並列LLM呼出を1回の「統合オーディター（Unified Auditor）」へ集約
  2. **PDCAループの制限**: 最大3回反復から「1発生成＋必要な場合のみ1回パッチ修正」へスリム化
  3. **Easy Mode（かんたん執筆）の完成**: 最も価値の高いMVPフロー（企画→本文→ZIP/EPUB）を研ぎ澄ます

### 【Phase 3: 環境統一と商用ローンチ（Production Readiness）】
- **ゴール**: 本番インフラ（PostgreSQL + Docker）での安定稼働
- **主要タスク**:
  1. SQLite と PostgreSQL / Apache AGE の二重管理を解消
  2. Docker Compose 本番構成の検証
  3. エラー監視（Sentry / OpenTelemetry）の整備
  4. 低コスト商用公開
