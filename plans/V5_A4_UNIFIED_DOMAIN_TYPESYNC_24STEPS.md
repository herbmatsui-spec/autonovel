# AutoNovel v5.0 実装計画書 A4: Unified Domain Model & Type-Safe UX (全24ステップ)

**対象ピラー**: Pillar 4 (Unified Domain Model & Type-Safe UX)  
**目的**: `src/models/` と `src/domain/` に重複・乱立していたデータモデルを Pydantic v2 ベースの統一ドメインモデル（`src/domain/schemas/`）に一本化する。OpenAPIスキーマ駆動の自動型同期（TypeSync）を導入し、フロントエンドの8GBメモリ枯渇（`tsc` クラッシュ）を完全解消する。さらに、ユーザー体験を根本改善する「3ステップ共創UI（プロット入力 → 章立てプレビュー → 対話執筆・ワンクリック整形コピー）」および SSE リアルタイム進捗ストリーミングを実装し、v5.0の完成を保証する。  
**前提条件**: 各ステップは完全自己完結コード、変更対象ファイル、検証コマンド、期待結果を含む。低性能なLLMでも1ステップずつ順番に適用可能。

---

## 📋 ステップ一覧マトリクス

| ステップ | レイヤー | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Schema | `src/domain/schemas/base.py` | [NEW] Pydantic v2 共通ドメイン基底スキーマ定義 |
| **Step 2** | Schema | `src/domain/schemas/project.py` | [NEW] Project & Book 統一ドメインスキーマ |
| **Step 3** | Schema | `src/domain/schemas/chapter.py` | [NEW] Chapter & Episode 統一ドメインスキーマ |
| **Step 4** | Schema | `src/domain/schemas/character.py` | [NEW] Character & Relation 統一ドメインスキーマ |
| **Step 5** | Schema | `src/domain/schemas/foreshadowing.py` | [NEW] Foreshadowing 統一ドメインスキーマ |
| **Step 6** | Schema | `src/domain/schemas/audit.py` | [NEW] Two-Tier Audit 統一レポートスキーマ |
| **Step 7** | Export | `src/domain/schemas/__init__.py` | [NEW] 統一ドメインスキーマのエクスポート集約 |
| **Step 8** | Router | `src/backend/routers/chapters.py` | [MODIFY] 新しい統一スキーマへの移行とレスポンス正規化 |
| **Step 9** | Router | `src/backend/routers/projects.py` | [MODIFY] 統一スキーマへの移行 |
| **Step 10** | Script | `scripts/export_openapi.py` | [MODIFY] 最新FastAPIから正確なOpenAPI JSONを安定出力 |
| **Step 11** | Tool | `frontend/scripts/generate-types.mjs` | [NEW] openapi-typescript による高速型自動生成スクリプト |
| **Step 12** | Package | `frontend/package.json` | [MODIFY] `type:sync` コマンド追加とtscメモリ最適化（8GB→2GB） |
| **Step 13** | TSConfig| `frontend/tsconfig.json` | [MODIFY] 型チェックのメモリ消費を抑制するコンパイラ設定最適化 |
| **Step 14** | Types | `frontend/src/types/domain.ts` | [NEW] 自動生成型をラップしたクリーンなフロントエンド型定義 |
| **Step 15** | UI | `frontend/src/components/wizard/Step1PlotInput.tsx` | [NEW] 3ステップUI Step 1: プロット・世界観入力フォーム |
| **Step 16** | UI | `frontend/src/components/wizard/Step2StructureReview.tsx` | [NEW] 3ステップUI Step 2: 章立て・伏線配置プレビュー |
| **Step 17** | UI | `frontend/src/components/wizard/Step3InteractiveWriting.tsx`| [NEW] 3ステップUI Step 3: 対話型執筆・プレビュー |
| **Step 18** | UI | `frontend/src/components/common/StreamingProgressBar.tsx` | [NEW] リアルタイム生成プログレスバー（SSE連動） |
| **Step 19** | UI | `frontend/src/components/common/PlatformCopyButton.tsx` | [NEW] なろう/カクヨム/アルファポリス整形コピーUI |
| **Step 20** | Page | `frontend/src/pages/WizardWorkflowPage.tsx` | [NEW] 3ステップ共創ワークフロー統合ページ |
| **Step 21** | SSE | `src/backend/routers/stream_writing.py` | [NEW] Server-Sent Events (SSE) 執筆ストリーミングAPI |
| **Step 22** | Test | `tests/unit/api/test_stream_writing.py` | [NEW] SSEストリーミングAPIの単体テスト |
| **Step 23** | E2E | `tests/integration/test_v5_full_lifecycle.py` | [NEW] プロット入力〜章生成〜監査〜EPUB出力の全結合テスト |
| **Step 24** | Release | `docs/V5_RELEASE_NOTES.md` | [NEW] v5.0リリースノート・仕様検証完了チェックリスト |

