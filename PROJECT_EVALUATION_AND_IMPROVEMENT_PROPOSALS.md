# AutoNovel プロジェクト詳細評価レポート & 改善提案 9項目

**作成日**: 2026-09-14
**対象**: e:/hhh（AutoNovel v4.9.0 — AI小説生成SaaS）
**評価方法**: 実コード静的精査 + 単体テスト実行（1,772件収集） + カバレッジ計測

---

# Part 1: 総合評価

## 結論: **C+（商業サービスとして投入不可、個人実験としては過剰品質）**

| 領域 | スコア | 根拠 |
|---|---|---|
| アーキテクチャ設計 | B- | UoW/Outbox/Repository分離の理想は描けているが、実装の統一感がない |
| セキュリティ | **D** | JWT鍵のgitコミット、認証穴、レースコンディション |
| テスト | C- | 1,772件あるがコア機能0%。CIゲート割れ確認済み |
| 実装の完成度 | C | 幅は広い（801ファイル）が深さがない。動かない機能あり |
| 保守性 | D+ | 設定ファイル5世代共存、repo二重管理、scratch残留 |
| 商用投入可能性 | **D+** | 1人でも課金ユーザーを抱えると物理的に危険 |

## 定量実測値

| 指標 | 値 |
|---|---|
| Pythonソースファイル数 | 801（src/のみ） |
| テストファイル数 | 403（Python）+ 306（frontend ts/tsx） |
| pytest収集テスト数 | 1,772（単体のみ） |
| ステートメント数 | 22,612 |
| **ラインカバレッジ** | **25.83%**（15,649行未カバー） |
| CIカバレッジゲート（35%） | **FAIL 確認済み** |
| 計画書ドキュメント | plans/ 34本 + docs/plans/ 数十本 |
| 認証保護済みルーター | 38中わずか4ドメイン |

---

# Part 2: 重大欠陥の詳細（リリース阻止レベル）

## 🔴 D-1: JWT秘密鍵のハードコード（gitコミット済み）

**ファイル**: `src/backend/security/jwt.py:7`

```python
# 本番環境では環境変数から読み込むこと (SHA256用に32バイト以上)
SECRET_KEY = "autonovel-super-secret-key-32bytes-minimum-change-in-prod"
```

**影響**:
- コメントで「本番では環境変数から」と宣言しているが実装が存在しない
- `settings.AUTH_SECRET` 等の設定項目も [`config.py`](src/backend/config.py) に存在しない
- 攻撃者はこの公開鍵で任意の `user_id` / `role` の有効トークンを生成可能
- **全ユーザーなりすまし・全テナント横断アクセスが成立**

**深刻度**: ★★★★★（SaaSの生命線）

---

## 🔴 D-2: 認証保護の欠落（38ルーター中34が無保護）

**実測**: `get_current_user` を依存性注入しているのは以下のみ:
- `src/backend/routers/books.py` ✅
- `src/backend/routers/auth.py` ✅（/me のみ）
- `src/backend/routers/billing.py` ✅
- `src/backend/security/credit_guard.py` ✅

**無認証で公開されている主要エンドポイント**:

| ルーター | prefix | 問題 |
|---|---|---|
| [`anti_ai.py`](src/backend/routers/anti_ai.py) | `/admin/anti_ai` | **admin**なのに認証なし |
| [`cost.py`](src/backend/routers/cost.py) | `/api/cost` | 原価情報が誰でも閲覧可 |
| [`trace.py`](src/backend/routers/trace.py) | `/api/trace` | トレース情報露出 |
| [`episodes.py`](src/backend/routers/episodes.py) | `/api/episodes` | 他ユーザーの原稿読み取り可能 |
| [`plots.py`](src/backend/routers/plots.py) | `/api/plots` | 同上 |
| [`commercial.py`](src/backend/routers/commercial.py) | `/commercial` | 商用機能無保護 |

