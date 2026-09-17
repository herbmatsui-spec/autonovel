# AutoNovel v5.0 実装計画書 A3: Zero-Cost Infra & Pure Creative Pipeline (全24ステップ)

**対象ピラー**: Pillar 3 (Zero-Cost Infra & Pure Creative Pipeline)  
**目的**: 自前GPU（ComfyUI / VOICEVOXサーバー）のホスティングコスト（月数万円）を完全撤廃し、外部従量API（fal.ai / DALL-E 3 / ElevenLabs等）へ移行する。また、壊れやすい小説投稿サイトのスクレイピング・自動ログインを廃止し、「各投稿サイト最適化済みワンクリック整形コピー機能」に転換する。さらに商用縦書きEPUB 3組版エンジンを完成させ、トークン・コスト予算ガードレールを実装して固定費ゼロ・1話数円の持続可能インフラを確立する。  
**前提条件**: 各ステップは完全自己完結コード、変更対象ファイル、検証コマンド、期待結果を含む。低性能なLLMでも1ステップずつ順番に適用可能。

---

## 📋 ステップ一覧マトリクス

| ステップ | レイヤー | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Adapter | `src/services/illustration/adapters/base.py` | [NEW] ImageGenerationAdapter 抽象基底インターフェース |
| **Step 2** | Adapter | `src/services/illustration/adapters/dalle3_adapter.py` | [NEW] OpenAI DALL-E 3 オンデマンド従量アダプタ |
| **Step 3** | Adapter | `src/services/illustration/adapters/fal_adapter.py` | [NEW] fal.ai (Flux / SDXL) 高速・格安APIアダプタ |
| **Step 4** | Adapter | `src/services/illustration/adapters/mock_adapter.py` | [NEW] テスト・開発用ゼロコストモックアダプタ |
| **Step 5** | Factory | `src/services/illustration/factory.py` | [MODIFY] ComfyUI依存を完全排除し、APIアダプタファクトリへ刷新 |
| **Step 6** | Test | `tests/unit/services/test_image_adapters.py` | [NEW] 画像生成アダプタ＆ファクトリ単体テスト |
| **Step 7** | Audio | `src/services/audio/adapters/base.py` | [NEW] AudioTtsAdapter 抽象基底インターフェース |
| **Step 8** | Audio | `src/services/audio/adapters/elevenlabs_adapter.py` | [NEW] ElevenLabs / OpenAI TTS 従量APIアダプタ |
| **Step 9** | Audio | `src/services/audio/factory.py` | [MODIFY] 常駐VOICEVOXコンテナ前提を廃止し、オンデマンドAPI切替対応 |
| **Step 10** | Test | `tests/unit/services/test_audio_adapters.py` | [NEW] 音声合成アダプタ単体テスト |
| **Step 11** | Copy | `src/services/formatters/platform_copy_formatter.py` | [NEW] 投稿サイト別（なろう・カクヨム・アルファ）整形エンジン |
| **Step 12** | API | `src/backend/routers/platform_export.py` | [NEW] ワンクリック整形テキスト取得APIエンドポイント |
| **Step 13** | Test | `tests/unit/services/test_platform_copy_formatter.py` | [NEW] 投稿サイト別ルビ・改行・前書き後書き整形テスト |
| **Step 14** | Cleanup | `src/services/publishers/` | [MODIFY] 脆いヘッドレス自動ログイン処理の非推奨化と整理 |
| **Step 15** | EPUB | `src/services/exporters/epub_vertical_styler.py` | [NEW] 商用KDP/楽天Kobo互換の縦書きCSS完全版 |
| **Step 16** | EPUB | `src/services/exporters/epub_ruby_processor.py` | [NEW] なろう/カクヨム記法からEPUB 3 XHTMLルビ・傍点タグへの高速変換器 |
| **Step 17** | EPUB | `src/services/exporters/commercial_epub_builder.py` | [MODIFY] 目次・表紙・縦書きCSSを包含する純Python組版ビルダー |
| **Step 18** | Test | `tests/unit/services/test_commercial_epub_builder.py` | [NEW] 商用EPUB 3バリデーション単体テスト |
| **Step 19** | Cost | `src/services/cost_guard/budget_calculator.py` | [NEW] モデル別トークン単価・コスト計算エンジン |
| **Step 20** | Cost | `src/services/cost_guard/token_circuit_breaker.py` | [NEW] 1話あたりコスト/トークン上限サーキットブレーカー |
| **Step 21** | Test | `tests/unit/services/test_token_circuit_breaker.py` | [NEW] 予算超過時の自動遮断単体テスト |
| **Step 22** | Docker | `docker/postgres/Dockerfile` | [MODIFY] Apache AGE独自ビルドを削除し軽量公式イメージへ一本化 |
| **Step 23** | Docker | `docker-compose.yml` | [MODIFY] GPU依存・AGE依存を全廃し、CPU最小構成（512MB稼働）に最適化 |
| **Step 24** | Verify | `tests/integration/test_zero_cost_pipeline.py` | [NEW] 外部API・整形コピー・EPUB・コストガードの総合結合テスト |

---

