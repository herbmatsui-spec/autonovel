# AutoNovel 低コスト商用化ロードマップ（ゼロ予算 公開戦略 v1.0）

**作成日**: 2026-09-15
**目的**: 費用をかけずに（月額固定費を最小化し、変動費を売上連動にする形で）AutoNovelを商用公開する
**前提**: 1人開発・広告予算ゼロ・サーバー予算月1万円以下を目標

---

## 1. 精査結果サマリー（現状）

### 1.1 実装済み資産（そのまま商用化に使える）

| 領域 | 実装状況 | 場所 |
|:---|:---|:---|
| Stripe決済（Checkout / Portal / Webhook） | ✅ 実装済・べき等性テストあり | [`src/backend/routers/billing.py`](../src/backend/routers/billing.py), [`billing_webhook.py`](../src/backend/routers/billing_webhook.py), [`src/services/billing/stripe_client.py`](../src/services/billing/stripe_client.py) |
| クレジット制（消費・付与・枯渇ブロック） | ✅ 実装済 | [`src/config/billing_plans.py`](../src/config/billing_plans.py), `src/services/billing/credit_service.py` |
| プラン体系（free/starter/pro/enterprise） | ✅ 実装済 | [`src/config/billing_plans.py`](../src/config/billing_plans.py) |
| マルチテナancy + JWT認証 + RBAC | ✅ 実装済 | `src/backend/auth.py`, `src/backend/security/`, migration 0027 |
| LLMコストガード（サーキットブレーカー/予算ガード） | ✅ 実装済 | [`plans/PROPOSAL_05_CIRCUIT_BREAKER_AND_BUDGET_12STEPS.md`](./PROPOSAL_05_CIRCUIT_BREAKER_AND_BUDGET_12STEPS.md) |
| プロンプトキャッシュ・モデルルーティング | ✅ 実装済 | `src/llm/model_router.py`, `src/backend/feature_flags.py` |
| 本番Docker構成（healthcheck分離・非特権） | ✅ 準備完了 | [`docker-compose.prod.yml`](../docker-compose.prod.yml) |
| 利用規約・プライバシーポリシー | ✅ 制定済 | [`docs/legal/TERMS_OF_SERVICE.md`](../docs/legal/TERMS_OF_SERVICE.md), [`PRIVACY_POLICY.md`](../docs/legal/PRIVACY_POLICY.md) |
| ePUB/ZIP/マルチメディア納品 | ✅ 実装済 | `src/easy_mode/`, `src/publishers/` |
| OpenAPI型同期・ProblemDetails | ✅ 実装済 | [`plans/PROPOSAL_03_OPENAPI_TYPESYNC_12STEPS.md`](./PROPOSAL_03_OPENAPI_TYPESYNC_12STEPS.md) |

### 1.2 現状の問題（シミュレーション v2 実行結果）

[`scripts/simulations/saas_revenue_simulation_v2.py`](../scripts/simulations/saas_revenue_simulation_v2.py) を実行した結果（36ヶ月）:

| シナリオ | 36ヶ月後ユーザー | MRR | 月次純利益 | 3年累積 |
|:---|---:|---:|---:|---:|
| STRESS TEST | 1,110 | JPY 140万 | **-742万** | **-2.25億** |
| REALISTIC BASE | 3,169 | JPY 734万 | **-754万** | **-2.03億** |
| OPTIMISTIC | 9,267 | JPY 2,995万 | **-1,244万** | **-2.64億** |

**根本原因**:
1. **LLM費がMRRの68%超**（BASE: LLM 754万 vs MRR 734万 → 粗利マイナス）
2. **人件費 250〜350万/月が構造赤字の主因**（1人開発なら不要）
3. **固定インフラ 15〜20万/月**（未契約ユーザーがいても発生）
4. **1話あたり原価 JPY 63.7** がクレジット単価（JPY 0.35〜0.6）を上回る場面あり

**→ 結論: 「大手SaaS型」の完全版を 0 予算で運用するのは不可能。 「最小構成・変動費連動・段階的公開」に切り替える必要がある。**

---

## 2. 低コスト商用化の基本原則（3原則）

### 原則1: 固定費ゼロ主義 — 売上が発生するまで月額固定費を払わない

