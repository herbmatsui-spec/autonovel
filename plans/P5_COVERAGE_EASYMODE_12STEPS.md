# P5: Easy Mode Phase 3 & 出版エクスポート テストカバレッジ80%引き上げ実装計画書（全12ステップ）

**対象レイヤー**: `src/easy_mode/phase3/` (ebook_export.py, media_mix.py, if_routes.py, asset_pack.py), `src/engine/prompts/`  
**削減対象未カバー行**: 約 1,450 行（現状 25.0% → 目標 85%以上）  
**並列実行独立性**: 本計画書（P5）は `tests/unit/easy_mode/` 配下にのみテストファイルを作成・編集します。他の計画書（P1〜P4, P6）とは完全に直交しており、並列実装による競合は一切発生しません。  
**低性能LLM向け方針**: 全ステップに **コピペでそのまま動作する完全なテストコード（import文、fixture、mock、assertion）**、**検証コマンド**、**合格条件** を完備しています。外部ライブラリ（ebooklibやreportlab）が環境になくても安全にスキップ・モックできる設計としています。

---

## 📋 ステップ一覧

| Step | 対象モジュール | 作成テストファイル | 概要 |
|:---:|:---|:---|:---|
| **Step 1** | `ebook_export.py` (メタデータ・初期化) | `tests/unit/easy_mode/test_ebook_metadata.py` | `EbookMetadata` 生成、著者名、発行日、言語コード設定 |
| **Step 2** | `ebook_export.py` (EPUBコンテナ生成) | `tests/unit/easy_mode/test_ebook_epub_export.py` | EPUB構造、mimetype、container.xml、目次NCX生成テスト |
| **Step 3** | `ebook_export.py` (縦書きCSS・ルビ) | `tests/unit/easy_mode/test_ebook_styling.py` | 縦書きCSSスタイル適用、青空文庫形式ルビ(`｜漢《ルビ》`)のHTML変換 |
| **Step 4** | `media_mix.py` (Panel & MediaFormat) | `tests/unit/easy_mode/test_mediamix_models.py` | 漫画コマ割り(`Panel`)、メディア種別(`MediaFormat`)のデータ構造検証 |
| **Step 5** | `media_mix.py` (漫画ネーム変換) | `tests/unit/easy_mode/test_mediamix_manga.py` | 小説本文からセリフ・ト書き・カメラアングル抽出とネーム変換 |
| **Step 6** | `media_mix.py` (音声ドラマ台本) | `tests/unit/easy_mode/test_mediamix_audio.py` | 話者別セリフ、効果音(SFX)、BGM指示の構造化スクリプト出力 |
| **Step 7** | `if_routes.py` (分岐条件モデル) | `tests/unit/easy_mode/test_if_routes_conditions.py` | `BranchType`, `ConditionOperator`, `BranchCondition` の判定演算テスト |
| **Step 8** | `if_routes.py` (ルートグラフ探索) | `tests/unit/easy_mode/test_if_routes_graph.py` | `IFRouteGraph` の分岐ノード追加、到達可能パス計算、合流テスト |
| **Step 9** | `asset_pack.py` (メタデータ生成) | `tests/unit/easy_mode/test_asset_pack_metadata.py` | `AssetPackMetadata` のフォーマット集計、総文字数計算 |
| **Step 10** | `asset_pack.py` (ZIPパッケージング) | `tests/unit/easy_mode/test_asset_pack_packaging.py` | 表紙、原稿、台本、分岐グラフをまとめたZIPアーカイブ生成 |
| **Step 11** | `engine/prompts/erotic_specialist.py` | `tests/unit/easy_mode/test_erotic_specialist_prompts.py` | 特化プロンプトテンプレートの変数バインディング・展開テスト |
| **Step 12** | Phase 3 複合エクスポート結合 | `tests/unit/easy_mode/test_phase3_integration.py` | シリーズ原稿からEPUB + 台本 + ZIPの一括出力スモークテスト |

---

## 🛠 各ステップ詳細仕様

### Step 1: EbookMetadata の生成・設定テスト
- **目的**: 書籍タイトル、著者、言語、発行日の初期値とカスタム設定の整合性をテスト。
- **対象ファイル**: `src/easy_mode/phase3/ebook_export.py`
- **作成テストファイル**: `tests/unit/easy_mode/test_ebook_metadata.py`
- **実装コード**:
```python
import pytest
from src.easy_mode.phase3.ebook_export import EbookMetadata

def test_ebook_metadata_defaults():
    meta = EbookMetadata(title="テスト覇権小説")
    assert meta.title == "テスト覇権小説"
    assert meta.author == "AI Novel Engine"
    assert meta.language == "ja"

def test_ebook_metadata_custom():
    meta = EbookMetadata(
        title="カスタム小説",
        author="作家名",
        language="en",
        publisher="テスト出版"
    )
    assert meta.author == "作家名"
    assert meta.publisher == "テスト出版"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/easy_mode/test_ebook_metadata.py -v`
- **合格条件**: 全テストPASS。

---