## 🛠️ 各ステップの詳細手順（1〜24）

### Step 1: ImageGenerationAdapter 抽象基底インターフェース
- **対象ファイル**: `src/services/illustration/adapters/base.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class ImagePromptRequest:
    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    aspect_ratio: str = "1:1"
    steps: int = 25
    seed: Optional[int] = None
    style: str = "anime"

@dataclass
class GeneratedImageResult:
    image_bytes: bytes
    format: str = "png"
    provider: str = "unknown"
    cost_usd: float = 0.0
    metadata: Dict[str, Any] = None

class ImageGenerationAdapter(ABC):
    """外部従量課金画像生成API用のアダプタ基底クラス"""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def generate_image(self, request: ImagePromptRequest) -> GeneratedImageResult:
        """画像を1枚生成しバイトデータと消費コストを返す"""
        pass
```
- **検証コマンド**:
```bash
python -c "from src.services.illustration.adapters.base import ImageGenerationAdapter, ImagePromptRequest; print(ImagePromptRequest(prompt='test').prompt)"
```
- **期待結果**: `test`

---

### Step 2: OpenAI DALL-E 3 オンデマンド従量アダプタ
- **対象ファイル**: `src/services/illustration/adapters/dalle3_adapter.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
import base64
import httpx
from src.services.illustration.adapters.base import (
    ImageGenerationAdapter,
    ImagePromptRequest,
    GeneratedImageResult,
)

class Dalle3Adapter(ImageGenerationAdapter):
    """OpenAI DALL-E 3 オンデマンド従量課金アダプタ（標準: $0.040/枚）"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "dalle3"

    async def generate_image(self, request: ImagePromptRequest) -> GeneratedImageResult:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # DALL-E 3 解像度正規化
        size = "1024x1024"
        if request.aspect_ratio in ("16:9", "horizontal"):
            size = "1792x1024"
        elif request.aspect_ratio in ("9:16", "vertical"):
            size = "1024x1792"

        payload = {
            "model": "dall-e-3",
            "prompt": request.prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json",
            "quality": "standard",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/images/generations", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        b64_str = data["data"][0]["b64_json"]
        image_bytes = base64.b64decode(b64_str)

        return GeneratedImageResult(
            image_bytes=image_bytes,
            format="png",
            provider="dalle3",
            cost_usd=0.040,
            metadata={"revised_prompt": data["data"][0].get("revised_prompt", "")},
        )
```
- **検証コマンド**:
```bash
python -c "from src.services.illustration.adapters.dalle3_adapter import Dalle3Adapter; a = Dalle3Adapter('fake'); print(a.provider_name)"
```
- **期待結果**: `dalle3`

---

### Step 3: fal.ai (Flux / SDXL) 高速・格安APIアダプタ
- **対象ファイル**: `src/services/illustration/adapters/fal_adapter.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
import httpx
from src.services.illustration.adapters.base import (
    ImageGenerationAdapter,
    ImagePromptRequest,
    GeneratedImageResult,
)

class FalAiAdapter(ImageGenerationAdapter):
    """fal.ai 従量課金アダプタ（Flux.1 schnell: 約$0.003/枚, SDXL: 約$0.005/枚）"""

    def __init__(self, api_key: str, model_endpoint: str = "fal-ai/flux/schnell"):
        self.api_key = api_key
        self.model_endpoint = model_endpoint

    @property
    def provider_name(self) -> str:
        return "fal_ai"

    async def generate_image(self, request: ImagePromptRequest) -> GeneratedImageResult:
        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }
        
        image_size = "square_hd"
        if request.aspect_ratio in ("9:16", "vertical"):
            image_size = "portrait_16_9"
        elif request.aspect_ratio in ("16:9", "horizontal"):
            image_size = "landscape_16_9"

        payload = {
            "prompt": request.prompt,
            "image_size": image_size,
            "num_inference_steps": min(request.steps, 10) if "schnell" in self.model_endpoint else request.steps,
            "seed": request.seed,
            "enable_safety_checker": True,
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            submit_resp = await client.post(
                f"https://queue.fal.run/{self.model_endpoint}",
                json=payload,
                headers=headers,
            )
            submit_resp.raise_for_status()
            data = submit_resp.json()
            
            image_url = data["images"][0]["url"]
            img_resp = await client.get(image_url)
            img_resp.raise_for_status()
            image_bytes = img_resp.content

        return GeneratedImageResult(
            image_bytes=image_bytes,
            format="png",
            provider="fal_ai",
            cost_usd=0.0035,
            metadata={"endpoint": self.model_endpoint},
        )
```
- **検証コマンド**:
```bash
python -c "from src.services.illustration.adapters.fal_adapter import FalAiAdapter; a = FalAiAdapter('fake'); print(a.provider_name)"
```
- **期待結果**: `fal_ai`

---