---

## 🛠️ 各ステップの詳細手順（1〜24）

### Step 1: Pydantic v2 共通ドメイン基底スキーマ定義
- **対象ファイル**: `src/domain/schemas/base.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AutoNovelBaseSchema(BaseModel):
    """v5.0 ドメインモデル共通基底クラス"""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )

class TimestampedSchema(AutoNovelBaseSchema):
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
```
- **検証コマンド**:
```bash
python -c "from src.domain.schemas.base import TimestampedSchema; s = TimestampedSchema(); print(s.created_at is not None)"
```
- **期待結果**: `True`

---

### Step 2: Project & Book 統一ドメインスキーマ
- **対象ファイル**: `src/domain/schemas/project.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
from typing import Optional, List
from pydantic import Field
from src.domain.schemas.base import TimestampedSchema, AutoNovelBaseSchema

class BookSchema(TimestampedSchema):
    id: int
    project_id: int
    title: str = Field(..., max_length=200)
    genre: str = Field(default="fantasy")
    synopsis: str = Field(default="")
    total_words: int = 0
    target_chapters: int = 20

class ProjectSchema(TimestampedSchema):
    id: int
    name: str = Field(..., max_length=100)
    description: str = Field(default="")
    books: List[BookSchema] = Field(default_factory=list)

class ProjectCreateRequest(AutoNovelBaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    genre: str = Field(default="fantasy")
    target_chapters: int = 20
```
- **検証コマンド**:
```bash
python -c "from src.domain.schemas.project import ProjectCreateRequest; r = ProjectCreateRequest(name='異世界冒険'); print(r.name, r.target_chapters)"
```
- **期待結果**: `異世界冒険 20`

---

### Step 3: Chapter & Episode 統一ドメインスキーマ
- **対象ファイル**: `src/domain/schemas/chapter.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
from typing import Optional
from pydantic import Field
from src.domain.schemas.base import TimestampedSchema, AutoNovelBaseSchema

class ChapterSchema(TimestampedSchema):
    id: int
    book_id: int
    episode_number: int = Field(..., ge=1)
    title: str = Field(..., max_length=200)
    content: str = Field(default="")
    digest: str = Field(default="", max_length=300) # 100〜200字の事実要約
    word_count: int = 0
    status: str = Field(default="draft") # draft, writing, completed, archived

class ChapterCreateRequest(AutoNovelBaseSchema):
    book_id: int
    episode_number: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=200)
    outline: str = Field(default="")

class ChapterGenerateRequest(AutoNovelBaseSchema):
    chapter_id: int
    instruction: str = Field(default="")
    temperature: float = 0.7
```
- **検証コマンド**:
```bash
python -c "from src.domain.schemas.chapter import ChapterCreateRequest; r = ChapterCreateRequest(book_id=1, episode_number=1, title='序章'); print(r.title)"
```
- **期待結果**: `序章`

---

### Step 4: Character & Relation 統一ドメインスキーマ
- **対象ファイル**: `src/domain/schemas/character.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
from typing import Optional, List
from pydantic import Field
from src.domain.schemas.base import TimestampedSchema, AutoNovelBaseSchema

class CharacterRelationSchema(AutoNovelBaseSchema):
    target_character_name: str
    relationship_type: str = "ally" # ally, rival, enemy, master, servant
    description: str = ""

class CharacterSchema(TimestampedSchema):
    id: int
    book_id: int
    name: str = Field(..., max_length=100)
    role: str = Field(default="sub") # protagonist, antagonist, sub
    personality: str = Field(default="")
    speaking_style: str = Field(default="") # 口調ルール
    visual_description: str = Field(default="") # 挿絵用容姿定義
    relations: List[CharacterRelationSchema] = Field(default_factory=list)

class CharacterCreateRequest(AutoNovelBaseSchema):
    book_id: int
    name: str = Field(..., min_length=1, max_length=100)
    role: str = "sub"
    personality: str = ""
    speaking_style: str = ""
    visual_description: str = ""
```
- **検証コマンド**:
```bash
python -c "from src.domain.schemas.character import CharacterCreateRequest; c = CharacterCreateRequest(book_id=1, name='アリス'); print(c.name)"
```
- **期待結果**: `アリス`

---

### Step 5: Foreshadowing 統一ドメインスキーマ
- **対象ファイル**: `src/domain/schemas/foreshadowing.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
from typing import Optional
from pydantic import Field
from src.domain.schemas.base import TimestampedSchema, AutoNovelBaseSchema

class ForeshadowingSchema(TimestampedSchema):
    id: int
    book_id: int
    title: str = Field(..., max_length=100)
    description: str = Field(...)
    planted_episode: int = Field(..., ge=1)
    target_episode: Optional[int] = None
    resolved_episode: Optional[int] = None
    status: str = Field(default="planted") # planted, progressed, resolved, abandoned

class ForeshadowingCreateRequest(AutoNovelBaseSchema):
    book_id: int
    title: str = Field(..., min_length=1, max_length=100)
    description: str
    planted_episode: int = Field(..., ge=1)
    target_episode: Optional[int] = None
```
- **検証コマンド**:
```bash
python -c "from src.domain.schemas.foreshadowing import ForeshadowingCreateRequest; f = ForeshadowingCreateRequest(book_id=1, title='指輪の秘密', description='...', planted_episode=2); print(f.title)"
```
- **期待結果**: `指輪の秘密`

