# PLAN 10: データベースのマルチテナント化と認証基盤 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 データベース・認証認可・マルチテナント分離基盤  
**目的**: シングルユーザー・ローカル前提のデータ構造（`books`, `episodes` 等）を完全なマルチテナントSaaS構造へと移行し、ユーザー認証（JWT/OAuth）、テナントスコープ認可、データ漏洩防止を達成する。  
**前提**: 既存のローカル開発データとの後方互換性を担保しつつ、1ステップずつ単一ファイル単位で実装・検証可能な粒度に分割。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | スキーマ | `src/models/user.py` (新規) | ユーザー・認証・テナント情報のPydanticモデル及びDTO定義 |
| **2** | ORMモデル | `src/backend/database/models.py` (修正) | `User` テーブル定義追加、および `Book`, `Episode`, `Branch` への `user_id` カラム追加 |
| **3** | マイグレーション | `src/backend/alembic/versions/xxxx_multitenancy_users.py` (新規) | `users` テーブル新設、各テーブルへの `user_id` 外部キー追加マイグレーション |
| **4** | データ移行 | `scripts/migrate_local_data_to_tenant.py` (新規) | 既存ローカルDBの全作品データを初期管理者ユーザーに安全に紐付ける移行スクリプト |
| **5** | セキュリティ | `src/backend/security/password.py` (新規) | Argon2 / bcrypt によるパスワードハッシュ化・検証ユーティリティ |
| **6** | トークン管理 | `src/backend/security/jwt.py` (新規) | JWTアクセストークンおよびリフレッシュトークンの発行・署名・検証エンジン |
| **7** | 認証依存性 | `src/backend/auth.py` (修正) | 静的キー検証から `get_current_user` / `require_auth` への全面リファクタリング |
| **8** | APIルーター | `src/backend/routers/auth.py` (新規) | サインアップ、ログイン、トークンリフレッシュ、プロフィール取得APIエンドポイント |
| **9** | テナント認可 | `src/backend/middleware/tenant_guard.py` (新規) | 他ユーザーの作品へのアクセスを403/404で遮断するテナントスコープ認可ガード |
| **10** | リポジトリ修正 | `src/infrastructure/repositories/` (修正) | 全クエリに `filter(user_id == current_user.id)` を強制するマルチテナント化 |
| **11** | フロントエンド | `frontend/src/context/AuthContext.tsx` (新規) | ログイン状態・トークン管理・Axios/Fetchリクエストヘッダー注入コンテキスト |
| **12** | 統合検証 | `tests/integration/test_multitenancy_isolation.py` (新規) | 複数ユーザー間でのデータ完全分離と不正アクセス遮断を検証する統合テスト |

---

## 各ステップの詳細仕様

### Step 1: ユーザー関連Pydanticモデル定義 (`src/models/user.py`)
* **目標**: ユーザー認証、登録、更新、レスポンスに必要なデータモデルを定義する。
* **実装内容**:
  ```python
  from __future__ import annotations
  from datetime import datetime
  from enum import Enum
  from pydantic import BaseModel, EmailStr, Field

  class UserRole(str, Enum):
      USER = "user"
      PRO = "pro"
      ADMIN = "admin"

  class UserStatus(str, Enum):
      ACTIVE = "active"
      SUSPENDED = "suspended"
      PENDING = "pending"

  class UserRegisterRequest(BaseModel):
      email: EmailStr = Field(..., description="メールアドレス")
      password: str = Field(..., min_length=8, max_length=128, description="パスワード")
      display_name: str = Field(..., min_length=1, max_length=50, description="作家名/表示名")

  class UserLoginRequest(BaseModel):
      email: EmailStr
      password: str

  class TokenResponse(BaseModel):
      access_token: str
      refresh_token: str
      token_type: str = "bearer"
      expires_in: int

  class UserProfileResponse(BaseModel):
      id: int
      email: str
      display_name: str
      role: UserRole
      status: UserStatus
      credits: int
      plan_tier: str
      created_at: datetime
  ```