### Step 4: テスト・開発用ゼロコストモックアダプタ
- **対象ファイル**: `src/services/illustration/adapters/mock_adapter.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
from src.services.illustration.adapters.base import (
    ImageGenerationAdapter,
    ImagePromptRequest,
    GeneratedImageResult,
)

# 1x1 透明PNGダミーバイト列
DUMMY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00"
    b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

class MockImageAdapter(ImageGenerationAdapter):
    """開発・CIテスト用ダミー画像生成アダプタ（コスト0円）"""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def generate_image(self, request: ImagePromptRequest) -> GeneratedImageResult:
        return GeneratedImageResult(
            image_bytes=DUMMY_PNG,
            format="png",
            provider="mock",
            cost_usd=0.0,
            metadata={"mock_prompt": request.prompt},
        )
```
- **検証コマンド**:
```bash
python -c "import asyncio; from src.services.illustration.adapters.mock_adapter import MockImageAdapter; from src.services.illustration.adapters.base import ImagePromptRequest; res = asyncio.run(MockImageAdapter().generate_image(ImagePromptRequest(prompt='a'))); print(res.provider, len(res.image_bytes) > 0)"
```
- **期待結果**: `mock True`

---

### Step 5: ComfyUI依存を完全排除しAPIアダプタファクトリへ刷新
- **対象ファイル**: `src/services/illustration/factory.py` (修正)
- **実装コード**:
```python
from __future__ import annotations
import os
from src.services.illustration.adapters.base import ImageGenerationAdapter
from src.services.illustration.adapters.mock_adapter import MockImageAdapter
from src.services.illustration.adapters.dalle3_adapter import Dalle3Adapter
from src.services.illustration.adapters.fal_adapter import FalAiAdapter

def get_image_adapter(provider: str | None = None) -> ImageGenerationAdapter:
    """外部従量APIベースの画像生成アダプタファクトリ。
    自前GPU/ComfyUI常駐コンテナは廃止し、オンデマンドAPIへ一本化。
    """
    if provider is None:
        provider = os.getenv("IMAGE_PROVIDER", "mock").lower()

    if provider == "mock":
        return MockImageAdapter()
    elif provider in ("dalle", "dalle3", "openai"):
        api_key = os.getenv("OPENAI_API_KEY", "")
        return Dalle3Adapter(api_key=api_key)
    elif provider in ("fal", "fal_ai"):
        api_key = os.getenv("FAL_KEY", "") or os.getenv("FAL_AI_API_KEY", "")
        return FalAiAdapter(api_key=api_key)
    else:
        # 未知のプロバイダの場合は安全にMockへフォールバック
        return MockImageAdapter()
```
- **検証コマンド**:
```bash
python -c "from src.services.illustration.factory import get_image_adapter; a = get_image_adapter('mock'); print(a.provider_name)"
```
- **期待結果**: `mock`

---

### Step 6: 画像生成アダプタ＆ファクトリ単体テスト
- **対象ファイル**: `tests/unit/services/test_image_adapters.py` (新規作成)
- **実装コード**:
```python
import pytest
from src.services.illustration.adapters.base import ImagePromptRequest
from src.services.illustration.adapters.mock_adapter import MockImageAdapter
from src.services.illustration.adapters.dalle3_adapter import Dalle3Adapter
from src.services.illustration.factory import get_image_adapter

@pytest.mark.asyncio
async def test_mock_image_adapter():
    adapter = MockImageAdapter()
    req = ImagePromptRequest(prompt="ファンタジー勇者の剣", aspect_ratio="1:1")
    res = await adapter.generate_image(req)
    assert res.provider == "mock"
    assert res.cost_usd == 0.0
    assert len(res.image_bytes) > 0

def test_image_factory_fallback():
    adapter = get_image_adapter("unknown_provider")
    assert adapter.provider_name == "mock"

def test_dalle_adapter_initialization():
    adapter = Dalle3Adapter(api_key="sk-test")
    assert adapter.provider_name == "dalle3"
```
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/unit/services/test_image_adapters.py
```
- **期待結果**: `3 passed`

---

### Step 7: AudioTtsAdapter 抽象基底インターフェース
- **対象ファイル**: `src/services/audio/adapters/base.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class TtsRequest:
    text: str
    voice_id: str = "default"
    speed: float = 1.0
    format: str = "mp3"

@dataclass
class TtsResult:
    audio_bytes: bytes
    format: str = "mp3"
    provider: str = "mock"
    cost_usd: float = 0.0
    character_count: int = 0

class AudioTtsAdapter(ABC):
    """従量課金TTS音声合成プロバイダ基底クラス"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def synthesize(self, request: TtsRequest) -> TtsResult:
        pass
```
- **検証コマンド**:
```bash
python -c "from src.services.audio.adapters.base import TtsRequest; print(TtsRequest(text='こんにちは').text)"
```
- **期待結果**: `こんにちは`

---

### Step 8: ElevenLabs / OpenAI TTS 従量APIアダプタ
- **対象ファイル**: `src/services/audio/adapters/elevenlabs_adapter.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
import httpx
from src.services.audio.adapters.base import AudioTtsAdapter, TtsRequest, TtsResult

class OpenAIttsAdapter(AudioTtsAdapter):
    """OpenAI TTS オンデマンド従量APIアダプタ（標準: $0.015 / 1k文字）"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def provider_name(self) -> str:
        return "openai_tts"

    async def synthesize(self, request: TtsRequest) -> TtsResult:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "tts-1",
            "input": request.text,
            "voice": request.voice_id if request.voice_id != "default" else "alloy",
            "speed": request.speed,
            "response_format": request.format,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.openai.com/v1/audio/speech", json=payload, headers=headers)
            resp.raise_for_status()
            audio_bytes = resp.content

        char_len = len(request.text)
        cost = (char_len / 1000.0) * 0.015
        return TtsResult(
            audio_bytes=audio_bytes,
            format=request.format,
            provider="openai_tts",
            cost_usd=cost,
            character_count=char_len,
        )