**補足**:
- [`auth.py:35`](src/backend/auth.py:35) の `require_api_key` は `APP_ENV == "development"` で**検証自体をスキップ**
- [`config.py:53`](src/backend/config.py:53) の `AUTH_DISABLED: bool = False` は**どの認証フローにも接続されていない死んだ設定**
- PLAN_10（マルチテナンシー）を謳うが、DBモデルに**tenant（組織）概念が存在しない**。ユーザー単位の所有権チェックのみ

**深刻度**: ★★★★★

---

## 🔴 D-3: クレジット消費のレースコンディション（実金額欠損）

**ファイル**: `src/services/billing/credit_service.py:55-83`

```python
async def deduct_credits(self, user_id, amount, ...):
    current_balance = await self.get_balance(user_id)  # ① 読み取り
    if current_balance < amount:
        raise InsufficientCreditsError(...)
    new_balance = current_balance - amount             # ② アプリ側で減算
    transaction = CreditTransaction(..., balance_after=new_balance)
    self.db.add(transaction)
    await self.db.commit()                             # ③ INSERT
```

**問題**:
1. `SELECT` → アプリ側減算 → `INSERT` の3段階で**行ロック（FOR UPDATE）も原子性UPDATEもない**
2. 同時2リクエストが同じ残高を読み、両方が減算INSERT → **二重消費**
3. 残高算出が「直近トランザクションの `balance_after`」依存のため、同時INSERT時の順序で結果が不定
4. `users.credits` カラムとの**二重管理**（[`auth.py`](src/backend/routers/auth.py) は `credits=50` を直接INSERT、CreditServiceは transactions から算出）— 正がどちらか不明

**深刻度**: ★★★★★（課金SaaSの金銭整合性）

---

## 🔴 D-4: Stripe Webhook のべき等性欠如 + 同期API呼び出し

**ファイル**: `src/backend/routers/billing_webhook.py`

```python
# L52: コード自体が自認
# イベントの重複処理を防止するため、イベントIDを記録すべき
# ここでは簡略化のため、主要なイベントタイプのみ処理

# L94: 非同期dbセッションの中で同期SDK呼び出し
subscription = stripe.Subscription.retrieve(subscription_id)
```

**問題**:
1. イベントIDの記録がなく、Stripeのリトライで**重複クレジット付与**が発生
2. 同期 `stripe.Subscription.retrieve()` がイベントループをブロック → タイムアウト → Stripeリトライ増幅
3. プラン別クレジット額がハードコード（L113-118、`price_starter: 300` 等）
4. router層から直接 `select(User).where(...)` を発行（層違反）

**深刻度**: ★★★★☆

---

## 🔴 D-5: ランタイムクラッシュ確定バグ（NameError）

**ファイル**: `src/backend/database/uow.py`

```python
# L59: 型アノテーションで宣言
self._pdca_history: PDCAHistoryRepository | None = None

# L166-169: プロパティで使用
@property
def pdca_history(self) -> PDCAHistoryRepository:
    if self._pdca_history is None:
        self._pdca_history = PDCAHistoryRepository(self.session)  # ← NameError
```

**検証済み**: [`repositories/__init__.py`](src/backend/database/repositories/__init__.py) を確認した結果、`PDCAHistoryRepository` は:
- エクスポート一覧 `__all__` に存在しない
- インポート文自体が存在しない

→ `uow.pdca_history` にアクセスした瞬間 `NameError` でクラッシュ。**PDCA履歴機能（PLAN_15系）は実質動作しない**。

**深刻度**: ★★★★☆（機能死）

---

# Part 3: 改善提案 9項目

## 提案1: JWT秘密鍵の環境変数化【最優先・工数0.5日】

**対象**: `src/backend/security/jwt.py`
**目的**: 全ユーザーなりすまし可能性の排除

```python
# 修正後
from src.backend.config import settings

class Settings(BaseSettings):
    # config.py に追加
    JWT_SECRET_KEY: str = ""  # 本番では必須
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

# jwt.py
def _get_secret() -> str:
    secret = settings.JWT_SECRET_KEY
    if not secret or len(secret) < 32:
        if settings.APP_ENV == "production":
            raise RuntimeError("JWT_SECRET_KEY must be set (min 32 chars) in production")
        return secrets.token_urlsafe(48)  # devのみ自動生成
    return secret
```