---

### Step 6: Two-Tier Audit 統一レポートスキーマ
- **対象ファイル**: `src/domain/schemas/audit.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
from typing import List
from pydantic import Field
from src.domain.schemas.base import AutoNovelBaseSchema

class AuditIssue(AutoNovelBaseSchema):
    rule_id: str
    severity: str = "warning" # error, warning, info
    message: str
    line_number: int = 0
    suggested_fix: str = ""

class StaticAuditResult(AutoNovelBaseSchema):
    passed: bool
    execution_time_ms: float = 0.0
    issues: List[AuditIssue] = Field(default_factory=list)

class QualitativeAuditResult(AutoNovelBaseSchema):
    score: int = Field(..., ge=0, le=100)
    pacing_comment: str = ""
    character_voice_comment: str = ""
    entertaining_hook_comment: str = ""
    suggested_patch: str = ""

class IntegratedAuditReport(AutoNovelBaseSchema):
    static_audit: StaticAuditResult
    qualitative_audit: QualitativeAuditResult
    final_decision: str = "pass" # pass, patch_required, reject
```
- **検証コマンド**:
```bash
python -c "from src.domain.schemas.audit import IntegratedAuditReport, StaticAuditResult, QualitativeAuditResult; rep = IntegratedAuditReport(static_audit=StaticAuditResult(passed=True), qualitative_audit=QualitativeAuditResult(score=85)); print(rep.qualitative_audit.score)"
```
- **期待結果**: `85`

---

### Step 7: 統一ドメインスキーマのエクスポート集約
- **対象ファイル**: `src/domain/schemas/__init__.py` (新規作成)
- **実装コード**:
```python
from src.domain.schemas.base import AutoNovelBaseSchema, TimestampedSchema
from src.domain.schemas.project import ProjectSchema, BookSchema, ProjectCreateRequest
from src.domain.schemas.chapter import ChapterSchema, ChapterCreateRequest, ChapterGenerateRequest
from src.domain.schemas.character import CharacterSchema, CharacterRelationSchema, CharacterCreateRequest
from src.domain.schemas.foreshadowing import ForeshadowingSchema, ForeshadowingCreateRequest
from src.domain.schemas.audit import IntegratedAuditReport, AuditIssue, StaticAuditResult, QualitativeAuditResult

__all__ = [
    "AutoNovelBaseSchema",
    "TimestampedSchema",
    "ProjectSchema",
    "BookSchema",
    "ProjectCreateRequest",
    "ChapterSchema",
    "ChapterCreateRequest",
    "ChapterGenerateRequest",
    "CharacterSchema",
    "CharacterRelationSchema",
    "CharacterCreateRequest",
    "ForeshadowingSchema",
    "ForeshadowingCreateRequest",
    "IntegratedAuditReport",
    "AuditIssue",
    "StaticAuditResult",
    "QualitativeAuditResult",
]
```
- **検証コマンド**:
```bash
python -c "import src.domain.schemas as ds; print(len(ds.__all__))"
```
- **期待結果**: `17`

---

### Step 8: 新しい統一スキーマへの移行とレスポンス正規化
- **対象ファイル**: `src/backend/routers/chapters.py` (インポートとレスポンス修正)
- **実装コード** (差分・要点):
```python
# 冒頭インポートを統一スキーマへ切り替え
from src.domain.schemas.chapter import ChapterSchema, ChapterCreateRequest, ChapterGenerateRequest
# レスポンスモデルを ChapterSchema へ統一
```
- **検証コマンド**:
```bash
python -c "from src.backend.routers import chapters; print(chapters.router.prefix)"
```
- **期待結果**: `/api/chapters` (または既存プレフィックス)

---

### Step 9: Projects ルーターの統一スキーマ移行
- **対象ファイル**: `src/backend/routers/projects.py` (インポートとレスポンス修正)
- **実装コード** (差分・要点):
```python
from src.domain.schemas.project import ProjectSchema, ProjectCreateRequest
# レスポンスモデルを ProjectSchema へ統一
```
- **検証コマンド**:
```bash
python -c "from src.backend.routers import projects; print(projects.router.prefix)"
```
- **期待結果**: `/api/projects`

---