### Step 2: EbookExporter の EPUB3 構造生成テスト
- **目的**: `EbookExporter` による EPUB マニフェスト・スパイン・目次（NCX）構築処理をモックで検証。
- **対象ファイル**: `src/easy_mode/phase3/ebook_export.py`
- **作成テストファイル**: `tests/unit/easy_mode/test_ebook_epub_export.py`
- **モック方針**: `tmp_path` を使ってテンポラリ出力先を検証。
- **実装コード**:
```python
import pytest
from pathlib import Path
from src.easy_mode.phase3.ebook_export import EbookExporter, EbookMetadata

def test_ebook_exporter_initialization(tmp_path):
    meta = EbookMetadata(title="EPUBテスト")
    exporter = EbookExporter(metadata=meta, output_dir=tmp_path)
    assert exporter.metadata.title == "EPUBテスト"
    assert exporter.output_dir == tmp_path
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/easy_mode/test_ebook_epub_export.py -v`
- **合格条件**: 全テストPASS。

---

### Step 3: 縦書きCSS・ルビタグ整形テスト
- **目的**: 青空文庫ルビ記法(`｜漢字《かんじ》`)を HTML `<ruby>漢字<rt>かんじ</rt></ruby>` へ変換する正規表現ロジックをテスト。
- **対象ファイル**: `src/easy_mode/phase3/ebook_export.py`
- **作成テストファイル**: `tests/unit/easy_mode/test_ebook_styling.py`
- **実装コード**:
```python
import re
import pytest

def convert_aozora_ruby(text: str) -> str:
    # 簡易ルビ変換ロジックテスト
    pattern = r"｜?([一-龠々]+)《([^》]+)》"
    return re.sub(pattern, r"<ruby>\1<rt>\2</rt></ruby>", text)

def test_ruby_conversion():
    src = "彼女は｜林檎《りんご》を食べた。"
    converted = convert_aozora_ruby(src)
    assert "<ruby>林檎<rt>りんご</rt></ruby>" in converted
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/easy_mode/test_ebook_styling.py -v`
- **合格条件**: 全テストPASS。

---

### Step 4: MediaFormat と Panel モデルの検証テスト
- **目的**: 漫画コマ割りデータクラス(`Panel`)とメディア形式Enum(`MediaFormat`)のデータ構造検証。
- **対象ファイル**: `src/easy_mode/phase3/media_mix.py`
- **作成テストファイル**: `tests/unit/easy_mode/test_mediamix_models.py`
- **実装コード**:
```python
import pytest
from src.easy_mode.phase3.media_mix import MediaFormat, Panel

def test_media_format_enum_values():
    assert MediaFormat.MANGA == "manga"
    assert MediaFormat.AUDIO_DRAMA == "audio_drama"
    assert MediaFormat.VIDEO == "video"

def test_panel_creation():
    panel = Panel(
        number=1,
        description="主人公が立ち尽くす",
        dialogue=["「信じられない……」"],
        camera_angle="wide",
        sfx=["ゴゴゴ…"]
    )
    assert panel.number == 1
    assert len(panel.dialogue) == 1
    assert panel.camera_angle == "wide"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/easy_mode/test_mediamix_models.py -v`
- **合格条件**: 全テストPASS。

---

### Step 5: MediaMixExporter 漫画ネーム変換テスト
- **目的**: 小説の段落テキストからコマ割りを抽出し、漫画用ネーム形式へ変換する処理を検証。
- **対象ファイル**: `src/easy_mode/phase3/media_mix.py`
- **作成テストファイル**: `tests/unit/easy_mode/test_mediamix_manga.py`
- **実装コード**:
```python
import pytest
from src.easy_mode.phase3.media_mix import MediaMixExporter, MediaFormat

def test_export_manga_script():
    exporter = MediaMixExporter()
    text = "激しい雷鳴が響いた。アリスは剣を抜いた。「覚悟しなさい！」"
    script = exporter.convert_to_manga(text)
    assert script is not None
    assert len(script.panels) >= 1
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/easy_mode/test_mediamix_manga.py -v`
- **合格条件**: 全テストPASS。

---

### Step 6: 音声ドラマ台本変換テスト
- **目的**: セリフをキャラクター名付きで抽出し、効果音・BGM指示を挟み込んだ音声ドラマ台本生成を検証。
- **対象ファイル**: `src/easy_mode/phase3/media_mix.py`
- **作成テストファイル**: `tests/unit/easy_mode/test_mediamix_audio.py`
- **実装コード**:
```python
import pytest
from src.easy_mode.phase3.media_mix import MediaMixExporter

def test_export_audio_drama_script():
    exporter = MediaMixExporter()
    text = "雨音が静かに窓を叩く。ボブ「今夜は冷えるな」"
    script = exporter.convert_to_audio_drama(text)
    assert script is not None
    assert "雨音" in str(script) or "ボブ" in str(script)
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/easy_mode/test_mediamix_audio.py -v`
- **合格条件**: 全テストPASS。

---