**受け入れ基準**:
- [ ] `JWT_SECRET_KEY` が `.env.example` に追加されている
- [ ] production起動時に鍵未設定なら起動失敗する
- [ ] 既存トークンの互換性検証テスト（鍵変更で旧トークンが401になること）を追加

---

## 提案2: 全ルーターへの認証強制（ミドルウェア一括化）【工数1〜2日】

**対象**: `src/backend/server.py`、`src/backend/auth.py`
**目的**: 認証穴の構造的解消（個別修正の繰り返しをやめる）

```python
# server.py にグローバル認証ミドルウェアを追加
from starlette.middleware.base import BaseHTTPMiddleware

PUBLIC_PATHS = {
    "/health", "/api/health", "/api/auth/login", "/api/auth/register",
    "/api/billing/webhook",  # 署名検証で保護
    "/docs", "/openapi.json",
}

class AuthEnforcementMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)
        if settings.AUTH_DISABLED and settings.APP_ENV == "development":
            return await call_next(request)  # dev明示時のみ
        token = request.headers.get("Authorization", "")
        if not token.startswith("Bearer "):
            return JSONResponse({"detail": "認証が必要です"}, status_code=401)
        try:
            decode_token(token[7:])
        except HTTPException:
            return JSONResponse({"detail": "無効なトークン"}, status_code=401)
        return await call_next(request)
```

**受け入れ基準**:
- [ ] `pytest` で全エンドポイント一覧をOpenAPIから取得し、認証必須を一括アサートするテスト（`test_auth_coverage_all_endpoints.py`）を新設
- [ ] `/admin/anti_ai` に admin ロール検証を追加（現状は認証すらない）
- [ ] `AUTH_DISABLED` をdev環境限定かつ明示オプトインに変更

---

## 提案3: クレジット消費の原子化【最優先・工数1日】

**対象**: `src/services/billing/credit_service.py`
**目的**: 二重消費の排除

```python
async def deduct_credits(self, user_id, amount, transaction_type, description, task_id=None) -> bool:
    # ① 原子性UPDATE（残高が足りる場合のみ減算、1クエリで完結）
    result = await self.db.execute(
        update(User)
        .where(User.id == user_id, User.credits >= amount)
        .values(credits=User.credits - amount)
        .returning(User.credits)
    )
    new_balance = result.scalar_one_or_none()
    if new_balance is None:
        raise InsufficientCreditsError(f"Required: {amount}")
    # ② 同一トランザクション内で取引記録（balance_after は残高の正をUser側に一本化）
    self.db.add(CreditTransaction(
        user_id=user_id, amount=-amount,
        balance_after=new_balance,  # 参考記録（正ではない）
        transaction_type=transaction_type, task_id=task_id, description=description,
    ))
    await self.db.commit()
    return True
```

**併せて必須**:
- `users.credits` を**唯一の正（Single Source of Truth）**と宣言し、transactionからの残高再構築ロジック（現 `get_balance`）を廃止または監査用に降格
- SQLite本番想定のため、`BEGIN IMMEDIATE` 相当の書き込み直列化も検討

**受け入れ基準**:
- [ ] 同時10並列で100クレジット消費×10リクエスト → 消費合計が正確に1000、残高が負にならないことを証明するテスト（`test_concurrent_deduction.py`）を新設
- [ ] `InsufficientCreditsError` 時に取引記録が残らないことを確認

---

## 提案4: Stripe Webhook のべき等化 + 非同期化【工数2日】

**対象**: `src/backend/routers/billing_webhook.py`

**修正内容**:
1. **イベントID記録テーブル**を追加（マイグレーション新設）:

```python
class ProcessedWebhookEvent(Base):
    __tablename__ = "processed_webhook_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)  # Stripe event.id
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# ハンドラ冒頭
if await db.get(ProcessedWebhookEvent, event["id"]):
    return {"status": "already_processed"}  # べき等応答
```

2. **同期呼び出しを `asyncio.to_thread` 化**:
```python
subscription = await asyncio.to_thread(stripe.Subscription.retrieve, subscription_id)
```