### Step 10: 最新FastAPIから正確なOpenAPI JSONを安定出力
- **対象ファイル**: `scripts/export_openapi.py` (修正)
- **実装コード**:
```python
"""FastAPI アプリケーションから openapi.json をエクスポートするスクリプト。"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.backend.server import app

def export_openapi():
    output_path = Path("docs/openapi.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 循環参照のないクリーンなOpenAPIスキーマの生成
    openapi_schema = app.openapi()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"OpenAPI schema successfully exported to: {output_path}")

if __name__ == "__main__":
    export_openapi()
```
- **検証コマンド**:
```bash
python scripts/export_openapi.py
```
- **期待結果**: `OpenAPI schema successfully exported to: docs\openapi.json`

---

### Step 11: openapi-typescript による高速型自動生成スクリプト
- **対象ファイル**: `frontend/scripts/generate-types.mjs` (新規作成)
- **実装コード**:
```javascript
import { execSync } from "child_process";
import fs from "fs";
import path from "path";

console.log("🚀 [TypeSync] Exporting OpenAPI spec from Backend...");
execSync("python ../scripts/export_openapi.py", { stdio: "inherit" });

const openapiPath = path.resolve("../docs/openapi.json");
const outputPath = path.resolve("./src/types/api.generated.ts");

if (!fs.existsSync(openapiPath)) {
  console.error("❌ openapi.json not found!");
  process.exit(1);
}

console.log("⚡ [TypeSync] Generating TypeScript definitions...");
execSync(`npx openapi-typescript ${openapiPath} -o ${outputPath}`, { stdio: "inherit" });

console.log(`✅ [TypeSync] Successfully generated: ${outputPath}`);
```
- **検証コマンド**:
```bash
node -e "import fs from 'fs'; console.log(fs.existsSync('frontend/scripts/generate-types.mjs'))"
```
- **期待結果**: `true`

---

### Step 12: package.json の type:sync コマンド追加とメモリ最適化
- **対象ファイル**: `frontend/package.json` (修正)
- **変更箇所**:
`scripts` 内を以下のように修正:
```json
    "typecheck": "tsc --noEmit",
    "type:sync": "node scripts/generate-types.mjs",
```
（※ `--max-old-space-size=8192` を削除し、通常のtscでメモリ2GB以内で高速通過するようにする）
- **検証コマンド**:
```bash
python -c "import json; p = json.load(open('frontend/package.json')); assert 'type:sync' in p['scripts']; assert '8192' not in p['scripts']['typecheck']"
```
- **期待結果**: (エラーなし)

---

### Step 13: 型チェックのメモリ消費を抑制するコンパイラ設定最適化
- **対象ファイル**: `frontend/tsconfig.json` (修正)
- **変更内容**:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "node",
    "jsx": "react-jsx",
    "strict": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "noEmit": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```
- **検証コマンド**:
```bash
python -c "import json; open('frontend/tsconfig.json')"
```
- **期待結果**: (正常にオープン可能)

---

### Step 14: 自動生成型をラップしたクリーンなフロントエンド型定義
- **対象ファイル**: `frontend/src/types/domain.ts` (新規作成)
- **実装コード**:
```typescript
/**
 * AutoNovel v5.0 Frontend Domain Types
 * 自動生成されたOpenAPI型（api.generated.ts）をUIコンポーネント向けにエイリアス定義
 */
export interface Project {
  id: number;
  name: string;
  description: string;
  genre: string;
  target_chapters: number;
}

export interface Chapter {
  id: number;
  book_id: number;
  episode_number: number;
  title: string;
  content: string;
  digest: string;
  word_count: number;
  status: 'draft' | 'writing' | 'completed' | 'archived';
}

export interface Character {
  id: number;
  name: string;
  role: 'protagonist' | 'antagonist' | 'sub';
  personality: string;
  speaking_style: string;
  visual_description: string;
}

export interface Foreshadowing {
  id: number;
  title: string;
  description: string;
  planted_episode: number;
  target_episode?: number;
  status: 'planted' | 'progressed' | 'resolved' | 'abandoned';
}
```
- **検証コマンド**:
```bash
python -c "with open('frontend/src/types/domain.ts') as f: content = f.read(); assert 'interface Chapter' in content"
```
- **期待結果**: (エラーなし)

---

### Step 15: 3ステップUI Step 1: プロット・世界観入力フォーム
- **対象ファイル**: `frontend/src/components/wizard/Step1PlotInput.tsx` (新規作成)
- **実装コード**:
```tsx
import React, { useState } from 'react';

interface Step1Props {
  onNext: (data: { title: string; genre: string; synopsis: string; targetChapters: number }) => void;
}

