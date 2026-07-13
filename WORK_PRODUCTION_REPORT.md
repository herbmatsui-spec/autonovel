# cR15 覇権小説自動生成エンジン - 制作レポート & 改善提案

**作成日**: 2026-07-11
**プロジェクト名**: cR15（覇権小説自動生成エンジン）
**対象バージョン**: v3.0+

---

## 1. 作品制作の概要

### 生成済みサンプル
- **ファイル**: `generated_sample_novel.md`
- **モデル**: gemini-2.5-flash
- **感情起点**: catharsis（長い苦悩の末に訪れる解放と浄化）
- **選択曲線**: zamaa_heavy
- **面白さ検証スコア**: 92/100
- **テーマ**: 復讐劇（国王ゼノンvs主人公セシル）

### システム構成

| コンポーネント | ファイル | 責務 |
|---------------|---------|------|
| 官能密度管理 | `src/services/erotic_density_controller.py` | 話数進行による強度調整 |
| 多様性スコアリング | `src/services/erotic_diversity_score.py` | 官能表現の重复検出 |
| 整合性チェッカー | `src/agents/erotic_integrity.py` | 同意表現・品質評価 |
| 伏字フィルタ | `formatters/erotic_censor.py` | プラットフォーム別 censura |
| リファインメント | `src/backend/workflows/refine_erotic_workflow.py` | 官能ワークフロー |

---

## 2. 中立的な評価

### 強み
1. **多層的な官能制御**: intensity 0-5 の細分化とフェーズ管理（Build/Peak/Afterglow）
2. **プラットフォーム対応**: なろう/カクヨム/ノクターン等複数の伏字パターンをサポート
3. **同意表現の明示的チェック**: `CONSENT_*_KEYWORDS` による双方向同意検証
4. **五感描写の多面的評価**: 触覚/嗅覚/聴覚/視覚/味覚のカバレッジスコア

### 弱み・課題
1. **テストカバレッジの不均衡**: 一部テストがImportErrorで失敗（`test_enigma_engine.py`, `test_background_worker.py`等）
2. **リファクタリング中の技術的負債**: `src/shared/utils/` の未削除によるIDEロック問題
3. **Pydantic v1からv2への移行不完全**: `@validator` から `@field_validator` への移行が進行中
4. **LLM依存リスク**: Gemini API可用性に完全依存

---

## 3. 改善案（9件）

### 改善1: テストカバレッジの強化と安定化
**対象**: `tests/test_erotic_workflow.py`, `tests/integration/test_erotic_full_pipeline.py`
**理由**: ImportErrorによるテスト失敗が継続しており、本番環境での信頼性を損なう
**手法**: 
- `conftest.py` に不足いている fixture を追加
- モックオブジェクトの配置を標準化

### 改善2: Pydantic v2 完全移行
**対象**: `config/archetypes.py`, `scripts/generate_plot.py`
**理由**: V1 から V2 への移行が部分的であり、警告ログが而出力されている
**手法**: `@validator` → `@field_validator` 置換を完了させ、CI で V2 警告を error 扱いにする

### 改善3: erotic_vocabulary の拡張（intense tier）- [完了]
**対象**: `config/erotic_vocabulary.py`, `config/erotic_vocabulary_ext.py`
**理由**: 強度5（過激）専用のボキャブラリが不足
**手法**:
- `intense` ティアを新規定義し、Base Bankを継承した超集合（Superset）として実装。
- 身体境界の消失、精神的溶解、生理的反応に特化した語彙を大幅に拡張（合計145アイテム）。
- 遅延インポートによる循環参照の回避と、`adult_selfhost` プリセットへの統合。
- `erotic_intensity_standards.md` への強度Lv.5定義の追記。

### 改善4: 官能シーンの一貫性検証強化
**対象**: `src/agents/erotic_integrity.py`
**理由**: 連続话間のキャラクター状態（体力・心理状態）の整合性チェックが未実装
**手法**: 前話の状態を引き継ぐ「 continuity tracker 」を追加

### 改善5: リファクタリング進捗の定期監視
**対象**: `REFACTORING_STATUS.md`, `REFACTORING_REMAINING_TASKS.md`
**理由**: IDEロックにより作業が停滞している
**手法**: ロック解除手順を文書化し、スクリプト化して自動化

### 改善6: 読者疲労度リアルタイム監視
**対象**: `streamlit_app/ui_tabs_monitor.py`
**理由**: 連続Peak話数の警告が後追いになっている
**手法**: ダッシュボードにリアルタイム監視チャートを追加し、閾値到達の前に警告

### 改善7: 多様性スコアの閾値自動校正
**対象**: `src/services/ncs_calibration.py`, `src/services/erotic_diversity_score.py`
**理由**: 閾値（0.5/0.35/0.2）が静的であり、人間評価との照合が困難
**手法**: フィードバックループを組み込み、A/Bテストで閾値を最適化

### 改善8: プラットフォーム規約変更検知の自動化
**対象**: `config/erotic_platform_presets.py`, `formatters/erotic_censor.py`
**理由**: 各プラットフォームの規約変更に対する手動更新が，非効率的
**手法**: Webhook 或いは定期実行で規約変更を自動検知するモジュールを追加

### 改善9: 代替LLM対応の追加
**対象**: `src/core/llm_gateway.py`
**理由**: Gemini单一依存により可用性リスクが存在
**手法**: OpenAI / Claude API へのフォールバック機能を実装し、circuit breaker パターンを適用

---

## 4. 優先度付け

| 優先度 | 改善案 | 工数概算 | リスク |
|-------|-------|---------|-------|
| 高 | 改善1（テスト安定化） | 小 | 低 |
| 高 | 改善2（Pydantic移行） | 中 | 中 |
| 低 | 改善3（ボキャブラリ拡張） | 小 | 低 |
| 中 | 改善7（閾値校正） | 中 | 中 |
| 中 | 改善6（リアルタイム監視） | 中 | 低 |
| 低 | 改善4（整合性検証） | 大 | 高 |
| 低 | 改善5（リファクタリング） | 小 | 低 |
| 低 | 改善8（規約変更検知） | 中 | 中 |
| 低 | 改善9（代替LLM） | 大 | 高 |

---

## 5. 結論

cR15 は Web 小説のランキング上位構造を工学的に再現する野心的なプロジェクトです。官能制御の多层的な設計とプラットフォーム対応は商用実用域に達しています。しかし、テストの不安定化・技術的負債の蓄積・单一LLM依存が継続的な課題として残っています。改善案9件の内、特にテスト安定化とPydantic移行を優先実施することで、プロジェクトの信頼性与えられます。