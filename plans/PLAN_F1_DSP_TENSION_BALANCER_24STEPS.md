# PLAN_F1: DSPベース テンション曲線バランサー 実装計画（24ステップ）

## 概要
離散信号処理（DSP）で物語テンションを時系列信号として扱い、スペクトル平坦度・低周波優位度で「中だるみ」を検知、インパルス応答で補正する決定論的モジュール。

**入力**: `beat_sheet: List[Beat]`（各話のテンション値 1-10 等）  
**出力**: `corrected_beat_sheet: List[Beat]`（必要話数のみ差し替え）

---

## ステップ定義

### Phase 0: 環境・インターフェース定義 (1-3)

#### Step 1: データ構造定義
- **ファイル**: `src/narrative_balancer/dsp/models.py`
- **内容**: `TensionSignal`, `Beat`, `CorrectionAction` 等の Pydantic モデル定義
- **テスト**: `tests/unit/test_dsp_models.py` - シリアライズ/デシリアライズ検証

#### Step 2: インターフェース（Protocol）定義
- **ファイル**: `src/narrative_balancer/dsp/ports.py`
- **内容**: `TensionAnalyzer`, `Corrector` プロトコル（抽象基底クラス）
- **テスト**: `tests/unit/test_dsp_ports.py` - サブクラス実装強制チェック

#### Step 3: 設定スキーマ（YAML）定義
- **ファイル**: `config/dsp_balancer.yaml`
- **内容**: `window_size`, `flatness_threshold`, `low_freq_ratio_threshold`, `impulse_shape` 等
- **テスト**: `tests/unit/test_dsp_config.py` - Pydantic Settings でバリデーション

---

### Phase 1: コア信号処理ロジック (4-10)

#### Step 4: テンション抽出ユーティリティ
- **ファイル**: `src/narrative_balancer/dsp/signal.py`
- **関数**: `extract_tension_curve(beats: List[Beat]) -> np.ndarray`
- **テスト**: `tests/unit/test_signal_extraction.py` - 既知入力で期待配列比較

#### Step 5: スペクトル平坦度計算
- **ファイル**: `src/narrative_balancer/dsp/spectral.py`
- **関数**: `spectral_flatness(curve: np.ndarray) -> float`
- **アルゴリズム**: `geometric_mean(psd) / arithmetic_mean(psd)`
- **テスト**: `tests/unit/test_spectral_flatness.py` - 正弦波(低平坦)・ホワイトノイズ(高平坦)で検証

#### Step 6: 低周波エネルギー比計算
- **ファイル**: `src/narrative_balancer/dsp/spectral.py` (同ファイル追加)
- **関数**: `low_freq_energy_ratio(curve: np.ndarray, cutoff_ratio: float=0.3) -> float`
- **テスト**: `tests/unit/test_low_freq_ratio.py` - 低周波合成信号で >0.8, 高周波で <0.2

#### Step 7: 中だるみ検知関数
- **ファイル**: `src/narrative_balancer/dsp/detector.py`
- **関数**: `detect_sag(curve: np.ndarray, ep: int, cfg: DSPConfig) -> bool`
- **ロジック**: 直近 `window` 話で `flatness > thresh AND low_freq_ratio > thresh`
- **テスト**: `tests/unit/test_detector.py` - 境界値・正常・中だるみケースでパラメータ化テスト

#### Step 8: インパルス応答設計
- **ファイル**: `src/narrative_balancer/dsp/impulse.py`
- **関数**: `design_midpoint_disaster_impulse(length: int, peak: float=9.0, decay: float=0.7) -> np.ndarray`
- **形状**: 急立ち上げ・指数減衰（ステップ応答的）
- **テスト**: `tests/unit/test_impulse_design.py` - 面積・ピーク・減衰特性検証

#### Step 9: 畳み込み補正関数
- **ファイル**: `src/narrative_balancer/dsp/corrector.py`
- **関数**: `apply_impulse_correction(curve: np.ndarray, ep: int, impulse: np.ndarray) -> np.ndarray`
- **ロジック**: `curve[ep:ep+len(impulse)] += impulse` （クリッピング 1-10）
- **テスト**: `tests/unit/test_corrector.py` - 元曲線復元性・境界クリップ検証

#### Step 10: Beatシートへの書き戻し
- **ファイル**: `src/narrative_balancer/dsp/corrector.py` (同ファイル追加)
- **関数**: `writeback_corrected_beats(original: List[Beat], corrected_curve: np.ndarray, corrected_eps: Set[int]) -> List[Beat]`
- **テスト**: `tests/unit/test_writeback.py` - 非補正話は不変、補正話のみ更新確認

---

### Phase 2: パイプライン統合 (11-15)

#### Step 11: DSPバランサーメインクラス
- **ファイル**: `src/narrative_balancer/dsp/balancer.py`
- **クラス**: `DSPTensionBalancer`（`TensionAnalyzer`, `Corrector` 実装）
- **メソッド**: `analyze(beats) -> List[SagDetection]`, `correct(beats) -> List[Beat]`
- **テスト**: `tests/integration/test_dsp_balancer.py` - エンドツーエンド正常系