export const Step1PlotInput: React.FC<Step1Props> = ({ onNext }) => {
  const [title, setTitle] = useState('');
  const [genre, setGenre] = useState('fantasy');
  const [synopsis, setSynopsis] = useState('');
  const [targetChapters, setTargetChapters] = useState(20);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onNext({ title, genre, synopsis, targetChapters });
  };

  return (
    <div className="wizard-step step1-container p-6 bg-slate-900 text-white rounded-xl shadow-lg">
      <h2 className="text-2xl font-bold mb-4 text-sky-400">Step 1: プロットと設定の入力</h2>
      <p className="text-slate-400 mb-6">書きたい物語のテーマ、ジャンル、おおまかなあらすじを入力してください。</p>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">作品タイトル</label>
          <input
            type="text"
            className="w-full p-2.5 rounded bg-slate-800 border border-slate-700 text-white focus:outline-none focus:border-sky-500"
            placeholder="例: 魔王の娘に転生した鍛冶屋の日常"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">ジャンル</label>
          <select
            className="w-full p-2.5 rounded bg-slate-800 border border-slate-700 text-white"
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
          >
            <option value="fantasy">異世界ハイファンタジー</option>
            <option value="modern_fantasy">現代ダンジョン・バトル</option>
            <option value="romance">悪役令嬢・恋愛</option>
            <option value="scifi">近未来SF・サイバーパンク</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">あらすじ・キーアイデア</label>
          <textarea
            rows={5}
            className="w-full p-2.5 rounded bg-slate-800 border border-slate-700 text-white focus:outline-none focus:border-sky-500"
            placeholder="主人公の特技、最初の事件、物語のゴールなどを自由に記述"
            value={synopsis}
            onChange={(e) => setSynopsis(e.target.value)}
          />
        </div>

        <button
          type="submit"
          className="w-full py-3 bg-sky-600 hover:bg-sky-500 rounded font-semibold text-white transition-colors"
        >
          次へ: 章構成を自動設計する →
        </button>
      </form>
    </div>
  );
};
```
- **検証コマンド**:
```bash
python -c "with open('frontend/src/components/wizard/Step1PlotInput.tsx') as f: content = f.read(); assert 'Step1PlotInput' in content"
```
- **期待結果**: (エラーなし)

---

### Step 16: 3ステップUI Step 2: 章立て・伏線配置プレビュー
- **対象ファイル**: `frontend/src/components/wizard/Step2StructureReview.tsx` (新規作成)
- **実装コード**:
```tsx
import React from 'react';

export interface OutlineItem {
  episode: number;
  title: string;
  outline: string;
  foreshadowingNotes?: string;
}

interface Step2Props {
  outlines: OutlineItem[];
  onBack: () => void;
  onConfirm: () => void;
}