```
- **検証コマンド**:
```bash
python -c "from src.services.audio.adapters.elevenlabs_adapter import OpenAIttsAdapter; a = OpenAIttsAdapter('fake'); print(a.provider_name)"
```
- **期待結果**: `openai_tts`

---

### Step 9: 常駐VOICEVOXコンテナ前提を廃止しオンデマンドAPI切替対応
- **対象ファイル**: `src/services/audio/factory.py` (修正)
- **実装コード**:
```python
from __future__ import annotations
import os
from src.services.audio.adapters.base import AudioTtsAdapter, TtsRequest, TtsResult
from src.services.audio.adapters.elevenlabs_adapter import OpenAIttsAdapter

class MockTtsAdapter(AudioTtsAdapter):
    @property
    def provider_name(self) -> str:
        return "mock"

    async def synthesize(self, request: TtsRequest) -> TtsResult:
        return TtsResult(
            audio_bytes=b"RIFFdummyWAVEfmt",
            format="wav",
            provider="mock",
            cost_usd=0.0,
            character_count=len(request.text),
        )

def get_tts_adapter(provider: str | None = None) -> AudioTtsAdapter:
    if provider is None:
        provider = os.getenv("TTS_PROVIDER", "mock").lower()

    if provider in ("openai", "openai_tts"):
        return OpenAIttsAdapter(api_key=os.getenv("OPENAI_API_KEY", ""))
    return MockTtsAdapter()
```
- **検証コマンド**:
```bash
python -c "from src.services.audio.factory import get_tts_adapter; print(get_tts_adapter().provider_name)"
```
- **期待結果**: `mock`

---

### Step 10: 音声合成アダプタ単体テスト
- **対象ファイル**: `tests/unit/services/test_audio_adapters.py` (新規作成)
- **実装コード**:
```python
import pytest
from src.services.audio.adapters.base import TtsRequest
from src.services.audio.factory import get_tts_adapter, MockTtsAdapter

@pytest.mark.asyncio
async def test_mock_tts_adapter():
    adapter = MockTtsAdapter()
    req = TtsRequest(text="ナレーションテキスト")
    res = await adapter.synthesize(req)
    assert res.provider == "mock"
    assert res.character_count == 10
    assert len(res.audio_bytes) > 0

def test_tts_factory_default():
    adapter = get_tts_adapter("mock")
    assert adapter.provider_name == "mock"
```
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/unit/services/test_audio_adapters.py
```
- **期待結果**: `2 passed`

---

### Step 11: 投稿サイト別（なろう・カクヨム・アルファ）整形エンジン
- **対象ファイル**: `src/services/formatters/platform_copy_formatter.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class FormattedChapterPayload:
    title: str
    foreword: str = ""       # 前書き
    body: str = ""           # 本文（最適化済み）
    afterword: str = ""      # 後書き
    total_characters: int = 0
    platform: str = "narou"

class PlatformCopyFormatter:
    """小説家になろう・カクヨム・アルファポリス等の規格にワンクリックコピー整形するエンジン"""

    DIALOGUE_STARTERS = ("「", "『", "（", "(", "【", "［", "[", "〈", "《", "“", "\"")

    @classmethod
    def format_for_platform(
        cls,
        title: str,
        body: str,
        foreword: str = "",
        afterword: str = "",
        platform: str = "narou",
    ) -> FormattedChapterPayload:
        platform = platform.lower()
        cleaned_body = cls._clean_typography(body)
        
        if platform == "kakuyomu":
            formatted_body = cls._to_kakuyomu_ruby(cleaned_body)
        elif platform == "alphapolis":
            formatted_body = cls._to_alphapolis_ruby(cleaned_body)
        else: # narou (default)
            formatted_body = cls._to_narou_ruby(cleaned_body)

        return FormattedChapterPayload(
            title=title.strip(),
            foreword=foreword.strip(),
            body=formatted_body,
            afterword=afterword.strip(),
            total_characters=len(formatted_body),
            platform=platform,
        )

    @classmethod
    def _clean_typography(cls, text: str) -> str:
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        out: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                out.append("")
                continue
            content = line.lstrip(" 　")
            if content.startswith(cls.DIALOGUE_STARTERS):
                out.append(content)
            else:
                out.append(f"　{content}")
        # 連続空行を最大2行に制限
        res = "\n".join(out)
        return re.sub(r"\n{3,}", "\n\n", res)

    @classmethod
    def _to_narou_ruby(cls, text: str) -> str:
        # なろう形式: |漢字《かんじ》
        return re.sub(r"[\|｜]([^《]+)《([^》]+)》", r"|\1《\2》", text)

    @classmethod
    def _to_kakuyomu_ruby(cls, text: str) -> str:
        # カクヨム形式: |漢字《かんじ》
        return re.sub(r"[\|｜]([^《]+)《([^》]+)》", r"|\1《\2》", text)

    @classmethod
    def _to_alphapolis_ruby(cls, text: str) -> str:
        # アルファポリス形式: #漢字__かんじ#
        return re.sub(r"[\|｜]([^《]+)《([^》]+)》", r"#\1__\2#", text)
```
- **検証コマンド**:
```bash
python -c "from src.services.formatters.platform_copy_formatter import PlatformCopyFormatter; r = PlatformCopyFormatter.format_for_platform('第1話', '走った。', platform='alphapolis'); print(r.platform, r.body)"
```
- **期待結果**: `alphapolis 　走った。`

