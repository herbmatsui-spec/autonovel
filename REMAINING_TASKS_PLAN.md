# 残りタスクの詳細実装計画書: Book Score Service テスト完了

## 目的
src/services/book_score_service.py (916行) のユニットテストを完成させ、構文エラーを修正してテストをパスさせる。

## 現在の状況
- テストファイル `tests/unit/test_book_score_service.py` はほぼ完成している（30,556行）
- 行178での構文エラーによりテストが収集できない状態
- エラー: `SyntaxError: invalid syntax` at line 178, pointing to underscore in "Not close"
- 原因: `with` 文の行継続におけるバックスラッシュの配置が間違っている（コメント内にあるため機能しない）

## 残りタスク詳細

### ステップ 18: BookScoreCalculator 初期化と重み計算テスト
**目的**: コンストラクタ、設定ファイル読み込み、重み計算メソッドのテスト
**テスト項目**:
- コンストラクタと設定ファイル読み込みのテスト
- _get_weights メソッドテスト（デフォルト重み、ジャンルオーバーライド、フェーズオーバーライド）
- BookScore データクラスと BookScoreRepository プロトコルテスト

### ステップ 19: スコア計算メソッドテスト
**目的**: 各スコア計算メソッドと総合スコア計算のテスト
**テスト項目**:
- calculate メソッドテスト（全体スコアと各次元スコアの計算）
- _score_structure, _score_coherency, _score_factual メソッドテスト
- _score_visual_textual, _score_reader_experience メソッドテスト
- 各スコアメソッドのエラーハンドリングとデフォルト値テスト
- save_score, get_latest_score メソッドテスト

### ステップ 20: トレンド分析とPDCAレポートテスト
**目的**: トレンド分析機能とPDCAレポート生成のテスト
**テスト項目**:
- _fetch_plot, _fetch_chapter, _fetch_illustration, _fetch_bible, _fetch_audit_report ヘルパーメソッドテスト
- _build_text_stats メソッドテスト
- analyze_trend メソッドテスト（線形回帰、移動平均、変化点検出、予測）
- generate_pdca_report メソッドテスト（Plan-Do-Check-Actサイクル）
- _get_anachronisms ヘルパーメソッドテスト

## 実装アプローチ

### 構文エラー修正
**問題**: 行178のバックスラッシュがコメント内にあるため行継続として機能しない
```python
# 現在の問題のあるコード:
patch.object(calculator, "_fetch_plot", return_value=MagicMock(end_ep=5)),  # Not close \
```

**解決策1**: バックスラッシュをコメントの外側に移動
```python
patch.object(calculator, "_fetch_plot", return_value=MagicMock(end_ep=5)),  # Not close \
```

**解決策2**（推奨）: 明示的な括弧を使って行継続を避ける
```python
with (
    patch.object(calculator, '_fetch_audit_report', return_value=[
        MagicMock(category='logical_consistency', severity='high'),  # Fail
        MagicMock(category='causal_integrity', severity='low')      # Pass
    ]),
    patch.object(calculator, '_fetch_plot', return_value=MagicMock(end_ep=5)),  # Not close
    patch.object(calculator, '_fetch_chapter', return_value=MagicMock(tension=30))  # Low tension
):
```

### テスト実装方針
1. まず構文エラーを修正
2. テストを実行して失敗するケースを特定
3. 失敗しているテストに対して実装またはテスト自体の修正を行う
4. すべてのテストがパスするまで繰り返し
5. hypothesis を使用したプロパティベーステストの実装確認

## 期待される成果
- tests/unit/test_book_score_service.py のすべてのテストがパスする
- book_score_service.py の行カバレッジが約16% → 85%以上に向上
- 外部依存はすべてモックまたはスタブを使用して独立したテストを実現
- エラーケース、境界値、契約遵守を網羅したテストスイート

## テスト実行方法
```bash
# 個別テストファイルの実行
pytest tests/unit/test_book_score_service.py -v

# カバレッジ測定
pytest --cov=src/services/book_score_service tests/unit/test_book_score_service.py
```