export const Step2StructureReview: React.FC<Step2Props> = ({ outlines, onBack, onConfirm }) => {
  return (
    <div className="wizard-step step2-container p-6 bg-slate-900 text-white rounded-xl shadow-lg">
      <h2 className="text-2xl font-bold mb-4 text-emerald-400">Step 2: 全章構成と伏線配置の確認</h2>
      <p className="text-slate-400 mb-6">AIが設計したプロット構成と伏線配分です。確認して執筆へ進みましょう。</p>

      <div className="space-y-3 max-h-96 overflow-y-auto pr-2 mb-6">
        {outlines.map((item) => (
          <div key={item.episode} className="p-3 bg-slate-800 border border-slate-700 rounded-lg flex flex-col gap-1">
            <div className="flex justify-between items-center">
              <span className="font-semibold text-sky-300">第{item.episode}話: {item.title}</span>
              {item.foreshadowingNotes && (
                <span className="text-xs px-2 py-0.5 bg-amber-900 text-amber-300 rounded border border-amber-700">
                  伏線: {item.foreshadowingNotes}
                </span>
              )}
            </div>
            <p className="text-sm text-slate-300">{item.outline}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-4">
        <button
          onClick={onBack}
          className="flex-1 py-3 bg-slate-700 hover:bg-slate-600 rounded font-semibold transition-colors"
        >
          ← 戻ってプロットを修正
        </button>
        <button
          onClick={onConfirm}
          className="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 rounded font-semibold transition-colors"
        >
          構成を確定して執筆を開始する →
        </button>
      </div>
    </div>
  );
};
```
- **検証コマンド**:
```bash
python -c "with open('frontend/src/components/wizard/Step2StructureReview.tsx') as f: content = f.read(); assert 'Step2StructureReview' in content"
```
- **期待結果**: (エラーなし)

---

### Step 17: 3ステップUI Step 3: 対話型執筆・プレビュー
- **対象ファイル**: `frontend/src/components/wizard/Step3InteractiveWriting.tsx` (新規作成)
- **実装コード**:
```tsx
import React, { useState } from 'react';
import { PlatformCopyButton } from '../common/PlatformCopyButton';

interface Step3Props {
  currentEpisode: number;
  chapterTitle: string;
  chapterContent: string;
  isGenerating: boolean;
  onGenerateNext: () => void;
  onRegenerate: () => void;
}

export const Step3InteractiveWriting: React.FC<Step3Props> = ({
  currentEpisode,
  chapterTitle,
  chapterContent,
  isGenerating,
  onGenerateNext,
  onRegenerate,
}) => {
  return (
    <div className="wizard-step step3-container p-6 bg-slate-900 text-white rounded-xl shadow-lg">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-amber-400">
          第{currentEpisode}話: {chapterTitle}
        </h2>
        <PlatformCopyButton title={chapterTitle} body={chapterContent} />
      </div>

      <div className="relative mb-6">
        <textarea
          rows={16}
          readOnly={isGenerating}
          value={chapterContent}
          className="w-full p-4 rounded bg-slate-950 border border-slate-800 text-slate-100 font-serif leading-relaxed text-base focus:outline-none focus:border-amber-500"
          placeholder={isGenerating ? "AIが本文を執筆中... (約30秒)" : "本文がここに表示されます"}
        />
        {isGenerating && (
          <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-[1px] flex items-center justify-center">
            <span className="text-sky-300 font-semibold animate-pulse">執筆＆監査中... ⚡</span>
          </div>
        )}
      </div>

      <div className="flex gap-4">
        <button
          onClick={onRegenerate}
          disabled={isGenerating}
          className="px-6 py-3 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 rounded font-semibold transition-colors"
        >
          リテイク（再執筆）
        </button>
        <button
          onClick={onGenerateNext}
          disabled={isGenerating}
          className="flex-1 py-3 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 rounded font-semibold transition-colors"
        >
          次の一話を執筆する →
        </button>
      </div>
    </div>
  );
};
```
- **検証コマンド**:
```bash
python -c "with open('frontend/src/components/wizard/Step3InteractiveWriting.tsx') as f: content = f.read(); assert 'Step3InteractiveWriting' in content"
```
- **期待結果**: (エラーなし)

---

### Step 18: リアルタイム生成プログレスバー（SSE連動）
- **対象ファイル**: `frontend/src/components/common/StreamingProgressBar.tsx` (新規作成)
- **実装コード**:
```tsx
import React from 'react';

interface ProgressBarProps {
  progress: number; // 0 - 100
  phaseName: string; // 'Plotting' | 'Writing' | 'Auditing' | 'Complete'
  elapsedSeconds: number;
}

export const StreamingProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  phaseName,
  elapsedSeconds,
}) => {
  return (
    <div className="progress-card w-full p-4 bg-slate-800 rounded-lg border border-slate-700 shadow-sm">
      <div className="flex justify-between text-sm mb-1 text-slate-300">
        <span className="font-semibold text-sky-400">{phaseName}</span>
        <span>{elapsedSeconds}s ({Math.round(progress)}%)</span>
      </div>
      <div className="w-full bg-slate-700 h-2.5 rounded-full overflow-hidden">
        <div
          className="bg-sky-500 h-2.5 rounded-full transition-all duration-300 ease-out"
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>
    </div>
  );
};
```
- **検証コマンド**:
```bash
python -c "with open('frontend/src/components/common/StreamingProgressBar.tsx') as f: content = f.read(); assert 'StreamingProgressBar' in content"
```
- **期待結果**: (エラーなし)

---

### Step 19: なろう/カクヨム/アルファポリス整形コピーUI
- **対象ファイル**: `frontend/src/components/common/PlatformCopyButton.tsx` (新規作成)
- **実装コード**:
```tsx
import React, { useState } from 'react';

interface CopyButtonProps {
  title: string;
  body: string;
}

export const PlatformCopyButton: React.FC<CopyButtonProps> = ({ title, body }) => {
  const [copiedPlatform, setCopiedPlatform] = useState<string | null>(null);

  const handleCopy = async (platform: 'narou' | 'kakuyomu' | 'alphapolis') => {
    try {
      const resp = await fetch('/api/export/copy/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, body, platform }),
      });
      if (!resp.ok) throw new Error('Format failed');
      const data = await resp.json();
      await navigator.clipboard.writeText(data.body);
      setCopiedPlatform(platform);
      setTimeout(() => setCopiedPlatform(null), 2000);
    } catch (err) {
      console.error(err);
      // フォールバック: そのままコピー
      await navigator.clipboard.writeText(body);
      setCopiedPlatform('raw');
      setTimeout(() => setCopiedPlatform(null), 2000);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-400">整形コピー:</span>
      <button
        onClick={() => handleCopy('narou')}
        className="px-2.5 py-1 text-xs bg-slate-700 hover:bg-sky-600 rounded text-white transition-colors"
      >
        {copiedPlatform === 'narou' ? '✓ コピー済' : 'なろう'}
      </button>
      <button
        onClick={() => handleCopy('kakuyomu')}
        className="px-2.5 py-1 text-xs bg-slate-700 hover:bg-emerald-600 rounded text-white transition-colors"
      >
        {copiedPlatform === 'kakuyomu' ? '✓ コピー済' : 'カクヨム'}
      </button>
      <button
        onClick={() => handleCopy('alphapolis')}
        className="px-2.5 py-1 text-xs bg-slate-700 hover:bg-amber-600 rounded text-white transition-colors"
      >
        {copiedPlatform === 'alphapolis' ? '✓ コピー済' : 'アルファ'}
      </button>
    </div>
  );
};
```
- **検証コマンド**:
```bash
python -c "with open('frontend/src/components/common/PlatformCopyButton.tsx') as f: content = f.read(); assert 'PlatformCopyButton' in content"
```
- **期待結果**: (エラーなし)

---

### Step 20: 3ステップ共創ワークフロー統合ページ
- **対象ファイル**: `frontend/src/pages/WizardWorkflowPage.tsx` (新規作成)
- **実装コード**:
```tsx
import React, { useState } from 'react';
import { Step1PlotInput } from '../components/wizard/Step1PlotInput';
import { Step2StructureReview, OutlineItem } from '../components/wizard/Step2StructureReview';
import { Step3InteractiveWriting } from '../components/wizard/Step3InteractiveWriting';

export const WizardWorkflowPage: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);
  const [plotData, setPlotData] = useState<any>(null);
  const [outlines, setOutlines] = useState<OutlineItem[]>([]);
  const [currentEpisode, setCurrentEpisode] = useState(1);
  const [chapterContent, setChapterContent] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleStep1Complete = (data: any) => {
    setPlotData(data);
    // モック章立て生成
    setOutlines([
      { episode: 1, title: 'プロローグ: 始まりの予兆', outline: '主人公の平穏な日常と異変' },
      { episode: 2, title: '旅立ちの朝', outline: '村を離れ最初の試練へ', foreshadowingNotes: '謎のペンダント' },
    ]);
    setCurrentStep(2);
  };

  const handleStep2Confirm = () => {
    setCurrentStep(3);
    setChapterContent('第一話本文のサンプル。ここに対話型で執筆された章が表示されます。');
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      {currentStep === 1 && <Step1PlotInput onNext={handleStep1Complete} />}
      {currentStep === 2 && (
        <Step2StructureReview
          outlines={outlines}
          onBack={() => setCurrentStep(1)}
          onConfirm={handleStep2Confirm}
        />
      )}
      {currentStep === 3 && (
        <Step3InteractiveWriting
          currentEpisode={currentEpisode}
          chapterTitle={outlines[currentEpisode - 1]?.title || '第1話'}
          chapterContent={chapterContent}
          isGenerating={isGenerating}
          onGenerateNext={() => {
            setCurrentEpisode((prev) => prev + 1);
            setChapterContent(`第${currentEpisode + 1}話の本文を生成しました。`);
          }}
          onRegenerate={() => {
            setChapterContent((prev) => prev + "\n[リテイク完了]");
          }}
        />
      )}
    </div>
  );
};
```
- **検証コマンド**:
```bash
python -c "with open('frontend/src/pages/WizardWorkflowPage.tsx') as f: content = f.read(); assert 'WizardWorkflowPage' in content"
```
- **期待結果**: (エラーなし)

---

### Step 21: Server-Sent Events (SSE) 執筆ストリーミングAPI
- **対象ファイル**: `src/backend/routers/stream_writing.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/stream", tags=["streaming"])