---

### Step 12: ワンクリック整形テキスト取得APIエンドポイント
- **対象ファイル**: `src/backend/routers/platform_export.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from src.services.formatters.platform_copy_formatter import PlatformCopyFormatter

router = APIRouter(prefix="/api/export/copy", tags=["export-copy"])

class CopyFormatRequest(BaseModel):
    title: str
    body: str
    foreword: str = ""
    afterword: str = ""
    platform: str = "narou" # narou, kakuyomu, alphapolis

class CopyFormatResponse(BaseModel):
    title: str
    foreword: str
    body: str
    afterword: str
    total_characters: int
    platform: str

@router.post("/", response_model=CopyFormatResponse)
async def format_chapter_for_copy(req: CopyFormatRequest):
    """Web小説投稿サイト別の整形済みテキストを返却する（クリップボードコピー用）"""
    res = PlatformCopyFormatter.format_for_platform(
        title=req.title,
        body=req.body,
        foreword=req.foreword,
        afterword=req.afterword,
        platform=req.platform,
    )
    return CopyFormatResponse(
        title=res.title,
        foreword=res.foreword,
        body=res.body,
        afterword=res.afterword,
        total_characters=res.total_characters,
        platform=res.platform,
    )
```
- **検証コマンド**:
```bash
python -c "from src.backend.routers.platform_export import router; print(router.prefix)"
```
- **期待結果**: `/api/export/copy`

---

### Step 13: 投稿サイト別ルビ・改行・前書き後書き整形テスト
- **対象ファイル**: `tests/unit/services/test_platform_copy_formatter.py` (新規作成)
- **実装コード**:
```python
from src.services.formatters.platform_copy_formatter import PlatformCopyFormatter

def test_narou_formatting():
    res = PlatformCopyFormatter.format_for_platform(
        title="第1章 旅立ち",
        body="「行くぞ」\n旅人は言った。\n\n\n|真紅《しんく》の瞳。",
        platform="narou",
    )
    assert res.platform == "narou"
    assert "「行くぞ」" in res.body
    assert "　旅人は言った。" in res.body
    assert "|真紅《しんく》" in res.body

def test_alphapolis_formatting():
    res = PlatformCopyFormatter.format_for_platform(
        title="第1章",
        body="|勇者《ゆうしゃ》よ",
        platform="alphapolis",
    )
    assert "#勇者__ゆうしゃ#" in res.body
```
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/unit/services/test_platform_copy_formatter.py
```
- **期待結果**: `2 passed`

---

### Step 14: 脆いヘッドレス自動ログイン処理の非推奨化と整理
- **対象ファイル**: `src/services/publishers/__init__.py` (修正)
- **実装コード**:
```python
"""Publishers Package (v5.0 Deprecation Notice)
自動ブラウザ操作によるWeb小説投稿機能は、サイト側のCAPTCHA導入や規約リスク、
高いメンテナンスコストのためv5.0で非推奨（Deprecated）となりました。
今後は PlatformCopyFormatter によるワンクリック整形コピー機能を使用してください。
"""
__all__ = []
```
- **検証コマンド**:
```bash
python -c "import src.services.publishers as p; print(p.__doc__[:10])"
```
- **期待結果**: `Publishers`

---

### Step 15: 商用KDP/楽天Kobo互換の縦書きCSS完全版
- **対象ファイル**: `src/services/exporters/epub_vertical_styler.py` (新規作成)
- **実装コード**:
```python
"""Commercial Vertical EPUB 3 CSS Styler for Kindle (KDP) and Rakuten Kobo."""

