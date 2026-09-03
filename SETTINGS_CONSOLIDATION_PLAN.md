# 設定項目統合 実装計画書

## 目的
- Homeページサイドバーの設定UIを削除（重複排除）
- Settingsページ（`00_Settings.py`）に**よく変える項目のみ**を集約
- 環境変数専用・稀に変更する項目はUI非表示（環境変数案内のみ）

---

## 1. 対象項目の分類（configスキーマ全95項目から選定）

### ✅ **よく変える項目（UI化対象・計27項目）**

| カテゴリ | 項目名 | 現在の場所 | 移動先タブ |
|----------|--------|-----------|------------|
| **モデル** | model_writing | Settings/サイドバー両方 | 🤖 モデル設定 |
| | model_planning | Settings/サイドバー両方 | 🤖 モデル設定 |
| | model_plot_expansion | Settings/サイドバー両方 | 🤖 モデル設定 |
| | model_climax | Settings/サイドバー両方 | 🤖 モデル設定 |
| | model_ultra_stable | Settingsのみ | 🤖 モデル設定 |
| | model_stable_fallback | 未公開 | 🤖 モデル設定 |
| | model_embedding | 未公開 | 🤖 モデル設定 |
| **API** | openai_api_key | Settings/サイドバー両方 | 🤖 モデル設定 |
| | openai_base_url | Settings/サイドバー両方 | 🤖 モデル設定 |
| **機能開閉** | enable_draft_polish | Settings/サイドバー両方 | 🔧 機能開閉 |
| | enable_actor_critic | Settings/サイドバー両方 | 🔧 機能開閉 |
| | enable_heavy_audit | Settings/サイドバー両方 | 🔧 機能開閉 |
| | prefetch_enabled | Settingsのみ | 🔧 機能開閉 |
| | context_trimming_enabled | Settingsのみ | 🔧 機能開閉 |
| | enable_semantic_edge_preservation | Settingsのみ | 🔧 機能開閉 |
| | enable_dogfeeding | 未公開 | 🔧 機能開閉 |
| | fail_fast_mode | 未公開 | 🔧 機能開閉 |
| | specialized_amplifier_enabled | 未公開 | 🔧 機能開閉 |
| **安全/NSFW** | enable_nsfw | Settings/サイドバー両方 | 🔒 安全設定 |
| | safety_filter_level | Settings/サイドバー両方 | 🔒 安全設定 |
| | similarity_threshold | Settingsのみ | 🔒 安全設定 |
| **コスト/保存** | cost_mode | Settings/サイドバー両方 | 💰 コスト管理 |
| | auto_backup | Settings/サイドバー両方 | 💰 コスト管理 |
| | max_history_len | Settings/サイドバー両方 | 💰 コスト管理 |
| **コンテキスト** | context_window_target_ratio | 未公開 | 🔧 機能開閉（詳細） |
| | prefetch_episode_count | 未公開 | 🔧 機能開閉（詳細） |
| **品質閾値** | min_immersion_score | 未公開 | 🔒 安全設定（品質閾値） |

---

### ❌ **UI非表示項目（環境変数専用・稀に変更）**

| カテゴリ | 項目名 | 理由 |
|----------|--------|------|
| DB/Redis | database_url, redis_url, redis_max_connections, redis_default_ttl, redis_namespace | インフラ設定。環境変数 `DATABASE_URL`, `REDIS_URL` で制御 |
| プロンプトキャッシュ | prompt_cache_max_size | 内部最適化パラメータ |
| 検索 | hybrid_search_alpha | 実験的機能 |
| ストレス/カタルシス | stress_catharsis_threshold, stress_filler_threshold, stress_climax_bonus, stress_hate_gain_base, catharsis_threshold, catharsis_reset_value | ドメインプロファイルで上書きされるため直接変更非推奨 |
| 並行処理 | max_concurrency, max_concurrent_api_calls | 自動計算推奨 (`get_auto_concurrency()`) |
| クールダウン | cooldown_base, cooldown_min, cooldown_max | 詳細チューニング用 |
| 品質詳細 | polishing_min_content_ratio, actor_critic_max_iterations, actor_critic_severity_threshold | 既定値で十分 |
| セーフモード | safe_append_mode | 内部制御 |
| 自己最適化 | optimized_prompt_patch | AI生成パッチ（手動編集非推奨） |
| 波形/密度 | wave_pattern_ratio, catharsis_density_range | 構造化設定（JSON） |