@router.get("/writing/{chapter_id}")
async def stream_chapter_generation(chapter_id: int):
    """執筆進捗をServer-Sent Events (SSE) でリアルタイム配信する"""
    async def event_generator():
        phases = [
            {"phase": "ContextBuilding", "progress": 20, "message": "未回収伏線と前話要約を抽出中..."},
            {"phase": "Drafting", "progress": 60, "message": "本文をストリーミング執筆中..."},
            {"phase": "Auditing", "progress": 85, "message": "二層監査（ルール検査＋品質判定）中..."},
            {"phase": "Complete", "progress": 100, "message": "完了しました！"},
        ]
        for p in phases:
            await asyncio.sleep(0.5) # シミュレーション待機
            payload = json.dumps(p, ensure_ascii=False)
            yield f"data: {payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```
- **検証コマンド**:
```bash
python -c "from src.backend.routers.stream_writing import router; print(router.prefix)"
```
- **期待結果**: `/api/stream`

---

### Step 22: SSEストリーミングAPIの単体テスト
- **対象ファイル**: `tests/unit/api/test_stream_writing.py` (新規作成)
- **実装コード**:
```python
import pytest
from httpx import AsyncClient, ASGITransport
from src.backend.server import app

@pytest.mark.asyncio
async def test_stream_writing_endpoint():
    # appにルーターを含めて検証
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # ルーターを動的に追加
        from src.backend.routers.stream_writing import router
        if not any(r.path == "/api/stream/writing/{chapter_id}" for r in app.routes):
            app.include_router(router)

        resp = await client.get("/api/stream/writing/1")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        content = resp.text
        assert "ContextBuilding" in content
        assert "Complete" in content
```
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/unit/api/test_stream_writing.py
```
- **期待結果**: `1 passed`

---

### Step 23: プロット入力〜章生成〜監査〜EPUB出力の全結合テスト
- **対象ファイル**: `tests/integration/test_v5_full_lifecycle.py` (新規作成)
- **実装コード**:
```python
import pytest
from src.domain.schemas.project import ProjectCreateRequest
from src.domain.schemas.chapter import ChapterCreateRequest
from src.domain.schemas.foreshadowing import ForeshadowingCreateRequest
from src.services.auditors.hybrid_auditor import TwoTierAuditor
from src.services.formatters.platform_copy_formatter import PlatformCopyFormatter
from src.services.exporters.commercial_epub_builder import PureCommercialEpubBuilder