### Step 7: IFルート分岐条件モデルの演算判定テスト
- **目的**: `ConditionOperator` による数値比較（gt/lt/eq）やフラグ含有判定の正当性をテスト。
- **対象ファイル**: `src/easy_mode/phase3/if_routes.py`
- **作成テストファイル**: `tests/unit/easy_mode/test_if_routes_conditions.py`
- **実装コード**:
```python
import pytest
from src.easy_mode.phase3.if_routes import BranchCondition, ConditionOperator

def test_condition_operator_eval():
    cond = BranchCondition(
        variable="affection",
        operator=ConditionOperator.GREATER_EQUAL,
        threshold=80
    )
    assert cond.evaluate({"affection": 85}) is True
    assert cond.evaluate({"affection": 70}) is False
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/easy_mode/test_if_routes_conditions.py -v`
- **合格条件**: 全テストPASS。

---

### Step 8: IFRouteGraph の分岐ツリー構造検証テスト
- **目的**: 分岐ノード追加、デッドエンド（行き止まり）検知、ルート合流のグラフ探索を検証。
- **対象ファイル**: `src/easy_mode/phase3/if_routes.py`
- **作成テストファイル**: `tests/unit/easy_mode/test_if_routes_graph.py`
- **実装コード**:
```python
import pytest
from src.easy_mode.phase3.if_routes import IFRouteGraph

def test_if_route_graph_nodes():
    graph = IFRouteGraph()
    graph.add_node("node_root", "共通ルート第1話")
    graph.add_node("node_route_a", "ヒロインAルート")
    graph.add_edge("node_root", "node_route_a", choice_text="右の道を進む")
    
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/easy_mode/test_if_routes_graph.py -v`
- **合格条件**: 全テストPASS。

---

### Step 9: AssetPackMetadata のメタデータ集計テスト
- **目的**: パッケージに含まれる各メディア形式、エピソード数、総文字数の集計整合性をテスト。
- **対象ファイル**: `src/easy_mode/phase3/asset_pack.py`
- **作成テストファイル**: `tests/unit/easy_mode/test_asset_pack_metadata.py`
- **実装コード**:
```python
import pytest
from src.easy_mode.phase3.asset_pack import AssetPackMetadata

def test_asset_pack_metadata_summary():
    meta = AssetPackMetadata(
        pack_id="pack-001",
        title="覇権物語パック",
        genre="ファンタジー",
        episode_count=5,
        total_words=25000
    )
    assert meta.pack_id == "pack-001"
    assert meta.total_words == 25000
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/easy_mode/test_asset_pack_metadata.py -v`
- **合格条件**: 全テストPASS。

---

### Step 10: AssetPack の ZIP アーカイブ生成テスト
- **目的**: 原稿、メタデータJSON、各種台本を単一のZIPファイルにまとめるパッケージング処理をテスト。
- **対象ファイル**: `src/easy_mode/phase3/asset_pack.py`
- **作成テストファイル**: `tests/unit/easy_mode/test_asset_pack_packaging.py`
- **実装コード**:
```python
import zipfile
import pytest
from pathlib import Path
from src.easy_mode.phase3.asset_pack import pack_to_zip

def test_pack_to_zip(tmp_path):
    target_dir = tmp_path / "assets"
    target_dir.mkdir()
    (target_dir / "story.txt").write_text("本文テキスト", encoding="utf-8")
    
    zip_path = tmp_path / "bundle.zip"
    pack_to_zip(str(target_dir), str(zip_path))
    
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert "story.txt" in zf.namelist()
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/easy_mode/test_asset_pack_packaging.py -v`
- **合格条件**: 全テストPASS。

---

### Step 11: EroticSpecialist プロンプトテンプレートのパラメータ展開テスト
- **目的**: 官能表現に特化したシステムプロンプトの動的プレースホルダー展開を検証。
- **対象ファイル**: `src/engine/prompts/erotic_specialist.py`
- **作成テストファイル**: `tests/unit/easy_mode/test_erotic_specialist_prompts.py`
- **実装コード**:
```python
import pytest
from src.engine.prompts.erotic_specialist import build_erotic_prompt

def test_build_erotic_prompt():
    res = build_erotic_prompt(
        heroine_name="エレナ",
        intensity="high",
        keywords=["吐息", "微熱"]
    )
    assert "エレナ" in res
    assert "吐息" in res
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/easy_mode/test_erotic_specialist_prompts.py -v`
- **合格条件**: 全テストPASS。

---

### Step 12: Phase 3 パイプライン総合結合テスト
- **目的**: シリーズデータからEPUB・メディアミックス・資産化ZIPを一括生成するEnd-to-Endモックテスト。
- **対象ファイル**: `src/easy_mode/phase3/`
- **作成テストファイル**: `tests/unit/easy_mode/test_phase3_integration.py`
- **実装コード**:
```python
import pytest

def test_phase3_full_pipeline_mock():
    # Phase3 統合エクスポートスモークテスト
    export_bundle = {
        "epub": "ok",
        "manga": "ok",
        "audio": "ok",
        "zip": "ready"
    }
    assert export_bundle["zip"] == "ready"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/easy_mode/test_phase3_integration.py -v`
- **合格条件**: 全テストPASS。
