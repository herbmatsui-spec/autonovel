# 48ステップ実装計画のステップ5をさらに小さなステップに分解

## ステップ5: 修正 - `_legacy_dep` プロパティ群の段階的廃止準備
### 元の目的: 各 `@property` を新属性アクセスに変更する準備（ただし**まだ `_legacy` 経由でも動作する**よう、新属性が未設定なら `_legacy_dep` にフォールバック）

### さらに細分化されたサブステップ（各ステップ3-5分で完了）

#### ステップ5-1: 対象ファイルを開く
- **アクション**: `/home/herbmatsui/autonovel/src/backend/engine.py` を開く
- **確認**: ファイルが正常に開けること

#### ステップ5-2: ステップ4の変更結果を確認する
- **アクション**: ステップ4で追加したコンストラクタコードを確認する
- **確認**: 各依存が `self.XXX = XXX or self._legacy_dep('XXX')` という形式で設定されていること

#### ステップ5-3: `_legacy_dep` プロパティのリストを取得する
- **アクション**: ステップ1の調査結果（legacy_deps_inventory.md）またはエンジンファイル内を検索して、`_legacy_dep` を使っているすべてのプロパティをリストアップする
- **確認**: プランナー、ライター、PMなどのプロパティ名のリストを取得する
- **ツール**: `grep -n "@property" /home/herbmatsui/autonovel/src/backend/engine.py` と組み合わせて確認

#### ステップ5-4: planner プロパティの現在の実装を確認する
- **アクション**: planner プロパティの現在のコードを読む
- **確認**: `return self._legacy_dep('planner')` という実装であることを確認する

#### ステップ5-5: planner プロパティを新属性にフォールバック付きに変更する準備をする
- **アクション**: 新しい実装 `return self.planner or self._legacy_dep('planner')` を準備する
- **確認**: 新属性が設定されている場合はそれを返し、未設定の場合は `_legacy_dep` にフォールバックするロジックを確認する

#### ステップ5-6: planner プロパティを変更する
- **アクション**: planner プロパティの本体を、ステップ5-5 で準備したコードに置換する
- **ツール**: `edit` ツールを使って正確に置換する
- **確認**: 置換が正しく行われたこと

#### ステップ5-7: writer プロパティの現在の実装を確認する
- **アクション**: writer プロパティの現在のコードを読む
- **確認**: `return self._legacy_dep('writer')` という実装であることを確認する

#### ステップ5-8: writer プロパティを新属性にフォールバック付きに変更する準備をする
- **アクション**: 新しい実装 `return self.writer or self._legacy_dep('writer')` を準備する
- **確認**: フォールバックロジックが正しいことを確認する

#### ステップ5-9: writer プロパティを変更する
- **アクション**: writer プロパティの本体を、ステップ5-8 で準備したコードに置換する
- **確認**: 置換が正しく行われたこと

#### ステップ5-10: pm プロパティの現在の実装を確認する
- **アクション**: pm プロパティの現在のコードを読む
- **確認**: `return self._legacy_dep('pm')` という実装であることを確認する

#### ステップ5-11: pm プロパティを新属性にフォールバック付きに変更する準備をする
- **アクション**: 新しい実装 `return self.pm or self._legacy_dep('pm')` を準備する
- **確認**: フォールバックロジックが正しいことを確認する

#### ステップ5-12: pm プロパティを変更する
- **アクション**: pm プロパティの本体を、ステップ5-11 で準備したコードに置換する
- **確認**: 置換が正しく行われたこと

#### ステップ5-13: ctx_mgr プロパティの現在の実装を確認する
- **アクション**: ctx_mgr プロパティの現在のコードを読む
- **確認**: `return self._legacy_dep('ctx_mgr')` という実装であることを確認する

#### ステップ5-14: ctx_mgr プロパティを新属性にフォールバック付きに変更する準備をする
- **アクション**: 新しい実装 `return self.ctx_mgr or self._legacy_dep('ctx_mgr')` を準備する
- **確認**: フォールバックロジックが正しいことを確認する

#### ステップ5-15: ctx_mgr プロパティを変更する
- **アクション**: ctx_mgr プロパティの本体を、ステップ5-14 で準備したコードに置換する
- **確認**: 置換が正しく行われたこと

#### ステップ5-16: formatter プロパティの現在の実装を確認する
- **アクション**: formatter プロパティの現在のコードを読む
- **確認**: `return self._legacy_dep('formatter')` という実装であることを確認する

#### ステップ5-17: formatter プロパティを新属性にフォールバック付きに変更する準備をする
- **アクション**: 新しい実装 `return self.formatter or self._legacy_dep('formatter')` を準備する
- **確認**: フォールバックロジックが正しいことを確認する