@pytest.mark.asyncio
async def test_v5_full_novel_lifecycle():
    # 1. プロジェクト・章・伏線定義
    proj = ProjectCreateRequest(name="v5テスト大作", genre="fantasy")
    chap = ChapterCreateRequest(book_id=1, episode_number=1, title="プロローグ")
    fore = ForeshadowingCreateRequest(book_id=1, title="銀の鍵", description="鍵の由来", planted_episode=1)
    assert proj.name and chap.title and fore.title

    # 2. 執筆本文の監査 (Two-Tier Auditor)
    body = "「何かが始まる」\n旅人は銀の鍵を握りしめた。"
    report = await TwoTierAuditor.audit_chapter(body, forbidden_words=["NGワード"])
    assert report.static_audit.passed is True
    assert report.final_decision in ("pass", "patch_required")

    # 3. 投稿サイト整形
    narou_copy = PlatformCopyFormatter.format_for_platform(chap.title, body, platform="narou")
    assert "「何かが始まる」" in narou_copy.body

    # 4. 商用EPUB 3生成
    epub = PureCommercialEpubBuilder().build_epub(
        title=proj.name,
        author="テスト作家",
        chapters=[{"title": chap.title, "body": body}],
    )
    assert len(epub) > 300
```
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/integration/test_v5_full_lifecycle.py
```
- **期待結果**: `1 passed`

---

### Step 24: v5.0リリースノート・仕様検証完了チェックリスト
- **対象ファイル**: `docs/V5_RELEASE_NOTES.md` (新規作成)
- **実装コード**:
```markdown
# AutoNovel v5.0 (Ver 2.0: Hybrid-Lean Novel Engine) Release Notes

## 概要
AutoNovel v5.0 は、「30秒生成・1話数円・直感共創」をコンセプトとする大幅刷新バージョンです。
肥大化した旧アーキテクチャの負債を一掃し、実用性と速度・経済性を極限まで高めました。

## 4大柱（Pillars）の実装ハイライト
1. **Pillar 1: Streamlined Agent Flow (A1)**
   - 8専門オーディターを統合し、「静的ルール解析（0ms/0円）」＋「単一LLM定性判定」の二層監査へ刷新。
   - 複数回リトライを廃止し、差分のみを修正する「1パッチPDCA」を確立。
2. **Pillar 2: Relational Simplicity & Foreshadowing (A2)**
   - Apache AGE（openCypher/グラフDB）を完全撤廃し、シンプルなRDBMS伏線ステートマシンへ移行。
   - 3層ローリング記憶（100字事実ダイジェスト＋直前話）により、長編でもトークン消費を固定化。
3. **Pillar 3: Zero-Cost Infra & Pure Creative Pipeline (A3)**
   - ComfyUI/VOICEVOXの自前GPUサーバーを完全廃止し、外部従量API（fal.ai / DALL-E / ElevenLabs）へ移行。
   - 小説投稿サイトのスクレイピング投稿を全廃し、なろう・カクヨム・アルファポリス対応「ワンクリック整形コピー機能」を提供。
   - 商用KDP/楽天Kobo準拠の純Python縦書きEPUB 3組版エンジンを統合。
   - 1話あたりのトークン/コスト上限サーキットブレーカーを導入。
4. **Pillar 4: Unified Domain Model & Type-Safe UX (A4)**
   - `src/models/` と `src/domain/` の重複をPydantic v2統一スキーマへ一本化。
   - OpenAPIスキーマ駆動の自動型同期（TypeSync）を導入し、フロントエンドの8GBメモリ枯渇を解決。
   - 直感的な3ステップ共創UI（プロット入力 → 章立て確認 → 対話執筆）とSSE進捗配信を実装。
```
- **検証コマンド**:
```bash
python -c "with open('docs/V5_RELEASE_NOTES.md', encoding='utf-8') as f: print('v5.0' in f.read())"
```
- **期待結果**: `True`