| 項目 | 従来想定 | 低コスト版 | 月額削減 |
|:---|---:|---:|---:|
| サーバー | 専用VPS 15-20万/月 | Fly.io / Railway 無料枠 → スリープ型小インスタンス | -99% |
| DB | 専用Postgres + AGE | Supabase Free / Neon Free (500MB) | -100% |
| キュー | Redis専用 | SQLite Huey（既存実装、`HUEY_BACKEND=sqlite`） | -100% |
| ベクター | ChromaDBサーバー + pgvector | SQLite内蔵モード（既存: `sqlite_rag_embedding`） | -100% |
| 監視 | Grafana/Datadog | UptimeRobot無料 + FastAPI /health エンドポイント | -100% |
| CDN/ドメイン | Cloudflare有料 | Cloudflare Free + 独自ドメイン年1,650円 | -95% |
| 人件費 | 250-350万/月 | 1人開発（自身の労働） | -100% |

**実装補足**: 本プロジェクトは既に SQLite フォールバック実装が完了している
（[`plans/PROPOSAL_06_DB_DIALECT_AND_MIGRATIONS_12STEPS.md`](./PROPOSAL_06_DB_DIALECT_AND_MIGRATIONS_12STEPS.md)のTypeDecorator、
`HUEY_BACKEND=sqlite`、`REQUIRE_PG=False`、`REQUIRE_CHROMA=False`）。
**この構成なら Fly.io / Railway の無料枠（512MB RAM）で動作する。**

### 原則2: LLM費は「クレジット前払い」で100%売上連動にする

- ユーザーは先にクレジットを購入 → LLMを叩くのはクレジット残高があるときだけ
- 原価率60%を超えたモデルはPremium専用に隔離（既存 [`PLOT_CREDIT_MODEL.md`](../PLOT_CREDIT_MODEL.md) のtier化案）
- フリープランは月1話×3,000字に制限（原価 JPY 5.6/月/人）

### 原則3: 0円マーケティング — プロダクト自体を広告にする

- **GitHub Public リポジトリ + READMEでバイラル獲得**（デモGIF既存: `docs/demo.gif`）
- **生成物に「AutoNovelで生成」の署名入り**（無料版のみ。有料版は署名なし＝フリーミアム誘導）
- 小説投稿サイト（なろう・カクヨム）に AI共創作品を投稿し、プロフィールにツールリンク
- Product Hunt / Qiita / Zenn に技術記事投稿（ゼロ円）

---

## 3. 公開ステージ別プラン（段階的スケール）

### Stage 0: プライベートβ（〜ユーザー50人）— 月額コスト目標: **¥0〜1,500**

| 項目 | 構成 |
|:---|:---|
| ホスティング | Fly.io 無料枠（shared-cpu-1x × 1、2GB未満）または自宅PC + Cloudflare Tunnel |
| DB | SQLite（`DATABASE_URL=sqlite:///storage/autonovel.db`） |
| キュー | Huey SQLite モード |
| LLM | Gemini 2.5 Flash 無料枠（RPM 10、RPD 250）+ OpenRouter fallback |
| 決済 | Stripe Test Mode → 招待制で直接銀行振込（個人間） |
| 招待 | 限定20人、手動招待コード（既存 `ALLOWED_API_KEYS` で代用可） |

**この段階では「商用公開」というより動作検証。生成コストは自腹で月1,500円以下に収める。**

### Stage 1: パブリックβ（〜ユーザー500人）— 月額コスト目標: **〜¥5,000 + 変動費**

| 項目 | 構成 |
|:---|:---|
| ホスティング | Fly.io $2-3/月インスタンス（shared-cpu-1x, 512MB）× 2（backend + worker） |
| DB | Supabase Free（500MB、Postgres + Auth込み）or Neon Free |
| キュー | Huey SQLite（1台構成なら継続） |
| LLM | Gemini Flash 有料（クレジット前払いで回収） |
| 決済 | **Stripe Live モード稼働開始**（既存コードがそのまま使える） |
| 公開 | `autonovel.app` 等のドメイン（Cloudflare Free + 年1,650円） |

**開始条件**: Stage 0で生成品質の苦情が月0件、LLM月額コストがクレジット売上の60%以内。

### Stage 2: 商用公開（〜ユーザー5,000人）— 月額コスト目標: **売上の〜40%以内**

| 項目 | 構成 |
|:---|:---|
| ホスティング | Fly.io / Hetzner VPS（€4.5/月 ≒ ¥750）+ Docker Compose |
| DB | Supabase Pro（$25/月）または Hetzner内 Postgres 16 |
| キュー | Redis（Fly.io アドオン or 自前Hetzner） |
| RAG | pgvector（Supabase内蔵）+ SQLiteフォールバック維持 |
| LLM | モデルルーティング: easy=Flash / pro=Flash→mini / climax=Sonnet |
| 決済 | Stripe Live + Customer Portal（既存実装） |

