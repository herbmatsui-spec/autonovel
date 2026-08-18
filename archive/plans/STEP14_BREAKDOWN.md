# ステップ14: 設計 - `pipeline.py` の分割アーキテクチャ確定

## 目的
新ディレクトリ構造と各モジュールの責務を明確化

## 作業内容
- 新構造を設計:
  ```
  src/easy_mode/
    pipeline.py           # オーケストレーション専用（200行以下目標）
    bible_generator.py    # _generate_bible, _parse_bible, _fallback_bible
    plot_generator.py     # _generate_plot_outline, _interpolate_tension, _select_plot_pattern
    episode_writer.py     # _write_episode, _build_writing_prompt
    episode_auditor.py    # _audit_episode
    episode_rewriter.py   # _rewrite_episode, _inject_spice_markers
    series_finalizer.py   # _finalize_series, _finalize_result
    progress_reporter.py  # _report_progress
    presets/
      loader.py           # 既存
  ```
- 各モジュールの公開 API（関数シグネチャ）を定義

## 完了基準
設計書（ASCII クラス図付き）を `proposals/pipeline_split_design.md` に記述

## マイクロステップ

#### ステップ14-1: リファレンスファイルを確認する
- **アクション**: `/home/herbmatsui/autonovel/proposals/pipeline_split_design.md` を開き、ステップ13の結果を確認
- **確認**: ファイルが存在し、グルーピング情報が得られること
- **ツール**: `read` コマンド
- **出確認**: ファイル内容を表示
- **完了": ✅

#### ステップ14-2: 新ディレクトリ構造を決定する
- **アクション**: ステップ13のグルーピングを基に、各グループに対応するモジュール名を決定する
- **確認**: 各モジュールの責務とファイル名を文書化する
- **ツール**: 手動でマークダウンに記述
- **出力**: モジュールリストと責務を一時ファイルに保存
- **完了**: ✅

#### ステップ14-3: 各モジュールの公開APIを設計する
- **アクション**: 各モジュールが外部に提供する関数またはクラスのシグネチャを考える
- **確認**: APIが他のモジュールから呼び出し可能かつテスト可能であることを確認
- **ツール**: 手動でマークダウンに記述
- **出力**: APIシグネチャ一覧を一時ファイルに保存
- **完了**: ✅

#### ステップ14-4: 設計書をマークダウンで作成する
- **アクション**: `proposals/pipeline_split_design.md` に新しいセクションを追加し、ASCII クラス図およびモジュール責務を記述
- **確認**: 図が明かつ正確であること
- **ツール**: エディタまたはマークダウン記法
- **出力**: 設計書ファイルを更新
- **完了": ✅

#### ステップ14-5: 設計の整合性を確認する
- **アクション**: ステップ13の依存関係と新設計が矛盾していないか確認
- **確認**: 外部依存と内部依存が適切にカプセル化されているか
- **ツール**: 手動でレビュー
- **出力**: 整合性確認メモを作成
- **完了": ✅

#### ステップ14-6: 一時ファイルをクリーンアップ
- **アクション**: 一時ファイルを削除
- **確認**: 一時ファイルが残っていないこと
- **ツール**: `rm -f` など
- **出力**: クリーンアップ完了
- **完了": ✅