---

## 2. Settingsページ タブ構成案（修正後）

```python
tab_models, tab_features, tab_safety, tab_costs, tab_advanced = st.tabs([
    "🤖 モデル設定",      # 9項目
    "🔧 機能開閉",        # 9項目
    "🔒 安全・品質設定",   # 4項目
    "💰 コスト・保存",     # 3項目
    "🔬 詳細設定",        # 2項目（context_window_target_ratio, prefetch_episode_count）
])
```

### タブ別詳細

#### 🤖 モデル設定（9項目）
- 執筆/企画/詳細展開/クライマックス/フォールバック/安定フォールバック/埋め込み の7モデル選択
- API Key / Base URL

#### 🔧 機能開閉（9項目）
- 執筆機能: ドラフトポリシング, アクタークォリティ, スタイルRAG
- 品質管理: 詳細オーディット, エッジ保全, ドッグフィーディング, フェイルファスト, 専用アンプ
- パフォーマンス: プリフェッチ, コンテキストトリミング

#### 🔒 安全・品質設定（4項目）
- NSFW許可, セーフティレベル, 類似度閾値, 最低没入スコア

#### 💰 コスト・保存（3項目）
- コストモード, 自動バックアップ, 履歴最大保持数

#### 🔬 詳細設定（2項目）
- コンテキスト目標使用率, プリフェッチエピソード数
- ※折りたたみデフォルト閉

---

## 3. 実装手順

### Step 1: Homeページサイドバー設定UI削除 (`01_Home.py`)
- 削除範囲: L96-L178（サイドバー設定セクション全体）
- 保持: 保存ボタンも削除（Settingsページに集約）
- 代替: サイドバーに「⚙️ 設定ページへ」リンクボタンのみ配置

### Step 2: Settingsページ拡張 (`00_Settings.py`)
1. タブ追加: `tab_advanced` を追加
2. 未公開項目のUI追加:
   - `model_stable_fallback`, `model_embedding` → モデル設定タブ
   - `enable_dogfeeding`, `fail_fast_mode`, `specialized_amplifier_enabled` → 機能開閉タブ
   - `context_window_target_ratio`, `prefetch_episode_count` → 詳細設定タブ
   - `min_immersion_score` → 安全・品質設定タブ
3. `save_all_settings()` に新項目追加
4. `load_config()` で全項目読み込み確認

### Step 3: 共通ヘルパー関数化（将来の保守性）
- `render_model_selector(key, label, help)` - モデル選択UI共通化
- `render_toggle(key, label, help)` - トグルUI共通化
- `render_slider(key, label, min, max, help)` - スライダーUI共通化

### Step 4: 動作確認
- Settingsページで全項目変更→保存→再読み込みで反映確認
- Homeページサイドバーに設定UIがなくなっていること確認
- 環境変数優先順位の維持確認 (`KAKU_*` / `DATABASE_URL` / `REDIS_URL`)

---

## 4. 影響範囲・リスク

| 領域 | 影響 | 対策 |
|------|------|------|
| Homeページ | サイドバー設定消失 | 設定ページへの導線ボタン配置 |
| 既存ユーザー | 設定場所変更 | 初回アクセス時トースト通知「設定は⚙️設定ページへ」 |
| 環境変数 | 変更なし | 既存優先順位維持（env > toml > default） |
| ConfigState | 参照キー変更なし | session_state キー名 `cfg_*` 維持 |

---

## 5. 実装優先度

1. **高** - Homeサイドバー削除 + Settingsへ導線
2. **高** - 不足項目（model_stable_fallback, model_embedding, enable_dogfeeding, fail_fast_mode, specialized_amplifier_enabled, min_immersion_score）追加
3. **中** - 詳細設定タブ作成（context_window_target_ratio, prefetch_episode_count）
4. **低** - 共通ヘルパー関数化（リファクタリング）

---

## 6. 完了基準

- [ ] Homeページサイドバーに設定UIなし（導線ボタンのみ）
- [ ] Settingsページで上記27項目すべて変更・保存可能
- [ ] 保存後、アプリ再起動で設定永続化確認
- [ ] 環境変数での上書きが機能すること確認
- [ ] 既存設定（settings.toml）が正しく読み込まれること確認