**この段階で初めて [`docker-compose.prod.yml`](../docker-compose.prod.yml) の5コンテナ構成をフル活用。**

---

## 4. 料金プラン再設計（原価率60%以下を強制）

既存 [`src/config/billing_plans.py`](../src/config/billing_plans.py) を以下に改定:

```python
PLAN_CONFIG = {
    "free":     {"price_jpy": 0,    "monthly_credits": 50,   "max_parallel_jobs": 1},  # 現状維持
    "starter":  {"price_jpy": 880,  "monthly_credits": 300,  "max_parallel_jobs": 2},  # 980→880円（心理的境界）
    "pro":      {"price_jpy": 2480, "monthly_credits": 1200, "max_parallel_jobs": 4},
    "enterprise": {"price_jpy": 7980, "monthly_credits": 5000, "max_parallel_jobs": 10},
}
```

**根拠**:
- 1クレジット = 約2.9〜8.3円相当 → LLM原価の2倍以上のマージンを確保
- 既存 `TASK_CREDIT_COSTS`（[`src/config/billing_plans.py:34`](../src/config/billing_plans.py:34)）:
  - 本文1話=10クレジット（¥29〜83の売上 vs 原価¥63.7）→ **Pro以上でクライマックス品質(25クレジット)に誘導し原価率を正常化**
- フリープラン原価: 月50クレジット分 ≒ 5話分 … **要制限変更（後述）**

### 4.1 フリープランの現実化（重要）

シミュレーションではフリーユーザーが全体の57%を占めLLM費を圧迫。
[`FREEMIUM_10YEN_MODEL.md`](../FREEMIUM_10YEN_MODEL.md) の設計を参考に:

| 項目 | 変更前 | 変更後 |
|:---|:---|:---|
| 生成回数 | 50クレジット/月（実質5話） | **1話/月（10クレジット）+ 残40クレジットは編集のみ** |
| モデル | デフォルト | **Gemini Flash固定**（上位モデル選択不可） |
| GraphRAG | 利用可 | **無効**（`ENABLE_GRAPHRAG=False`をフリーユーザーへ強制） |
| エクスポート | ZIP/EPUB可 | **TXTのみ**（`Watermarked`署名付き） |
| マルチメディア | 利用可 | 無効（既存 `ENABLE_MULTIMEDIA` フラグで個別制御） |

**実装箇所**: `src/backend/feature_flags.py` をティア別判定に拡張（`is_multimedia_enabled(user.tier)` 形式へ）。

---

## 5. 実装タスクリスト（0円公開に向けた最小セット）

### Phase A: 公開前の必須修正（1週間）

- [ ] **A1. フリープラン制限の強制実装**
  - `src/backend/feature_flags.py` → ユーザーティア参照型フラグ判定
  - `src/llm/model_router.py` → フリーユーザーは `model_planning/writing/audit` 全てFlash固定
- [ ] **A2. AUTH_DISABLED の本番ガード**
  - `.env.example` に記載の `AUTH_DISABLED=False` を、`APP_ENV=production` 時は強制False化（起動時バリデーション）
  - 場所: `src/backend/config.py` または `src/config/`
- [ ] **A3. JWT_SECRET_KEY の強度チェック**
  - 32文字未満 / デフォルト値の場合、productionで起動拒否
- [ ] **A4. レート制限の有効化**
  - 既存 `src/backend/rate_limit.py` を全ルーター適用（フリーユーザー1日3生成まで等）
- [ ] **A5. Docker イメージ最適化**
  - [`plans/PROPOSAL_08_DOCKER_OPTIMIZATION_AND_HEALTHCHECK_12STEPS.md`](./PROPOSAL_08_DOCKER_OPTIMIZATION_AND_HEALTHCHECK_12STEPS.md) を実施（無料枠512MBに収めるため必須）

### Phase B: 決済有効化（1週間）

- [ ] **B1. Stripe Live アカウント開設**（個人事業主でも可・初期費用0円）
- [ ] **B2. Price ID の作成と `.env` 反映**（free/starter/pro/enterprise 4種）
- [ ] **B3. Webhook エンドポイントの本番登録**（`/api/billing/webhook`）
  - べき等性テスト済み（`tests/unit/test_webhook_idempotency.py`）なのでそのまま稼働可
- [ ] **B4. 特定商取引法に基づく表示ページ作成**（フロントエンドに `/legal/commerce` を追加）
- [ ] **B5. 請求書・領収書の自動発行設定**（Stripe標準機能のみで対応、実装0）