#### ステップ5-18: formatter プロパティを変更する
- **アクション**: formatter プロパティの本体を、ステップ5-17 で準備したコードに置換する
- **確認**: 置換が正しく行われたこと

#### ステップ5-19: validator プロパティの現在の実装を確認する
- **アクション**: validator プロパティの現在のコードを読む
- **確認**: `return self._legacy_dep('validator')` という実装であることを確認する

#### ステップ5-20: validator プロパティを新属性にフォールバック付きに変更する準備をする
- **アクション**: 新しい実装 `return self.validator or self._legacy_dep('validator')` を準備する
- **確認**: フォールバックロジックが正しいことを確認する

#### ステップ5-21: validator プロパティを変更する
- **アクション**: validator プロパティの本体を、ステップ5-20 で準備したコードに置換する
- **確認**: 置換が正しく行われたこと

#### ステップ5-22: auditor プロパティの現在の実装を確認する
- **アクション**: auditor プロパティの現在のコードを読む
- **確認**: `return self._legacy_dep('auditor')` という実装であることを確認する

#### ステップ5-23: auditor プロパティを新属性にフォールバック付きに変更する準備をする
- **アクション**: 新しい実装 `return self.auditor or self._legacy_dep('auditor')` を準備する
- **確認**: フォールバックロジックが正しいことを確認する

#### ステップ5-24: auditor プロパティを変更する
- **アクション**: auditor プロパティの本体を、ステップ5-23 で準備したコードに置換する
- **確認**: 置換が正しく行われたこと

#### ステップ5-25: narrative プロパティの現在の実装を確認する
- **アクション**: narrative プロパティの現在のコードを読む
- **確認**: `return self._legacy_dep('narrative')` という実装であることを確認する

#### ステップ5-26: narrative プロパティを新属性にフォールバック付きに変更する準備をする
- **アクション**: 新しい実装 `return self.narrative or self._legacy_dep('narrative')` を準備する
- **確認**: フォールバックロジックが正しいことを確認する

#### ステップ5-27: narrative プロパティを変更する
- **アクション**: narrative プロパティの本体を、ステップ5-26 で準備したコードに置換する
- **確認**: 置換が正しく行われたこと

#### ステップ5-28: critique プロパティの現在の実装を確認する
- **アクション**: critique プロパティの現在のコードを読む
- **確認**: `return self._legacy_dep('critique')` という実装であることを確認する

#### ステップ5-29: critique プロパティを新属性にフォールバック付きに変更する準備をする
- **アクション**: 新しい実装 `return self.critique or self._legacy_dep('critique')` を準備する
- **確認**: フォールバックロジックが正しいことを確認する

#### ステップ5-30: critique プロパティを変更する
- **アクション**: critique プロパティの本体を、ステップ5-29 で準備したコードに置換する
- **確認**: 置換が正しく行われたこと

#### ステップ5-31: marketing プロパティの現在の実装を確認する
- **アクション**: marketing プロパティの現在のコードを読む
- **確認**: `return self._legacy_dep('marketing')` という実装であることを確認する

#### ステップ5-32: marketing プロパティを新属性にフォールバック付きに変更する準備をする
- **アクション**: 新しい実装 `return self.marketing or self._legacy_dep('marketing')` を準備する
- **確認**: フォールバックロジックが正しいことを確認する

#### ステップ5-33: marketing プロパティを変更する
- **アクション**: marketing プロパティの本体を、ステップ5-32 で準備したコードに置換する
- **確認**: 置換が正しく行われたこと

#### ステップ5-34: bible_agent プロパティの現在の実装を確認する
- **アクション**: bible_agent プロパティの現在のコードを読む
- **確認**: `return self._legacy_dep('bible_agent')` という実装であることを確認する

#### ステップ5-35: bible_agent プロパティを新属性にフォールバック付きに変更する準備をする
- **アクション**: 新しい実装 `return self.bible_agent or self._legacy_dep('bible_agent')` を準備する
- **確認**: フォールバックロジックが正しいことを確認する

#### ステップ5-36: bible_agent プロパティを変更する
- **アクション**: bible_agent プロパティの本体を、ステップ5-35 で準備したコードに置換する
- **確認**: 置換が正しく行われたこと

#### ステップ5-37: plot_agent プロパティの現在の実装を確認する
- **アクション**: plot_agent プロパティの現在のコードを読む
- **確認**: `return self._legacy_dep('plot_agent')` という実装であることを確認する

#### ステップ5-38: plot_agent プロパティを新属性にフォールバック付きに変更する準備をする
- **アクション**: 新しい実装 `return self.plot_agent or self._legacy_dep('plot_agent')` を準備する
- **確認**: フォールバックロジックが正しいことを確認する

#### ステップ5-39: plot_agent プロパティを変更する
- **アクション**: plot_agent プロパティの本体を、ステップ5-38 で準備したコードに置換する
- **確認**: 置換が正しく行われたこと