3. **プランクレジット額を設定へ移動**（`src/config/billing_plans.py` の `PLAN_CONFIG` と統合、L113のハードコード削除）

4. **ロジックをサービス層へ移動**（routerから直接SQLクエリを排除、`CreditService` に集約）

**受け入れ基準**:
- [ ] 同一イベントを2回送信 → 2回目は付与されないことをテスト
- [ ] `stripe.Subscription.retrieve` がスレッドプールで実行されることをモックで確認

---

## 提案5: UoW未インポート修正 + リポジトリ登録の自動化【工数0.5日】

**対象**: `src/backend/database/uow.py`、`src/backend/database/repositories/__init__.py`

**即時修正**:
```python
# repositories/__init__.py に追加（クラスが存在する場合）
from .pdca_history import PDCAHistoryRepository
# クラス自体が存在しない場合は database/repositories/pdca_history.py を新規作成
```

**構造的修正**（2箇所更新忘れを防ぐ）:
```python
# プロパティ17個の手書きを廃止し、遅延生成を統一
def _repo(self, attr: str, cls):
    if getattr(self, attr) is None:
        setattr(self, attr, cls(self.session))
    return getattr(self, attr)

@property
def pdca_history(self):
    return self._repo("_pdca_history", PDCAHistoryRepository)
```

**受け入れ基準**:
- [ ] `uow.pdca_history` へのアクセスが NameError で落ちないことを確認するテスト
- [ ] `__aexit__` のリセット処理をリポジトリ一覧から自動生成し、追加忘れを構造的に排除
- [ ] `mypy src/backend/database/uow.py` がエラー0

---

## 提案6: コアモジュールのカバレッジ 0% 解消【工数3〜5日】

**実測**: 25.83%（ゲート35%未達）。特に**コア中のコアが0%**:

| ファイル | 行数 | カバレッジ |
|---|---|---|
| `src/services/vector_store.py` | 1,412 | **0.00%** |
| `src/services/writing_services.py` | 973 | **0.00%** |
| `src/services/tracing_service.py` | 106 | **0.00%** |
| `src/services/unified_pipeline_config.py` | 138 | **0.00%** |

**方針**:
1. 新規計画書（P6, P7...）を**作らない**。既存P0〜P5を完遂させる
2. 0%の4ファイルを最優先ターゲットに、まず正常系パスのみのテストを追加
3. カバレッジゲートを**35%固定から「前回比非劣化」に変更**（`--cov-fail-under` の代わりに diff-cover をCI導入）

**受け入れ基準**:
- [ ] `vector_store.py` と `writing_services.py` のカバレッジが各40%以上
- [ ] CIでカバレッジ25.83%→35%到達
- [ ] 「追加時にのみ非劣化を強制」するdiff-cover設定が [.github/workflows](.github) に反映

---

## 提案7: 重複実装・デッドコードの一掃【工数2日】

**実測された重複**:

| 種別 | 実態 | 処置 |
|---|---|---|
| 設定5世代 | `config/archetypes.py` / `_new` / `_fixed_legacy` / `_stub_legacy` / `_legacy` | 最新1つのみ残し削除 |
| repo二重管理 | `src/backend/database/repo_book.py` vs `repositories/book.py` | `repositories/` に統一、旧を削除 |
| writing系 | `writing_service.py` vs `writing_services.py`、`writing/writing.py` vs `_writing.py` vs `agent.py` | 統合または明示的非推奨化 |
| skill二重 | `agents/skills/v1/` vs `v2/` | v1を `deprecated/` へ移動 |
| scratch残留 | `scripts/scratch/` 12本、`scripts/verification/` 10本 | git履歴に残す旨で削除 |

**受け入れ基準**:
- [ ] `vulture src` で検出される未使用コードが（例外リスト込みで）ゼロ
- [ ] `config/` 配下のarchetypesが1ファイルに統一されている
- [ ] 削除前に `pytest` 全緑を確認（削除による破壊がないことの証明）

---