* **受け入れ基準**: `mypy src/models/user.py` で型エラーゼロ。

---

### Step 2: ORMモデルの修正 (`src/backend/database/models.py`)
* **目標**: `User` テーブルを新設し、主要テーブルにテナント所有権を示す `user_id` カラムを追加する。
* **実装内容**:
  ```python
  from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index, text
  from sqlalchemy.orm import relationship

  class User(Base):
      __tablename__ = "users"

      id = Column(Integer, primary_key=True, autoincrement=True)
      email = Column(String(255), unique=True, nullable=False, index=True)
      hashed_password = Column(String(255), nullable=False)
      display_name = Column(String(100), nullable=False)
      role = Column(String(20), default="user", nullable=False)
      status = Column(String(20), default="active", nullable=False)
      plan_tier = Column(String(20), default="free", nullable=False)
      credits = Column(Integer, default=50, nullable=False)  # 初期無料クレジット
      stripe_customer_id = Column(String(255), nullable=True, index=True)
      created_at = Column(DateTime, server_default=func.now())
      updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

      books = relationship("Book", back_populates="owner", cascade="all, delete-orphan")

  # Book テーブルに user_id を追加
  # class Book(Base):
  #     ...
  #     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
  #     owner = relationship("User", back_populates="books")
  ```
* **受け入れ基準**: SQLAlchemy Base のメタデータに `users` テーブルが登録され、リレーションシップが成立すること。

---

### Step 3: Alembic マイグレーションスクリプト作成 (`src/backend/alembic/versions/xxxx_multitenancy_users.py`)
* **目標**: DBスキーマに破壊的変更を与えず、`users` テーブル作成と `user_id` 付与を行う。
* **実装内容**:
  - `users` テーブルを作成。
  - `books`, `publication_schedules` に `user_id` カラムを追加（初期値 null 許容で作成し、データ移行後に nullable=False へ変更可能にする二段階移行）。
  - `user_id` に外部キー制約および B-Tree インデックスを付与。
* **受け入れ基準**: `alembic upgrade head` でエラーなくマイグレーションが完了すること。

---

### Step 4: 既存ローカルデータの移行スクリプト (`scripts/migrate_local_data_to_tenant.py`)
* **目標**: 開発環境やテストに存在する既存の `autonovel.db` 内の作品データを救済する。
* **実装内容**:
  - デフォルトのシードユーザー（`admin@autonovel.local`, パスワード設定済み）を生成。
  - `user_id` が NULL の全 `books` レコードに上記シードユーザーの ID を割り当て。
  - 割り当て完了後、データの整合性をチェックしレポートを出力。
* **受け入れ基準**: 既存の全Bookレコードに有効な `user_id` が紐付き、外部キー違反が生じないこと。

---

### Step 5: パスワードセキュリティ実装 (`src/backend/security/password.py`)
* **目標**: 安全なハッシュ化アルゴリズムによるパスワード保護。
* **実装内容**:
  ```python
  from passlib.context import CryptContext

  pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

  def hash_password(password: str) -> str:
      return pwd_context.hash(password)

  def verify_password(plain_password: str, hashed_password: str) -> bool:
      return pwd_context.verify(plain_password, hashed_password)
  ```
* **受け入れ基準**: 異なるソルトにより同一パスワードでも異なるハッシュ値が生成され、`verify_password` が正常判定すること。

---

### Step 6: JWTトークンエンジン実装 (`src/backend/security/jwt.py`)
* **目標**: ステートレスな認証トークンの発行と検証。
* **実装内容**:
  - `create_access_token(user_id: int, role: str, expires_delta: timedelta | None = None) -> str`
  - `create_refresh_token(user_id: int) -> str`
  - `decode_token(token: str) -> dict[str, Any]` (署名検証、期限切れ判定、トークン種別チェック)
* **受け入れ基準**: 期限切れトークンが正しく `ExpiredSignatureError` を送出し、改ざんされた署名が弾かれること。

---