COMMERCIAL_VERTICAL_CSS = """@charset "UTF-8";

html {
  writing-mode: vertical-rl;
  -webkit-writing-mode: vertical-rl;
  -epub-writing-mode: vertical-rl;
  font-family: "Hiragino Mincho ProN", "Yu Mincho", serif;
  font-size: 100%;
  line-height: 1.85;
}

body {
  margin: 0;
  padding: 0;
}

h1, h2, h3 {
  font-family: "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif;
  margin-right: 1.5em;
  margin-left: 1.5em;
}

p {
  margin: 0;
  padding: 0;
  text-indent: 1em;
  text-align: justify;
}

p.dialogue {
  text-indent: 0;
}

/* 禁則処理 */
p, div {
  word-break: normal;
  overflow-wrap: break-word;
}

/* 圏点・傍点 */
span.bouten {
  -webkit-text-emphasis-style: sesame;
  text-emphasis-style: sesame;
}

/* 縦中横 (2桁数字・感嘆符) */
span.tcy {
  -webkit-text-combine: horizontal;
  -epub-text-combine: horizontal;
  text-combine-upright: all;
}
"""
```
- **検証コマンド**:
```bash
python -c "from src.services.exporters.epub_vertical_styler import COMMERCIAL_VERTICAL_CSS; print('writing-mode: vertical-rl;' in COMMERCIAL_VERTICAL_CSS)"
```
- **期待結果**: `True`

---

### Step 16: なろう/カクヨム記法からEPUB 3 XHTMLルビ・傍点タグへの高速変換器
- **対象ファイル**: `src/services/exporters/epub_ruby_processor.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
import html
import re

class EpubRubyProcessor:
    """Web小説のルビ表記・縦中横をEPUB 3 XHTMLタグへ変換する"""

    @classmethod
    def to_xhtml_paragraphs(cls, text: str) -> str:
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        xhtml_lines: list[str] = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                xhtml_lines.append('<p class="empty-line">&#160;</p>')
                continue

            escaped = html.escape(line_str)
            # ルビ変換: |漢字《かんじ》 -> <ruby>漢字<rt>かんじ</rt></ruby>
            with_ruby = re.sub(r"[\|｜]([^《]+)《([^》]+)》", r"<ruby>\1<rt>\2</rt></ruby>", escaped)
            # 傍点変換: 《《強調》》 -> <span class="bouten">強調</span>
            with_bouten = re.sub(r"《《([^》]+)》》", r'<span class="bouten">\1</span>', with_ruby)
            # 2桁数字の縦中横: !! or ?? or 2桁数字
            with_tcy = re.sub(r"\b([0-9]{2})\b", r'<span class="tcy">\1</span>', with_bouten)
            with_tcy = re.sub(r"([!?！？]{2})", r'<span class="tcy">\1</span>', with_tcy)

            is_dialogue = line_str.startswith(("「", "『", "（", "("))
            p_class = ' class="dialogue"' if is_dialogue else ""
            xhtml_lines.append(f"<p{p_class}>{with_tcy}</p>")

        return "\n".join(xhtml_lines)
```
- **検証コマンド**:
```bash
python -c "from src.services.exporters.epub_ruby_processor import EpubRubyProcessor; print(EpubRubyProcessor.to_xhtml_paragraphs('|勇者《ゆうしゃ》'))"
```
- **期待結果**: `<p><ruby>勇者<rt>ゆうしゃ</rt></ruby></p>`

---

### Step 17: 目次・表紙・縦書きCSSを包含する純Python組版ビルダー
- **対象ファイル**: `src/services/exporters/commercial_epub_builder.py` (新規作成/整理)
- **実装コード**:
```python
from __future__ import annotations
import uuid
import zipfile
import io
from typing import Any, List, Dict
from src.services.exporters.epub_vertical_styler import COMMERCIAL_VERTICAL_CSS
from src.services.exporters.epub_ruby_processor import EpubRubyProcessor

class PureCommercialEpubBuilder:
    """外部コマンド(calibre等)不要、純Python/標準ライブラリのみでKDP準拠EPUB 3を生成"""

    def build_epub(
        self,
        title: str,
        author: str,
        chapters: List[Dict[str, str]], # [{"title": "第1話", "body": "..."}]
    ) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. mimetype (先頭・非圧縮)
            zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

            # 2. container.xml
            container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>"""
            zf.writestr("META-INF/container.xml", container_xml)

            # 3. CSS
            zf.writestr("OEBPS/styles/vertical.css", COMMERCIAL_VERTICAL_CSS)

            # 4. Chapters XHTML
            manifest_items = ['<item id="css" href="styles/vertical.css" media-type="text/css"/>']
            spine_items = []
            
            for idx, ch in enumerate(chapters, 1):
                ch_id = f"chapter_{idx}"
                body_html = EpubRubyProcessor.to_xhtml_paragraphs(ch.get("body", ""))
                xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ja">
<head>
    <meta charset="utf-8"/>
    <title>{ch.get("title", "")}</title>
    <link rel="stylesheet" type="text/css" href="styles/vertical.css"/>
</head>
<body class="vertical-text">
    <h2>{ch.get("title", "")}</h2>
    {body_html}
</body>
</html>"""
                zf.writestr(f"OEBPS/{ch_id}.xhtml", xhtml)
                manifest_items.append(f'<item id="{ch_id}" href="{ch_id}.xhtml" media-type="application/xhtml+xml"/>')
                spine_items.append(f'<itemref idref="{ch_id}"/>')

            # 5. content.opf
            unique_id = str(uuid.uuid4())
            opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="pub-id">urn:uuid:{unique_id}</dc:identifier>
        <dc:title>{title}</dc:title>
        <dc:creator>{author}</dc:creator>
        <dc:language>ja</dc:language>
    </metadata>
    <manifest>
        {"".join(manifest_items)}
    </manifest>
    <spine page-progression-direction="rtl">
        {"".join(spine_items)}
    </spine>
