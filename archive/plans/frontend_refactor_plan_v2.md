# フロントエンド改善 実装計画書 v2.0
## 現在の達成度: ~95% → 目標: 100%

---

## 1. 残存課題の特定

### 1.1 S61-S70: UIStateStore マルチ継承の安定化（構成アプローチ）
**現状**: `state.py:188` で多重継承を継続使用
```python
class UIStateStore(JobStore, PollStateStore, ToastStore, SessionStore):
```
**課題**: MRO（Method Resolution Order）の複雑性、責務の混在
**目標**: 合成パターンへの移行

### 1.2 CSS最適化の完了
**現状**: 
- `landing.py`, `sidebar.py`, `ui_utils.py`, `ui_components.py` にコメントアウトされた<style>タグが残存
- CSSの重複定義（`render_centered_title`等がインラインCSSを使用）

**目標**: インラインCSSを完全に排除

### 1.3 time.sleepの完全排除
**現状**: `backend_launcher.py:83` に機能的スリープが残存
```python
while time.time() < deadline:
    try:
        resp = req.get(_BACKEND_URL, timeout=2)
        if resp.status_code == 200:
            return proc
    except Exception:
        time.sleep(poll_interval)  # ← ここ
```
**目標**: 非ブロッキングポーリング方式に置換

---

## 2. 実装手順

### Phase 1: UIStateStore合成パターン実装 (S61-S70)
1. `stores/base.py` に合成ロジックを追加
2. `state.py` のUIStateStoreをファサードから合成ベースに変更
3. 既存の呼び出し箇所を維持したまま内部実装を置換

### Phase 2: CSS完全統合 (最優先度: 高)
1. `landing.py` から残存<style>タグを完全削除
2. `sidebar.py` からコメントアウト部分を削除
3. `ui_utils.py` の`render_centered_title`をCSSクラス化
4. `ui_components.py` の`inject_focus_css`を統合

### Phase 3: time.sleep完全排除 (最優先度: 中)
1. `backend_launcher.py` のポーリングループを非ブロッキング化
2. `progress.py` のスリープ処理を見直し

### Phase 4: テスト拡充 (最優先度: 中)
1. UIStateStore合成後のテスト追加
2. 統合テストの実行

---

## 3. タイムライン

| Phase | タスク | 所要時間 | 依存関係 |
|-------|--------|----------|----------|
| 1 | UIStateStore合成 | 30分 | なし |
| 2 | CSS統合完了 | 20分 | Phase 1完了 |
| 3 | time.sleep排除 | 15分 | Phase 2完了 |
| 4 | テスト実行 | 10分 | Phase 3完了 |

**合計: 75分 (~1.5時間)**

---

## 4. リスクと対策

### リスク1: UIStateStoreの変更による既存機能への影響
**対策**: 
- 段階的に移行（ファサード維持）
- 包括的テストで検証

### リスク2: CSS変更によるUI崩れ
**対策**:
- ブラウザキャッシュを考慮
- レスポンシブ確認

### リスク3: ポーリング方式変更によるUX劣化
**対策**:
- `st.rerun()` を適切に使用
- プログレスバーで進捗表示

---

## 5. 成功基準

- [ ] UIStateStoreが合成パターンを採用
- [ ] 全てのインライン<style>タグが削除
- [ ] time.sleepがUIコードパスから完全排除
- [ ] 既存テストが全てパス
- [ ] 手動UIテストで崩れなし
