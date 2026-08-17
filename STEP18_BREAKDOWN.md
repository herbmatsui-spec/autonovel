# ステップ18: 実装 - `episode_auditor.py` と `episode_rewriter.py` の抽出

## 目的
監査・リライトロジックを独立モジュール化

## 作業内容
- 新ファイル `src/easy_mode/episode_auditor.py` を作成
- `EasyModeEpisodeAuditor` クラスを定義（`audit(content, context) -> AuditResult`）
- 新ファイル `src/easy_mode/episode_rewriter.py` を作成
- `EasyModeEpisodeRewriter` クラスを定義（`rewrite(content, improvements, spice_elements) -> str`）
- スコア正規化ロジック（1000点満点 → 100点満点）を `AuditResult` クラスに集約

## 完了基準
監査とリライトが独立してテスト可能

## マイクロステップ

#### ステップ18-1: 対象ディレクトリを確認する
- **アクション**: `/home/herbmatsui/autonovel/src/easy_mode/` ディレクトリを確認し、`episode_auditor.py` と `episode_rewriter.py` が存在することを確認
- **確認**: ファイルが存在すること
- **ツール**: `ls` コマンド
- **出力**: ディレクトリリストを表示
- **完了**: ✅

#### ステップ18-2: `episode_auditor.py` の新ファイルを作成し、クラスの骨組みを書く
- **アクション**: `src/easy_mode/episode_auditor.py` を作成し、`EasyModeEpisodeAuditor` クラスの骨組みを書く
- **確認**: ファイルが作成され、クラス定義が存在すること
- **ツール**: `write` または `edit` コマンド
- **出力**: ファイル内容を表示
- **完了": ✅

#### ステップ18-3: `_audit_episode` メソッドを移植する
- **アクション**: `pipeline.py` から `_audit_episode` メソッドを抜き出し、`episode_auditor.py` のクラスメソッドとして貼り付ける
- **確認**: メソッドが正しく移植され、シグネチャが一致すること
- **ツール**: `read`、`edit` コマンド
- **出力**: 移植後のメソッド内容を表示
- **完了": ✅

#### ステップ18-4: `_rewrite_episode` メソッドを移植する
- **アクション**: `pipeline.py` から `_rewrite_episode` メソッドを抜き出し、`episode_rewriter.py` のクラスメソッドとして貼り付ける
- **確認**: メソッドが正しく移植され、シグネチャが一致すること
- **ツール**: `read`、`edit` コマンド
- **出力**: 移植後のメソッド内容を表示
- **完了": ✅

#### ステップ18-5: スコア正規化ロジックを `AuditResult` に集約する
- **アクション**: `AuditResult` クラスのスコア正規化ロジックを確認し、必要ならば集約する
- **確認**: スコア正規化が `AuditResult` クラス内で完結していること
- **ツール**: `read`、`edit` コマンド
- **出力**: `AuditResult` クラスの内容を表示
- **完了": ✅

#### ステップ18-6: `pipeline.py` からメソッドの呼び出しを削除し、新モジュールを使用するように変更する
- **アクション**: `pipeline.py` で `_audit_episode`、`_rewrite_episode` の呼び出しを削除し、代わりに `self.episode_auditor.audit()` などを呼び出すように変更
- **確認**: 呼び出しが正しく置き換えられ、エラーがないこと
- **ツール**: `edit` コマンド
- **出力**: 変更後の呼び出し部分を表示
- **完了": ✅

#### ステップ18-7: 単体テストファイルを作成する
- **アクション**: `tests/test_episode_auditor.py` と `tests/test_episode_rewriter.py` を作成し、基本的なテストを書く
- **確認**: テストファイルが作成され、それぞれ少なくとも 1 つのテスト関数が存在すること
- **ツール**: `write` コマンド
- **出力**: テストファイルの内容を表示
- **完了": ✅

#### ステップ18-8: 単体テストを実行し、パスすることを確認する
- **アクション**: `pytest tests/test_episode_auditor.py tests/test_episode_rewriter.py -v` を実行し、すべてのテストがパスすることを確認
- **確認**: テストがすべてパスすること
- **ツール**: `pytest` コマンド
- **出力**: テスト結果を表示
- **完了": ✅

#### ステップ18-9: `pipeline.py` の行数削減を確認する
- **アクション**: `pipeline.py` の行数を測定し、約 50 行削減されているか確認
- **確認**: 行数削減が達成されていること
- **ツール**: `wc -l` コマンド
- **出力**: 行数を表示
- **完了": ✅

#### ステップ18-10: 一時ファイルをクリーンアップする
- **アクション**: 作業中に作成した一時ファイルを削除する
- **確認**: 一時ファイルが残っていないこと
- **ツール**: `rm -f` など
- **出力**: クリーンアップ完了
- **完了": ✅