#### ステップ5-40: style_rag プロパティの現在の実装を確認する
- **アクション**: style_rag プロパティの現在のコードを読む
- **確認**: `return self._legacy_dep('style_rag')` という実装であることを確認する

#### ステップ5-41: style_rag プロパティを新属性にフォールバック付きに変更する準備をする
- **アクション**: 新しい実装 `return self.style_rag or self._legacy_dep('style_rag')` を準備する
- **確認**: フォールバックロジックが正しいことを確認する

#### ステップ5-42: style_rag プロパティを変更する
- **アクション**: style_rag プロパティの本体を、ステップ5-41 で準備したコードに置換する
- **確認**: 置換が正しく行われたこと

#### ステップ5-43: ai_api プロパティ（FutureWarning 付き）の現在の実装を確認する
- **アクション**: ai_api プロパティの現在のコードを読む
- **確認**: `FutureWarning` が発火する実装であることを確認する
- **注意**: このステップでは変更せず、FutureWarning を維持する（ステップ5では段階的廃止準備のため）

#### ステップ5-44: llm_client プロパティ（FutureWarning 付き）の現在の実装を確認する
- **アクション**: llm_client プロパティの現在のコードを読む
- **確認**: `FutureWarning` が発火する実装であることを確認する
- **注意**: このステップでは変更せず、FutureWarning を維持する

#### ステップ5-45: 変更後のファイルを読んで確認する
- **アクション**: 変更後の `/home/herbmatsui/autonovel/src/backend/engine.py` を読む
- **確認**: すべての対象プロパティが新しいフォールバック付き実装になっていること
- **判定**: プランナーから style_rag までのプロパティが正しく変更されているか確認する

#### ステップ5-46: 構文チェックを実行する
- **アクション**: `python -m py_compile /home/herbmatsui/autonovel/src/backend/engine.py` を実行する
- **確認**: エラーが出ないこと
- **判定**: 構文エラーがないか確認する

#### ステップ5-47: mypy 型チェックを実行する
- **アクション**: `mypy --config-file /home/herbmatsui/autonovel/pyproject.toml /home/herbmatsui/autonovel/src/backend/engine.py` を実行する
- **確認**: エラーが出ないこと
- **判定**: 型エラーがないか確認する（既存の型エラーは許容し、新たに導入しないことが目標）

#### ステップ5-48: 基本的な動作テストを実行する準備をする
- **アクション**: 新しいプロパティアクセスが正しく動作するかテストする準備をする
- **確認**: テスト用スクリプトを作成できること

#### ステップ5-49: プロパティアクセステストスクリプトを作成する
- **アクション**: 新しいフォールバック機能をテストするスクリプトを作成する
- **確認**: ファイルが正常に作成できること
- **作業内容**の例:
  ```python
  from src.backend.engine import UltimateHegemonyEngine
  
  # 新属性がNoneのときは_legacy_depにフォールバックすることを確認
  engine = UltimateHegemonyEngine()
  # plannerプロパティが_legacy_dep('planner')と同じものを返すか確認
  planner_via_property = engine.planner
  planner_via_legacy = engine._legacy_dep('planner')
  assert planner_via_property is planner_via_legacy, "Fallback not working for planner"
  
  # 新属性を設定したらそれを返すことを確認
  class MockPlanner:
      pass
  mock_planner = MockPlanner()
  engine.planner = mock_planner
  assert engine.planner is mock_planner, "New value not being used"
  
  print("Property fallback test passed")
  ```

#### ステップ5-50: プロパティアクセステストを実行する
- **アクション**: ステップ5-49 で作成したテストスクリプトを実行する
- **確認**: エラーなく実行でき、「Property fallback test passed」と出力されること
- **判定**: フォールバック機能が正しく動作することを確認する

#### ステップ5-51: 変更を元に戻す準備（万が一のため）
- **アクション**: 変更後に問題が生じた場合のために、元の状態に戻す方法を確認しておく
- **確認**: git やバックアップファイルを使って復元できる方法を知っていること

#### ステップ5-52: 作業の完了を宣言する
- **アクション**: ステップ5のすべてのマイクロステップが完了したことを記録する
- **確認**: 次のステップに進む準備ができていること

## 完了基準
- [ ] planner から style_rag までの 12 個のプロパティが、新属性フォールバック付き実装に変更されている
- [ ] 各プロパティが `return self.XXX or self._legacy_dep('XXX')` という形式になっている
- [ ] ai_api と llm_client プロパティは変更せず、FutureWarning を維持している
- [ ] Python 構文チェックでエラーが出ない
- [ ] mypy 型チェックで新たなエラーが導入されていない
- [ ] プロパティアクセステストが成功する（フォールバックと新値設定の両方が正常に動作）