## 提案8: router→services→repositories の層違反矯正【工数2日】

**実測**: [`billing_webhook.py`](src/backend/routers/billing_webhook.py) がrouter層から直接SQL発行。一方 [`books.py`](src/backend/routers/books.py) は正しくUoW経由。**同一プロジェクトに2つの作法が混在**。

**方針**:
```python
# ルール: routerはHTTP変換のみ。DBへのアクセスはすべてUoWまたはService経由
# 違反検出をruffカスタムルール or CI grepで強制
# CI チェック例
if grep -rEn "select\(|update\(|delete\(" src/backend/routers/; then
  echo " routers must not import sqlalchemy directly"; exit 1
fi
```

**移行対象**: `billing_webhook.py`、`billing.py`、`auth.py` の直接クエリを `CreditService` / `UserService` へ移動

**受け入れ基準**:
- [ ] CIに「routers内の直接SQL検出」ゲートを追加し、検出ゼロ
- [ ] `books.py` 方式（UoW経由）をプロジェクト標準として `docs/architecture.md` に明記

---

## 提案9: 機能凍結宣言 + 計画書統合【工数0.5日 + 継続】

**現状**: `plans/` 34本 + `docs/plans/` 数十本。PLAN_01〜18、P0〜P5、108STEPSロードマップが乱立し、**PLAN_18（原価90%削減）は未着手**（対象ファイルが存在せず）。[`IMPLEMENTATION_SUMMARY.md:95`](IMPLEMENTATION_SUMMARY.md:95) は「環境問題によりテスト実行できず」と検証放棄を自認。

**方針**:
1. **1ヶ月の機能凍結**を宣言（新PLANの作成禁止）
2. 既存34本の計画書を3つに統合:
   - `ROADMAP_DONE.md`（完了済み＋証拠テスト名）
   - `ROADMAP_ACTIVE.md`（進行中、担当・完了条件つき、**最大5項目**）
   - `ROADMAP_FREEZED.md`（凍結中、着手禁止）
3. **完了の定義を厳格化**: 「実装した」ではなく「テストが緑でCIが通った」のみを完了と認定
4. `IMPLEMENTATION_SUMMARY.md` のような「検証できませんでした」を含む完了報告を禁止

**受け入れ基準**:
- [ ] plans/ の全ファイルが3つのロードマップに再分類されている
- [ ] ROADMAP_ACTIVE が5項目以下
- [ ] 未着手計画（PLAN_18等）に「凍結」ラベルが付与されている

---

# Part 4: 実施順序と工数サマリー

| 順序 | 提案 | 工数 | 効果 |
|---|---|---|---|
| 1日目 | 提案1（JWT鍵） | 0.5日 | なりすまし排除 |
| 1〜2日目 | 提案3（クレジット原子化） | 1日 | 金銭整合性 |
| 3〜4日目 | 提案2（認証一括強制） | 1〜2日 | 全API保護 |
| 5日目 | 提案5（UoW修正） | 0.5日 | 機能死解消 |
| 6〜7日目 | 提案4（Webhookべき等） | 2日 | 重複課金排除 |
| 2週目 | 提案7（デッドコード） | 2日 | 保守性回復 |
| 2〜3週目 | 提案8（層矯正） | 2日 | 一貫性確立 |
| 3〜4週目 | 提案6（カバレッジ） | 3〜5日 | 品質ゲート回復 |
| 継続 | 提案9（凍結+統合） | 0.5日+ | 集中力の回復 |

**合計**: 約3〜4週間の集中作業で「デモ」から「課金ユーザー1人を安全に受け入れられる状態」に到達可能。

---

# Part 5: 最重要メッセージ

このプロジェクトの最大のリスクは、**見た目の完成度の高さ**である。
801ファイル、1,772テスト、34計画書という規模感は「大きなプロジェクト」に見えるが、
実態は「秘密鍵がコミットされ、admin画面が無認証で、クレジットが二重消費でき、
PDCA機能がNameErrorで落ち、カバレッジゲートが割れたまま」である。

**次の一手は新機能でも新計画書でもない。既存コードの固定化である。**