### Phase C: 低コストデプロイ（3日）

- [ ] **C1. Fly.io へのデプロイ**（fly.toml 作成、`docker-compose.prod.yml` の内容を移植）
- [ ] **C2. Supabase / Neon Postgres の接続設定**（`DATABASE_URL` 差し替えのみ）
- [ ] **C3. Cloudflare でDNS + SSL設定**（年1,650円のみの実費）
- [ ] **C4. UptimeRobot で /health/liveness 監視**（無料）

### Phase D: 0円マーケティング（公開日から継続）

- [ ] **D1. README のデモGIF改善 + 「なぜ無料で使えるか」セクション追加**
- [ ] **D2. Qiita / Zenn に技術記事**（GraphRAG・マルチエージェントの設計解説 → エンジニア作家を獲得）
- [ ] **D3. なろう/カクヨムにサンプル作品投稿**（AutoNovel併記、規約OK範囲）
- [ ] **D4. Product Hunt / 便利ツールまとめサイトへ申請**
- [ ] **D5. 生成物に "Powered by AutoNovel" 署名**（無料版のみ、拡散装置として機能させる）

---

## 6. 財務シミュレーション（低コスト版・1人開発）

### 前提の変更点

| 項目 | 従来 | 低コスト版 |
|:---|---:|---:|
| 人件費 | 250-350万/月 | **0円**（1人・副業） |
| サーバー固定費 | 15-20万/月 | **¥750-3,000/月** |
| LLM原価率 | 103-160% | **60%以下**（クレジット前払い+Flash固定） |
| フリーユーザー原価 | JPY 127/月 | **JPY 5.6/月** |

### 月次損益（Stage 2、3年後相当の楽観シナリオ）

```
ユーザー 5,000人（フリー4,300 / 有料700想定）
├── 有料 700人 × 平均ARPU ¥2,800 = 売上 JPY 196万/月
├── LLM費: 有料原価 60% (¥118万) + フリー4300人×¥5.6 (¥2.4万) = JPY 120万/月
├── インフラ: JPY 1万/月
├── Stripe手数料 3.6%: JPY 7万/月
└── 純利益: JPY 196万 - 128万 = **JPY 68万/月（黒字）**
```

**損益分岐点: 有料ユーザー約 45〜50人（月売上 約12.6万）** で固定費+LLM費をカバー。
0予算でも**有料50人到達**は現実的な最初のマイルストーン。

---

## 7. リスクと対策

| リスク | 対策 |
|:---|:---|
| LLM料金の変動（Flash値上げ等） | OpenRouter経由で複数モデル切替可能（既存 `OPENROUTER_*` 設定） |
| 無料ユーザーの悪用（大量生成） | レート制限 + クレジット枯渇ブロック（既存実装）+ IP制限 |
| Stripe審査通過の遅延 | Stage 0-1は銀行振込で先行、Live通過後にStripeへ切替 |
| SQLite→Postgres移行の不具合 | [`PROPOSAL_06`](./PROPOSAL_06_DB_DIALECT_AND_MIGRATIONS_12STEPS.md) の往復検証スクリプトを本番前に実行 |
| 1人運用でのサポート負荷 | Discord コミュニティ（無料）+ FAQ自動応答 + 返信48hを規約に明記 |
| 法律・税務（インボイス等） | 売上50万/月超えたら個人事業主開業 + 青色申告（実費ほぼ0） |

---

## 8. 直近30日のアクション要約

1. **Day 1-7**: Phase A（フリー制限・セキュリティガード・Docker最適化）
2. **Day 8-14**: Phase B（Stripe Live開通・法務ページ）
3. **Day 15-17**: Phase C（Fly.io + Supabase + ドメイン設定）
4. **Day 18-30**: Phase D（記事執筆・作品投稿・Product Hunt）

**月間実費予算: ドメイン1,650円/年を含めて実質 ¥1,500/月以下で商用公開が可能。**

---

## 関連ドキュメント

- 黒字化施策9選: [`PROFITABILITY_PROPOSALS.md`](../PROFITABILITY_PROPOSALS.md)
- フリーミアム設計詳細: [`FREEMIUM_10YEN_MODEL.md`](../FREEMIUM_10YEN_MODEL.md)
- プロット課金モデル: [`PLOT_CREDIT_MODEL.md`](../PLOT_CREDIT_MODEL.md)
- 収益シミュレーション: [`scripts/simulations/saas_revenue_simulation_v2.py`](../scripts/simulations/saas_revenue_simulation_v2.py)
- 法務ドキュメント: [`docs/legal/`](../docs/legal/)