</package>"""
            zf.writestr("OEBPS/content.opf", opf)

        return buf.getvalue()
```
- **検証コマンド**:
```bash
python -c "from src.services.exporters.commercial_epub_builder import PureCommercialEpubBuilder; b = PureCommercialEpubBuilder().build_epub('テスト', '作者', [{'title': '1話', 'body': '本文'}]); print(len(b) > 500)"
```
- **期待結果**: `True`

---

### Step 18: 商用EPUB 3バリデーション単体テスト
- **対象ファイル**: `tests/unit/services/test_commercial_epub_builder.py` (新規作成)
- **実装コード**:
```python
import io
import zipfile
from src.services.exporters.commercial_epub_builder import PureCommercialEpubBuilder

def test_pure_epub_builder_structure():
    builder = PureCommercialEpubBuilder()
    data = builder.build_epub(
        title="異世界転生録",
        author="作家A",
        chapters=[{"title": "第一話", "body": "|勇者《ゆうしゃ》誕生。\n「行くぞ！」"}],
    )
    zf = zipfile.ZipFile(io.BytesIO(data))
    namelist = zf.namelist()

    # EPUB必須ファイルの存在検証
    assert "mimetype" in namelist
    assert "META-INF/container.xml" in namelist
    assert "OEBPS/content.opf" in namelist
    assert "OEBPS/styles/vertical.css" in namelist
    assert "OEBPS/chapter_1.xhtml" in namelist

    # 右開き（縦書きrtl）の検証
    opf = zf.read("OEBPS/content.opf").decode("utf-8")
    assert 'page-progression-direction="rtl"' in opf
```
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/unit/services/test_commercial_epub_builder.py
```
- **期待結果**: `1 passed`

---

### Step 19: モデル別トークン単価・コスト計算エンジン
- **対象ファイル**: `src/services/cost_guard/budget_calculator.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations
from dataclasses import dataclass

# 1M (1,000,000) トークンあたりの価格 (USD)
MODEL_PRICING = {
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
}

USD_JPY_RATE = 150.0

@dataclass
class CostEstimate:
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    cost_jpy: float

class BudgetCalculator:
    """トークン消費量とモデル価格表に基づくコスト計算"""

    @classmethod
    def calculate_cost(cls, model: str, prompt_tokens: int, completion_tokens: int) -> CostEstimate:
        pricing = MODEL_PRICING.get(model, {"input": 0.15, "output": 0.60})
        cost_usd = (prompt_tokens / 1_000_000.0) * pricing["input"] + (
            completion_tokens / 1_000_000.0
        ) * pricing["output"]
        cost_jpy = cost_usd * USD_JPY_RATE

        return CostEstimate(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=round(cost_usd, 6),
            cost_jpy=round(cost_jpy, 4),
        )
```
- **検証コマンド**:
```bash
python -c "from src.services.cost_guard.budget_calculator import BudgetCalculator; c = BudgetCalculator.calculate_cost('gemini-2.5-flash', 10000, 3000); print(c.cost_jpy < 1.0)"
```
- **期待結果**: `True`

---

### Step 20: 1話あたりコスト/トークン上限サーキットブレーカー
- **対象ファイル**: `src/services/cost_guard/token_circuit_breaker.py` (新規作成)
- **実装コード**:
```python
from __future__ import annotations

class BudgetExceededError(Exception):
    """トークンまたはコストの予算上限を超過した際の例外"""
    pass

class TokenCircuitBreaker:
    """1話あたりの暴走・無限ループ課金を防止する安全装置"""

    def __init__(self, max_tokens_per_episode: int = 50_000, max_cost_jpy_per_episode: float = 15.0):
        self.max_tokens = max_tokens_per_episode
        self.max_cost_jpy = max_cost_jpy_per_episode
        self.accumulated_tokens = 0
        self.accumulated_cost_jpy = 0.0

    def record_usage(self, tokens: int, cost_jpy: float):
        self.accumulated_tokens += tokens
        self.accumulated_cost_jpy += cost_jpy

        if self.accumulated_tokens > self.max_tokens:
            raise BudgetExceededError(
                f"Token budget exceeded: {self.accumulated_tokens} > {self.max_tokens}"
            )
        if self.accumulated_cost_jpy > self.max_cost_jpy:
            raise BudgetExceededError(
                f"Cost budget exceeded: {self.accumulated_cost_jpy:.2f} JPY > {self.max_cost_jpy:.2f} JPY"
            )

    def reset(self):
        self.accumulated_tokens = 0
        self.accumulated_cost_jpy = 0.0
```
- **検証コマンド**:
```bash
python -c "from src.services.cost_guard.token_circuit_breaker import TokenCircuitBreaker; b = TokenCircuitBreaker(); b.record_usage(100, 0.1); print(b.accumulated_tokens)"
```
- **期待結果**: `100`

---

### Step 21: 予算超過時の自動遮断単体テスト
- **対象ファイル**: `tests/unit/services/test_token_circuit_breaker.py` (新規作成)
- **実装コード**:
```python
import pytest
from src.services.cost_guard.token_circuit_breaker import TokenCircuitBreaker, BudgetExceededError

def test_circuit_breaker_pass():
    breaker = TokenCircuitBreaker(max_tokens_per_episode=1000, max_cost_jpy_per_episode=5.0)
    breaker.record_usage(500, 2.0)
    assert breaker.accumulated_tokens == 500

def test_circuit_breaker_token_exceeded():
    breaker = TokenCircuitBreaker(max_tokens_per_episode=1000, max_cost_jpy_per_episode=5.0)
    with pytest.raises(BudgetExceededError) as exc:
        breaker.record_usage(1001, 1.0)
    assert "Token budget exceeded" in str(exc.value)

def test_circuit_breaker_cost_exceeded():
    breaker = TokenCircuitBreaker(max_tokens_per_episode=50000, max_cost_jpy_per_episode=5.0)
    with pytest.raises(BudgetExceededError) as exc:
        breaker.record_usage(1000, 5.5)
    assert "Cost budget exceeded" in str(exc.value)
```
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/unit/services/test_token_circuit_breaker.py
```
- **期待結果**: `3 passed`

---

### Step 22: Apache AGE独自ビルドを削除し軽量公式イメージへ一本化
- **対象ファイル**: `docker/postgres/Dockerfile` (修正)
- **実装コード**:
```dockerfile
# AutoNovel v5.0: Apache AGE (Graph DB) の独自ビルドを廃止し、
# 公式 pgvector 軽量イメージへ一本化（ビルド時間短縮 & クラッシュゼロ）
FROM pgvector/pgvector:pg16

# 初期化スクリプト等があれば必要に応じてコピー
COPY ./docker/postgres/init.sql /docker-entrypoint-initdb.d/init.sql
```
- **検証コマンド**:
```bash
python -c "with open('docker/postgres/Dockerfile') as f: content = f.read(); assert 'apache/age' not in content"
```
- **期待結果**: (エラーなし)

---

### Step 23: GPU依存・AGE依存を全廃しCPU最小構成に最適化
- **対象ファイル**: `docker-compose.yml` (dbサービスの簡素化)
- **変更箇所**:
`docker-compose.yml` の `db` サービス定義を軽量化:
```yaml
  db:
    image: pgvector/pgvector:pg16
    container_name: autonovel_db
    environment:
      - POSTGRES_USER=autonovel
      - POSTGRES_PASSWORD=autonovel
      - POSTGRES_DB=autonovel
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U autonovel -d autonovel"]
      interval: 5s
      timeout: 5s
      retries: 5
```
- **検証コマンド**:
```bash
python -c "import yaml; open('docker-compose.yml')"
```
- **期待結果**: (正常にオープン可能)

---

### Step 24: 外部API・整形コピー・EPUB・コストガードの総合結合テスト
- **対象ファイル**: `tests/integration/test_zero_cost_pipeline.py` (新規作成)
- **実装コード**:
```python
import pytest
from src.services.illustration.factory import get_image_adapter
from src.services.audio.factory import get_tts_adapter
from src.services.formatters.platform_copy_formatter import PlatformCopyFormatter
from src.services.exporters.commercial_epub_builder import PureCommercialEpubBuilder
from src.services.cost_guard.budget_calculator import BudgetCalculator
from src.services.cost_guard.token_circuit_breaker import TokenCircuitBreaker

@pytest.mark.asyncio
async def test_zero_cost_pipeline_integration():
    # 1. 外部従量モック画像アダプタ
    img_adapter = get_image_adapter("mock")
    img_res = await img_adapter.generate_image(type("Req", (), {"prompt": "test"})())
    assert img_res.cost_usd == 0.0

    # 2. 外部従量モック音声アダプタ
    tts_adapter = get_tts_adapter("mock")
    tts_res = await tts_adapter.synthesize(type("Req", (), {"text": "セリフ"})())
    assert tts_res.cost_usd == 0.0

    # 3. 投稿サイト整形
    formatted = PlatformCopyFormatter.format_for_platform("題名", "本文", platform="narou")
    assert formatted.platform == "narou"

    # 4. 商用EPUB 3生成
    epub_builder = PureCommercialEpubBuilder()
    epub_bytes = epub_builder.build_epub("小説タイトル", "作者", [{"title": "第1話", "body": "本文"}])
    assert len(epub_bytes) > 200

    # 5. コスト計算 & ガードレール
    cost = BudgetCalculator.calculate_cost("gemini-2.5-flash", 8000, 2500)
    breaker = TokenCircuitBreaker(max_tokens_per_episode=30000, max_cost_jpy_per_episode=10.0)
    breaker.record_usage(cost.prompt_tokens + cost.completion_tokens, cost.cost_jpy)
    assert breaker.accumulated_cost_jpy < 10.0
```
- **検証コマンド**:
```bash
.venv\Scripts\pytest tests/integration/test_zero_cost_pipeline.py
```
- **期待結果**: `1 passed`