### Step 7: 認証依存関数（FastAPI Depends）のリファクタリング (`src/backend/auth.py`)
* **目標**: APIエンドポイントでユーザー情報を取得できるようにする。
* **実装内容**:
  ```python
  from fastapi import Depends, HTTPException, status
  from fastapi.security import OAuth2PasswordBearer
  from src.backend.security.jwt import decode_token

  oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

  async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
      if not token:
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="認証が必要です")
      payload = decode_token(token)
      user = await db.get(User, payload["sub"])
      if not user or user.status != "active":
          raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ユーザーが無効です")
      return user
  ```
* **受け入れ基準**: 正常なJWTでUserオブジェクトが注入され、無効なトークンでは401レスポンスが返ること。

---

### Step 8: 認証APIルーター実装 (`src/backend/routers/auth.py`)
* **目標**: ユーザー登録・ログイン・トークンリフレッシュ・マイページ情報提供。
* **実装内容**:
  - `POST /api/auth/register`: メールアドレス重複検証、パスワードハッシュ化、初期50クレジット付与。
  - `POST /api/auth/login`: メール・パスワード認証、Access/Refreshトークン発行。
  - `POST /api/auth/refresh`: リフレッシュトークンによるアクセストークン再発行。
  - `GET /api/auth/me`: 現在ログイン中のユーザープロフィールと残クレジット照会。
* **受け入れ基準**: サインアップからログイン、`/me` 取得までの一連のHTTPリクエストが通ること。

---

### Step 9: テナントスコープ認可ガード (`src/backend/middleware/tenant_guard.py`)
* **目標**: 他人の小説へのアクセスを確実に防止する。
* **実装内容**:
  ```python
  async def verify_book_ownership(book_id: int, current_user: User, db: AsyncSession) -> Book:
      book = await db.get(Book, book_id)
      if not book:
          raise HTTPException(status_code=404, detail="作品が見つかりません")
      if book.user_id != current_user.id and current_user.role != "admin":
          raise HTTPException(status_code=403, detail="この作品に対するアクセス権限がありません")
      return book
  ```
* **受け入れ基準**: User A が User B の `book_id` を指定してリクエストした際に 403 Forbidden が返ること。

---

### Step 10: リポジトリ層のマルチテナント化 (`src/infrastructure/repositories/`)
* **目標**: `BookRepository` や `EpisodeRepository` のデータ取得ロジックにテナント境界を適用。
* **実装内容**:
  - `find_by_id(book_id, user_id)`
  - `list_books(user_id, limit, offset)`
  - 全てのSELECT・UPDATE・DELETE文に `WHERE user_id = :user_id` 条件を必須化。
* **受け入れ基準**: ログインユーザーに紐づく作品のみが一覧に返り、他ユーザーの作品が混入しないこと。

---

### Step 11: フロントエンド認証コンテキスト実装 (`frontend/src/context/AuthContext.tsx`)
* **目標**: React側でのトークン保持、自動リフレッシュ、APIリクエストへのBearerトークン自動付与。
* **実装内容**:
  - `AuthContext`: `user`, `token`, `login()`, `logout()`, `register()` を提供。
  - Fetch / Axios インターセプターにより、全APIリクエストに `Authorization: Bearer <token>` を付加。
  - 401受信時の自動ログアウトまたはリフレッシュ処理。
* **受け入れ基準**: ログイン後にページをリロードしてもセッションが維持されること。

---

### Step 12: マルチテナント統合テスト (`tests/integration/test_multitenancy_isolation.py`)
* **目標**: 複数テナント間でのデータ隔離性を自動テストで実証する。
* **実装内容**:
  - テスト用ユーザー2名（Alice, Bob）を生成。
  - Aliceのトークンで作品「Alice Story」を作成。
  - Bobのトークンで「Alice Story」の編集・取得・削除を試み、すべて 403/404 で遮断されることをアサート。
  - Bobの作品一覧に「Alice Story」が表示されないことを確認。
* **受け入れ基準**: `pytest tests/integration/test_multitenancy_isolation.py` が PASS すること。