#### Step 12: 設定注入・ファクトリ
- **ファイル**: `src/narrative_balancer/dsp/factory.py`
- **関数**: `create_dsp_balancer(config_path: str) -> DSPTensionBalancer`
- **テスト**: `tests/unit/test_factory.py` - 設定ファイル読み込み・デフォルト値検証

#### Step 13: ロギング・メトリクス出力
- **ファイル**: `src/narrative_balancer/dsp/balancer.py` (拡張)
- **追加**: 検知スコア、補正量、実行時間を構造化ログ（JSONL）出力
- **テスト**: `tests/unit/test_logging.py` - ログフォーマット・必須フィールド検証

#### Step 14: CLI エントリーポイント
- **ファイル**: `src/narrative_balancer/dsp/cli.py`
- **コマンド**: `dsp-balance --input beats.json --output corrected.json --config config.yaml`
- **テスト**: `tests/integration/test_cli.py` - 実行コード・stdout/stderr・出力ファイル検証

#### Step 15: 統合テスト・ゴールデンマスタ
- **ファイル**: `tests/integration/test_dsp_golden.py`
- **データ**: `tests/fixtures/golden/normal_40ep.json`, `sag_20_30ep.json`
- **検証**: 既知入力に対する既知出力（ハッシュ比較）でリグレッション防止

---

### Phase 3: エッジケース・堅牢化 (16-20)

#### Step 16: 短系列・境界処理
- **対象**: 10話未満、ep=0, ep=39 付近
- **修正**: `detector.py`, `corrector.py` でガード節追加
- **テスト**: `tests/unit/test_edge_cases.py` - parametrize で 1,5,10,39,40 話ケース

#### Step 17: NaN/欠損値ハンドリング
- **対象**: テンション値欠損（None）、全話同一値
- **修正**: `signal.py` で補間・フォールバック
- **テスト**: `tests/unit/test_nan_handling.py` - 全パターン網羅

#### Step 18: 多変量テンション対応（拡張）
- **対象**: `tension`, `stakes`, `pacing` 等多チャネル
- **修正**: `spectral.py` で多変量スペクトル平坦度（行列対数行列式）実装
- **テスト**: `tests/unit/test_multivariate.py` - 2ch/3ch 合成信号

#### Step 19: パフォーマンスベンチマーク
- **ファイル**: `benchmarks/benchmark_dsp.py`
- **測定**: 40話×1000回実行で p50/p99/p999 レイテンシ
- **目標**: p99 < 5ms（NumPy ベクトル化確認）
- **テスト**: `tests/performance/test_dsp_perf.py` - CI で閾値超過なら失敗

#### Step 20: ドキュメント・型ヒント完全化
- **対象**: 全 `.py` ファイル
- **内容**: docstring (NumPy形式)、型ヒント 100%、README 追記
- **テスト**: `tests/meta/test_typing.py` - `mypy --strict` パス、`pydocstyle` パス

---

### Phase 4: 回帰テストスイート自動化 (21-24)

#### Step 21: プロパティベーステスト導入
- **ツール**: `hypothesis`
- **対象**: `spectral_flatness`（0-1範囲）、`low_freq_energy_ratio`（0-1範囲）、`detect_sag`（冪等性）
- **ファイル**: `tests/property/test_dsp_properties.py`

#### Step 22: 回帰テストデータセット拡充
- **データ**: `tests/fixtures/regression/` 以下に 50+ ケース追加
  - 正常曲線、緩やか中だるみ、急激中だるみ、多峰性、フラット、スパイク混在
- **スクリプト**: `scripts/generate_regression_cases.py` で自動生成可能に

#### Step 23: CI パイプライン統合
- **ファイル**: `.github/workflows/dsp_balancer.yml`
- **ステージ**: lint → typecheck → unit → integration → property → performance
- **ゲート**: 全ステージパス必須、カバレッジ ≥ 90%

#### Step 24: リリース用パッケージング
- **ファイル**: `pyproject.toml` 更新（`dsp-balancer` エントリーポイント追加）
- **確認**: `pip install -e . && dsp-balance --help` 正常動作
- **タグ**: `v0.1.0-dsp` でリリース

---

## 依存関係グラフ

```
1→2→3
  ↓
4→5→6→7→8→9→10
         ↓
        11←12
         ↓
        13→14→15
         ↓
        16→17→18→19→20
                    ↓
                  21→22→23→24
```

---

## 実装順序の指針
- **低性能LLMでも迷わないよう**: 各ステップは単一ファイル・単一関数・単一責任
- **テストファースト**: 実装前に対応テストファイルを雛形作成（`pytest --co -q` で確認）
- **並列化可能**: Phase 1 (4-10) は相互独立 → 並行実装可
- **リグレッション防止**: Step 15・21・22・23 で多層防御

---

## 完了基準
- [ ] 全 24 ステップのコード・テストが `main` ブランチにマージ済み
- [ ] `pytest tests/ -v --tb=short` 全パス
- [ ] `mypy --strict src/narrative_balancer/dsp` パス
- [ ] ベンチマーク p99 < 5ms 達成
- [ ] ゴールデンマスタテスト 100% 一致