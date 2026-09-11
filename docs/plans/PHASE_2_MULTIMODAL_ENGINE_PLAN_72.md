# 第2段階: 外部エンジン・マルチモーダル直結フェーズ 72ステップ詳細実装計画書
## （画像生成ダイレクトAPI連携・VOICEVOX音声合成・商用EPUB 3縦書き組版刷新）

- **策定日**: 2026年9月10日
- **対象バージョン**: AutoNovel v4.5.0+
- **設計方針**: 低性能なLLMでも迷わず1ステップずつ確実に実装・検証できるよう、最小単位の作業に分割。12ステップごとに動作検証ゲート（Checkpoint）を設置。
- **総ステップ数**: 全72ステップ（6パート × 12ステップ）

---

## 📋 パート別構成概要

| パート | ステップ | テーマ | 主な対象ファイル | ステータス |
|---|---|---|---|---|
| **Part 1** | Step 1〜12 | Stable Diffusion / ComfyUI / DALL-E 3 ダイレクトHTTPアダプタ | `src/services/illustration/base.py`<br>`src/services/illustration/sd_client.py`<br>`src/services/illustration/dalle_client.py` | ⏳ 未着手 |
| **Part 2** | Step 13〜24 | 画像実体自動生成パイプライン & キャラクター一貫性（LoRA）注入 | `src/services/image_service.py`<br>`src/agents/illustration_agent.py`<br>`src/backend/tasks/illustration_tasks.py` | ⏳ 未着手 |
| **Part 3** | Step 25〜36 | VOICEVOX 音声合成エンジンのローカル/リモートAPI接続 | `src/services/audio/voicevox_client.py`<br>`src/services/audio/dialogue_extractor.py`<br>`src/backend/config.py` | ⏳ 未着手 |
| **Part 4** | Step 37〜48 | マルチメディアアセットパック統合 & 音声試聴プレイヤーUI | `src/backend/routers/multimedia.py`<br>`frontend/src/components/AssetPackPanel.tsx`<br>`frontend/src/components/common/AudioPlayer.tsx` | ⏳ 未着手 |
| **Part 5** | Step 49〜60 | EPUB 3 縦書き商用組版エンジンの刷新（ルビ・傍点・禁則処理・目次） | `src/services/exporters/epub_commercial_builder.py`<br>`src/services/exporters/vertical_css_templates.py` | ⏳ 未着手 |
| **Part 6** | Step 61〜72 | Kindle / 電子書籍リーダー互換性検証 & 第2段階 E2E 結合テスト | `tests/integration/test_phase2_multimodal_e2e.py`<br>`tests/unit/test_epub_commercial.py` | ⏳ 未着手 |

---

## 🎨 Part 1: Stable Diffusion / ComfyUI / DALL-E 3 ダイレクトHTTPアダプタ (Step 1〜12)

### Step 1: 画像生成クライアント抽象基底インターフェース `ImageGeneratorClient` の定義
- **目的**: プロバイダ（Stable Diffusion WebUI, ComfyUI, DALL-E 3, Mock）を統一的に扱う抽象クラスを定義する。
- **対象ファイル**: `src/services/illustration/base.py` (新規作成)
- **変更内容**:
  ```python
  from abc import ABC, abstractmethod
  from dataclasses import dataclass

  @dataclass
  class ImageGenerationRequest:
      prompt: str
      negative_prompt: str = ""
      width: int = 512
      height: int = 768  # 縦長ノベル挿絵比率
      steps: int = 25
      cfg_scale: float = 7.0
      seed: int = -1
      lora_tags: list[str] | None = None

  @dataclass
  class ImageGenerationResult:
      image_bytes: bytes
      format: str = "png"
      seed_used: int = -1
      metadata: dict = None

  class ImageGeneratorClient(ABC):
      @abstractmethod
      async def generate_image(self, req: ImageGenerationRequest) -> ImageGenerationResult:
          pass
  ```
- **確認コマンド**: `python -c "from src.services.illustration.base import ImageGeneratorClient; print('OK')"`
- **完了条件**: 基底インターフェースがインポートできること。

### Step 2: Stable Diffusion WebUI (AUTOMATIC1111) HTTPアダプタの実装
- **目的**: ローカルまたはリモートの SD WebUI API (`POST /sdapi/v1/txt2img`) に接続するクライアントを実装する。
- **対象ファイル**: `src/services/illustration/sd_client.py` (新規作成)
- **変更内容**: `httpx.AsyncClient` を用い、Base64画像をデコードして `ImageGenerationResult` を返す `SDWebUIClient` を実装。
- **確認コマンド**: `python -m py_compile src/services/illustration/sd_client.py`
- **完了条件**: コンパイルエラーがないこと。

### Step 3: ComfyUI REST/WebSocket アダプタの実装
- **目的**: 高度なワークフロー（キャラ固定LoRA + ControlNet）を実行できる ComfyUI 連携クライアントを実装する。
- **対象ファイル**: `src/services/illustration/comfyui_client.py` (新規作成)
- **変更内容**: `POST /prompt` でジョブを投入し、WebSocket または `/history` で完了を待機して画像バイナリを取得する `ComfyUIClient`。
- **確認コマンド**: `python -m py_compile src/services/illustration/comfyui_client.py`
- **完了条件**: コンパイルエラーがないこと。

### Step 4: OpenAI DALL-E 3 HTTPアダプタの実装
- **目的**: クラウドAPI経由で即座に高品質な挿絵を生成できる DALL-E 3 クライアントを実装する。
- **対象ファイル**: `src/services/illustration/dalle_client.py` (新規作成)
- **変更内容**: OpenAI SDK または httpx で `POST /v1/images/generations` を呼び出し、画像URLからバイナリを取得する `DalleClient`。
- **確認コマンド**: `python -m py_compile src/services/illustration/dalle_client.py`
- **完了条件**: コンパイルエラーがないこと。

### Step 5: オフライン・テスト用 `MockImageClient` の実装
- **目的**: 外部APIやGPUがない環境・テスト自動実行時に、ダミーの1x1またはSVG/PNGバイナリを返すモッククライアントを実装する。
- **対象ファイル**: `src/services/illustration/mock_client.py` (新規作成)
- **変更内容**: Pillow で指定サイズのシンプルな画像をオンメモリ生成して返す `MockImageClient`。
- **確認コマンド**: `python -m py_compile src/services/illustration/mock_client.py`
- **完了条件**: コンパイルエラーがないこと。

### Step 6: 画像生成プロバイダファクトリ `get_image_client()` の実装
- **目的**: 設定ファイルおよび環境変数 `IMAGE_PROVIDER`（`sd_webui`, `comfyui`, `dalle3`, `mock`）に応じてクライアントインスタンスを生成する。
- **対象ファイル**: `src/services/illustration/factory.py` (新規作成)
- **変更内容**: ファクトリ関数とシングルトンキャッシュ。
- **確認コマンド**: `python -c "from src.services.illustration.factory import get_image_client; client = get_image_client('mock'); assert client is not None; print('OK')"`
- **完了条件**: モッククライアントが正常に取得できること。

### Step 7: アプリケーション設定 `Settings` への画像生成パラメータ追加
- **目的**: SD WebUI の URL、ComfyUI のホスト、DALL-E の API キー、デフォルトモデルを設定可能にする。
- **対象ファイル**: `src/backend/config.py`
- **変更内容**:
  ```python
  IMAGE_PROVIDER: Literal["mock", "sd_webui", "comfyui", "dalle3"] = "mock"
  SD_WEBUI_URL: str = "http://localhost:7860"
  COMFYUI_URL: str = "http://localhost:8188"
  DEFAULT_IMAGE_WIDTH: int = 512
  DEFAULT_IMAGE_HEIGHT: int = 768
  ```
- **確認コマンド**: `python -c "from src.backend.config import settings; print(settings.IMAGE_PROVIDER)"`
- **完了条件**: デフォルト設定が読み込めること。

### Step 8: 画像クライアントの自動リトライ・タイムアウト保護
- **目的**: GPU処理の遅延や一時的な通信切断に対して、最大3回の指数バックオフリトライとタイムアウト（デフォルト120秒）を設定。
- **対象ファイル**: `src/services/illustration/sd_client.py`
- **変更内容**: `@retry_decorator` または tenacity によるリトライラップ。
- **確認コマンド**: `python -m py_compile src/services/illustration/sd_client.py`
- **完了条件**: リトライデコレータが組み込まれていること。

### Step 9: 画像生成結果メタデータ（シード値・プロンプト・使用モデル）の抽出ロジック
- **目的**: 生成された画像のメタデータを抽出し、後から同一構図で再生成（シード再現）できるようにする。
- **対象ファイル**: `src/services/illustration/base.py`
- **変更内容**: `extract_png_metadata(image_bytes: bytes) -> dict` 関数の追加。
- **確認コマンド**: `python -m py_compile src/services/illustration/base.py`
- **完了条件**: 関数が定義されていること。

### Step 10: 画像生成クライアント群の単体テスト作成
- **目的**: `MockImageClient`, `SDWebUIClient`, `DalleClient`（モックレスポンス使用）の呼び出しと例外処理を検証。
- **対象ファイル**: `tests/unit/test_image_clients.py` (新規作成)
- **変更内容**: pytest-asyncio を用いた非同期テスト。
- **確認コマンド**: `pytest tests/unit/test_image_clients.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 11: 設定変更API `POST /api/settings/illustration` の実装
- **目的**: 稼働中に画像生成プロバイダや接続先URLをGUIから変更・テスト接続できるようにする。
- **対象ファイル**: `src/backend/routers/illustrations.py`
- **変更内容**: 設定更新とテスト画像生成リクエストの疎通確認エンドポイント。
- **確認コマンド**: `python -m py_compile src/backend/routers/illustrations.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 12: 【Checkpoint 1】Part 1 画像クライアント疎通確認
- **目的**: 画像生成クライアント群の単体テストがすべて合格することを確認。
- **確認コマンド**: `pytest tests/unit/test_image_clients.py -v`
- **完了条件**: すべてのテストがオールグリーンであること。

---

## 🖼️ Part 2: 画像実体自動生成パイプライン & キャラクター一貫性（LoRA）注入 (Step 13〜24)

### Step 13: キャラクター外見設定からのLoRAタグ自動マッピングテーブル作成
- **目的**: 世界観Bibleのキャラクターデータ（髪型、目の色、服装、固有属性）から、画像生成プロンプト用LoRAタグを合成する。
- **対象ファイル**: `src/services/illustration/character_lora_mapper.py` (新規作成)
- **変更内容**:
  ```python
  class CharacterLoraMapper:
      def get_prompt_tags_for_character(self, char_data: dict) -> tuple[str, list[str]]:
          # 戻り値: (プロンプト追記文字列, 適用すべきLoRA名リスト)
          ...
  ```
- **確認コマンド**: `python -m py_compile src/services/illustration/character_lora_mapper.py`
- **完了条件**: クラスが定義されていること。

### Step 14: ライトノベル標準ネガティブプロンプトの動的注入
- **目的**: 「崩れた手」「余分な指」「低解像度」「文字混入」等を防ぐ品質保証ネガティブプロンプトを自動合成。
- **対象ファイル**: `src/services/illustration/prompt_builder.py` (新規作成)
- **変更内容**: `STANDARD_LIGHT_NOVEL_NEGATIVE = "bad anatomy, blurry, watermark, text, signature, low quality, extra limbs, bad hands"` などの定数化。
- **確認コマンド**: `python -m py_compile src/services/illustration/prompt_builder.py`
- **完了条件**: プロンプトビルダーがコンパイルできること。

### Step 15: 本文クライマックスシーンからの画像生成プロンプト自動構築ロジックの改善
- **目的**: 単なる一文抽出ではなく、「場所」「時間帯（夕暮れ・月夜など）」「登場人物の表情・アクション」を網羅した詳細プロンプトを構成。
- **対象ファイル**: `src/agents/illustration_agent.py`
- **変更内容**: `IllustrationAgent._build_scene_prompt` に環境光・カメラアングルの指示を追加。
- **確認コマンド**: `python -m py_compile src/agents/illustration_agent.py`
- **完了条件**: プロンプト構築関数が拡張されていること。

### Step 16: 画像ファイル永続化サービス `ImageStorageService` の実装
- **目的**: 生成された画像バイナリを `storage/multimedia/images/{book_id}/ep_{num}_{scene_id}.png` に安全に保存し、URLパスを発行。
- **対象ファイル**: `src/services/image_service.py`
- **変更内容**: `save_image_artifact(book_id: int, episode: int, image_bytes: bytes) -> str` の実装。
- **確認コマンド**: `python -m py_compile src/services/image_service.py`
- **完了条件**: ファイル保存とパス返却が実装されていること。

### Step 17: 画像アセットメタデータDBモデル `ImageAssetModel` の拡張
- **目的**: 生成画像ファイルパス、シード値、プロンプト、解像度、対象章番号をDBに保存。
- **対象ファイル**: `src/backend/database/models.py`
- **変更内容**: `ImageAssetModel` のカラム拡充（file_path, prompt, negative_prompt, seed, width, height, created_at）。
- **確認コマンド**: `python -c "from src.backend.database.models import ImageAssetModel; print('OK')"`
- **完了条件**: モデルがインポートできること。

### Step 18: 非同期タスク `generate_chapter_illustrations_task` の実装
- **目的**: 章の本文生成完了後に、Huey経由でバックグラウンド実行される実画像生成タスク。
- **対象ファイル**: `src/backend/tasks/illustration_tasks.py`
- **変更内容**: 本文からシーン抽出 → プロンプト構築 → `ImageGeneratorClient.generate_image` 呼び出し → DB保存。
- **確認コマンド**: `python -m py_compile src/backend/tasks/illustration_tasks.py`
- **完了条件**: タスク関数が定義されていること。

### Step 19: 画像生成進捗のSSE / EventBus 通知発行
- **目的**: 画像生成開始、完了、失敗のステータスをフロントエンドへリアルタイム中継（`illustration.started`, `illustration.completed`）。
- **対象ファイル**: `src/backend/tasks/illustration_tasks.py`
- **変更内容**: `event_bus.publish("illustration.completed", {"image_url": ..., "chapter": ...})`
- **確認コマンド**: `python -m py_compile src/backend/tasks/illustration_tasks.py`
- **完了条件**: イベント発行が記述されていること。

### Step 20: 画像一覧取得API `GET /api/illustrations/{book_id}/{chapter}` の実装
- **目的**: 指定章に紐づく生成画像の一覧（サムネイルURL、プロンプト、シード値）を返却。
- **対象ファイル**: `src/backend/routers/illustrations.py`
- **変更内容**: Pydanticレスポンススキーマ `IllustrationResponse` とエンドポイント。
- **確認コマンド**: `python -m py_compile src/backend/routers/illustrations.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 21: 画像バイナリ配信API `GET /api/illustrations/artifacts/{asset_id}/download` の実装
- **目的**: 保存されたPNGファイルをHTTPストリーミングまたはFileResponseで安全にクライアントへ配信。
- **対象ファイル**: `src/backend/routers/illustrations.py`
- **変更内容**: `FileResponse(path, media_type="image/png")` の返却。
- **確認コマンド**: `python -m py_compile src/backend/routers/illustrations.py`
- **完了条件**: 配信エンドポイントが追加されていること。

### Step 22: 画像手動再生成API `POST /api/illustrations/{asset_id}/regenerate` の追加
- **目的**: ユーザーがプロンプトやシード値を微調整して単体画像を再生成する機能。
- **対象ファイル**: `src/backend/routers/illustrations.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/illustrations.py`
- **完了条件**: 再生成エンドポイントが追加されていること。

### Step 23: 実画像生成パイプラインの統合テスト作成
- **目的**: シーン抽出からプロンプト合成、モック画像生成、DB保存、API取得までをテスト。
- **対象ファイル**: `tests/integration/test_illustration_pipeline.py` (新規作成)
- **確認コマンド**: `pytest tests/integration/test_illustration_pipeline.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 24: 【Checkpoint 2】Part 2 実画像生成パイプライン動作検証
- **目的**: パイプライン統合テストが合格することを確認。
- **確認コマンド**: `pytest tests/integration/test_illustration_pipeline.py -v`
- **完了条件**: すべてのテストがオールグリーンであること。

---

## 🎙️ Part 3: VOICEVOX 音声合成エンジンのローカル/リモートAPI接続 (Step 25〜36)

### Step 25: VOICEVOX APIクライアント `VoicevoxClient` の新設
- **目的**: VOICEVOX エンジン (`POST /audio_query`, `POST /synthesis`) に接続し、日本語テキストからWAV音声バイナリを合成する。
- **対象ファイル**: `src/services/audio/voicevox_client.py` (新規作成)
- **変更内容**:
  ```python
  class VoicevoxClient:
      def __init__(self, base_url: str = "http://localhost:50021"):
          self.base_url = base_url
      async def synthesize(self, text: str, speaker_id: int = 3) -> bytes:
          # audio_query -> synthesis -> wav_bytes
          ...
  ```
- **確認コマンド**: `python -m py_compile src/services/audio/voicevox_client.py`
- **完了条件**: クライアントがコンパイルできること。

### Step 26: テスト用 `MockAudioClient` の実装
- **目的**: VOICEVOX非起動環境でもテストやビルドが通るよう、ダミーの無音WAVヘッダーを返すモックを作成。
- **対象ファイル**: `src/services/audio/mock_client.py` (新規作成)
- **変更内容**: 標準ライブラリ `wave` を使って0.5秒の無音WAVを生成して返却。
- **確認コマンド**: `python -m py_compile src/services/audio/mock_client.py`
- **完了条件**: コンパイルできること。

### Step 27: キャラクター別話者ID（Speaker ID）割り当てテーブルの定義
- **目的**: 「主人公」「ヒロイン」「悪役」「ナレーション」にそれぞれ異なるVOICEVOX話者（四国めたん、ずんだもん等）を自動マッピング。
- **対象ファイル**: `src/services/audio/speaker_mapper.py` (新規作成)
- **変更内容**: 性別・性格属性から最適な `speaker_id` を推薦・解決するロジック。
- **確認コマンド**: `python -m py_compile src/services/audio/speaker_mapper.py`
- **完了条件**: マッパーが定義されていること。

### Step 28: 本文からのセリフ・地の文抽出パーサー `DialogueExtractor` の実装
- **目的**: 小説本文からかぎ括弧「……」のセリフと話者を抽出し、地の文（ナレーション）と分離したタイムラインリストを作成。
- **対象ファイル**: `src/services/audio/dialogue_extractor.py` (新規作成)
- **変更内容**:
  ```python
  @dataclass
  class DialogueLine:
      speaker_name: str  # キャラ名 または "narration"
      text: str
      line_index: int
  ```
- **確認コマンド**: `python -c "from src.services.audio.dialogue_extractor import DialogueExtractor; print('OK')"`
- **完了条件**: パーサーがインポートできること。

### Step 29: 音声ファイル永続化サービス `AudioStorageService` の実装
- **目的**: 合成されたWAV/MP3ファイルを `storage/multimedia/audio/{book_id}/ep_{num}_{line_id}.wav` に保存。
- **対象ファイル**: `src/services/audio/audio_storage.py` (新規作成)
- **確認コマンド**: `python -m py_compile src/services/audio/audio_storage.py`
- **完了条件**: コンパイルできること。

### Step 30: 連続した音声クリップの連結機能（章丸ごと朗読ファイル生成）
- **目的**: 各セリフ・地の文の個別WAVを結合し、1話分の通し朗読音声（`chapter_{num}_full.wav`）を生成。
- **対象ファイル**: `src/services/audio/audio_combiner.py` (新規作成)
- **変更内容**: `pydub` または `wave` による安全な連結処理（文間の適切なポーズ/無音挿入）。
- **確認コマンド**: `python -m py_compile src/services/audio/audio_combiner.py`
- **完了条件**: 結合モジュールがコンパイルできること。

### Step 31: 設定ファイル `Settings` への VOICEVOX 設定追加
- **目的**: `VOICEVOX_URL`, `DEFAULT_NARRATOR_SPEAKER_ID`, `ENABLE_AUDIO_SYNTH` を環境変数化。
- **対象ファイル**: `src/backend/config.py`
- **変更内容**:
  ```python
  VOICEVOX_URL: str = "http://localhost:50021"
  DEFAULT_NARRATOR_SPEAKER_ID: int = 3
  ```
- **確認コマンド**: `python -c "from src.backend.config import settings; print(settings.VOICEVOX_URL)"`
- **完了条件**: 設定が読み込めること。

### Step 32: 音声合成APIエンドポイント `POST /multimedia/audio/synthesize-chapter` の実装
- **目的**: 指定章のテキストを解析して音声合成ジョブを投入するエンドポイント。
- **対象ファイル**: `src/backend/routers/multimedia.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/multimedia.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 33: 音声合成タスクの非同期キューイング (`synthesize_chapter_audio_task`)
- **目的**: 長時間かかる音声生成をHueyタスクキューでバックグラウンド実行。
- **対象ファイル**: `src/backend/tasks/multimedia_tasks.py`
- **確認コマンド**: `python -m py_compile src/backend/tasks/multimedia_tasks.py`
- **完了条件**: タスクが定義されていること。

### Step 34: 音声ファイル配信API `GET /multimedia/audio/artifacts/{audio_id}/stream` の実装
- **目的**: ブラウザの `<audio>` タグで再生可能なオーディオストリーミングレスポンスを返却。
- **対象ファイル**: `src/backend/routers/multimedia.py`
- **変更内容**: `StreamingResponse` または `FileResponse(media_type="audio/wav")`。
- **確認コマンド**: `python -m py_compile src/backend/routers/multimedia.py`
- **完了条件**: 配信エンドポイントが追加されていること。

### Step 35: 音声合成パイプラインの単体テスト作成
- **目的**: セリフ抽出パーサー、話者マッパー、モック音声合成のテスト。
- **対象ファイル**: `tests/unit/test_voicevox_pipeline.py` (新規作成)
- **確認コマンド**: `pytest tests/unit/test_voicevox_pipeline.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 36: 【Checkpoint 3】Part 3 音声合成パイプライン動作検証
- **目的**: 音声合成ユニットテストがすべて合格することを確認。
- **確認コマンド**: `pytest tests/unit/test_voicevox_pipeline.py -v`
- **完了条件**: すべてのテストがオールグリーンであること。

---

## 📦 Part 4: マルチメディアアセットパック統合 & 音声試聴プレイヤーUI (Step 37〜48)

### Step 37: 納品ZIPパッケージへの音声ファイル同梱ロジック
- **目的**: `POST /easy_mode/export-with-data` で生成される納品ZIPに `05_音声/` フォルダを追加し、章朗読WAVを同梱。
- **対象ファイル**: `src/services/exporters/zip_exporter.py`
- **変更内容**: 音声ファイルが存在する場合にZIPに追加する処理。
- **確認コマンド**: `python -m py_compile src/services/exporters/zip_exporter.py`
- **完了条件**: ZIPエクスポーターが拡張されていること。

### Step 38: 納品ZIPへの画像アセット（高解像度挿絵）同梱の堅牢化
- **目的**: `06_挿絵/` フォルダに生成画像PNGとプロンプトテキストを確実に格納。
- **対象ファイル**: `src/services/exporters/zip_exporter.py`
- **確認コマンド**: `python -m py_compile src/services/exporters/zip_exporter.py`
- **完了条件**: 画像同梱処理が正常にコンパイルできること。

### Step 39: フロントエンド共通オーディオプレイヤー `AudioPlayer.tsx` の新設
- **目的**: 再生/一時停止、シークバー、音量調整、再生速度変更（1.0x, 1.25x, 1.5x）を備えたミニプレイヤーコンポーネント。
- **対象ファイル**: `frontend/src/components/common/AudioPlayer.tsx` (新規作成)
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: コンポーネントが型チェックを通過すること。

### Step 40: `AssetPackPanel.tsx` への「オーディオ試聴セクション」追加
- **目的**: アセットパック管理パネルに、章ごとの朗読音声の再生プレイヤーとWAVダウンロードボタンを配置。
- **対象ファイル**: `frontend/src/components/AssetPackPanel.tsx`
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: 型エラーなくビルドできること。

### Step 41: `AssetPackPanel.tsx` への「生成挿絵ギャラリー」追加
- **目的**: 生成された重要シーンの挿絵をグリッド表示し、ライトボックス（拡大表示）や再生成トリガーを提供。
- **対象ファイル**: `frontend/src/components/AssetPackPanel.tsx`
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: ギャラリーUIが正常に追加されていること。

### Step 42: 音声・画像生成のリアルタイムプログレスバーの統合
- **目的**: 生成ジョブの進捗率（0〜100%）と推定残り時間をプログレスバーで表示。
- **対象ファイル**: `frontend/src/components/AssetPackPanel.tsx`
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: プログレスバーが正しくレンダリングされること。

### Step 43: Studioエディタ本文横への「挿絵プレビュー」インライン埋め込み
- **目的**: エディタ中央ペインで執筆中、該当シーンの余白に生成挿絵のサムネイルを表示。
- **対象ファイル**: `frontend/src/components/editor/Editor.tsx`
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: エディタコンポーネントが型チェックを通ること。

### Step 44: 音声合成トリガーボタンのエディタツールバーへの追加
- **目的**: エディタ上部の「🪄 AIツール」に「🔊 この章を音声朗読」ボタンを配置。
- **対象ファイル**: `frontend/src/components/editor/InlineAiToolbar.tsx`
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: ツールバーにボタンが追加されていること。

### Step 45: フロントエンド型定義 `frontend/src/types/multimedia.ts` の拡張
- **目的**: 音声アセット情報、挿絵アセット情報のTypeScriptインターフェースを定義。
- **対象ファイル**: `frontend/src/types/multimedia.ts` (新規作成)
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: 型定義ファイルが作成されインポートできること。

### Step 46: マルチメディアAPIクライアント関数 `frontend/src/api/multimedia.ts` の拡充
- **目的**: `fetchAudioArtifacts`, `triggerAudioSynthesis`, `fetchIllustrationArtifacts` を実装。
- **対象ファイル**: `frontend/src/api/multimedia.ts` (新規作成)
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: API関数がエクスポートされること。

### Step 47: マルチメディアUIコンポーネントの単体テスト作成
- **目的**: `AudioPlayer.tsx` および `AssetPackPanel.tsx` のレンダリングと操作テスト。
- **対象ファイル**: `frontend/src/components/__tests__/AssetPackPanel.test.tsx` (新規作成)
- **確認コマンド**: `npm run --prefix frontend test:ci`
- **完了条件**: フロントエンドテストが通過すること。

### Step 48: 【Checkpoint 4】Part 4 マルチメディアフロントエンドビルド確認
- **目的**: フロントエンド全体の型チェックとビルドがエラー0件であることを確認。
- **確認コマンド**: `npm run --prefix frontend typecheck && npm run --prefix frontend build`
- **完了条件**: 本番ビルドが正常に完了すること。

---

## 📖 Part 5: EPUB 3 縦書き商用組版エンジンの刷新（ルビ・傍点・禁則処理・目次） (Step 49〜60)

### Step 49: 商用ライトノベル専用 縦書きCSSテンプレートの刷新
- **目的**: `writing-mode: vertical-rl`、行間、字間、フォント指定（源ノ明朝等対応）を含む商用基準CSSを策定。
- **対象ファイル**: `src/services/exporters/vertical_css_templates.py` (新規作成)
- **変更内容**:
  ```css
  html {
      writing-mode: vertical-rl;
      -webkit-writing-mode: vertical-rl;
      line-height: 1.8;
      font-family: "Hiragino Mincho ProN", "Yu Mincho", serif;
  }
  ```
- **確認コマンド**: `python -m py_compile src/services/exporters/vertical_css_templates.py`
- **完了条件**: コンパイルエラーがないこと。

### Step 50: 日本語ルビ記法パーサーの商用規格化
- **目的**: `｜親文字《るび》` および `二重山括弧`、自動検出（漢字直後のひらがな括弧）を XHTML `<ruby>親文字<rt>るび</rt></ruby>` に完全変換。
- **対象ファイル**: `src/services/exporters/ruby_parser.py` (新規作成)
- **確認コマンド**: `python -c "from src.services.exporters.ruby_parser import convert_ruby_to_xhtml; res = convert_ruby_to_xhtml('｜魔導《まどう》'); assert '<rt>まどう</rt>' in res; print('OK')"`
- **完了条件**: ルビタグ変換が正しく機能すること。

### Step 51: 傍点（圏点・ごま点）記法のサポート (`《《強調》》`)
- **目的**: ライトノベルで多用される傍点を XHTML `<span class="bouten">強調</span>` および CSS `text-emphasis-style: sesame;` へ変換。
- **対象ファイル**: `src/services/exporters/ruby_parser.py`
- **確認コマンド**: `python -m py_compile src/services/exporters/ruby_parser.py`
- **完了条件**: 傍点パーサーが追加されていること。

### Step 52: 縦中横（Tate-chu-yoko）処理の実装（2桁半角数字・記号）
- **目的**: 縦書き本文中の「10」「99」「!?」などの2桁数字・感嘆符を横書きにする `<span class="tcy">10</span>` の自動適用。
- **対象ファイル**: `src/services/exporters/tcy_formatter.py` (新規作成)
- **確認コマンド**: `python -c "from src.services.exporters.tcy_formatter import apply_tatechuyoko; res = apply_tatechuyoko('第12話'); assert 'class=\"tcy\">12<' in res; print('OK')"`
- **完了条件**: 縦中横変換が正しく動作すること。

### Step 53: 日本語約物禁則処理（行頭・行末禁則）のCSS適用
- **目的**: 句読点（、。）や閉じかぎ括弧（」）が行頭に来ないよう、`line-break: strict;` および `word-break: normal;` を適用。
- **対象ファイル**: `src/services/exporters/vertical_css_templates.py`
- **確認コマンド**: `python -m py_compile src/services/exporters/vertical_css_templates.py`
- **完了条件**: 禁則処理CSSが定義されていること。

### Step 54: EPUB 3 ナビゲーション文書 (`nav.xhtml`) および 目次 (`toc.ncx`) の二重生成
- **目的**: 最新のEPUB 3規格リーダーと、古いEPUB 2 / Kindle環境の双方で正しく目次ジャンプができるよう両対応。
- **対象ファイル**: `src/services/exporters/epub_commercial_builder.py` (新規作成)
- **確認コマンド**: `python -m py_compile src/services/exporters/epub_commercial_builder.py`
- **完了条件**: ビルダーがコンパイルできること。

### Step 55: 表紙画像（Cover Image）の自動レイアウトとOPFメタデータ登録
- **目的**: `cover.xhtml` を生成し、OPFマニフェストに `properties="cover-image"` を正しく付与。
- **対象ファイル**: `src/services/exporters/epub_commercial_builder.py`
- **確認コマンド**: `python -m py_compile src/services/exporters/epub_commercial_builder.py`
- **完了条件**: 表紙レイアウト処理が実装されていること。

### Step 56: 口絵・章間挿絵の適切なページ割り（フルスクリーン見開き制御）
- **目的**: 挿絵画像が本文途中で不自然に分断されないよう、独立した画像専用ページまたは中央配置スタイルを適用。
- **対象ファイル**: `src/services/exporters/epub_commercial_builder.py`
- **確認コマンド**: `python -m py_compile src/services/exporters/epub_commercial_builder.py`
- **完了条件**: 挿絵ページ割り処理が記述されていること。

### Step 57: `ebooklib` 非依存の Pure Python ZIPベース EPUB 3 パッカーの実装
- **目的**: 外部 C 拡張や `ebooklib` がインストールされていない最小環境でも、100% EPUB 3 標準準拠のアーカイブを生成する。
- **対象ファイル**: `src/services/exporters/pure_epub_packer.py` (新規作成)
- **変更内容**: `mimetype`（無圧縮、先頭配置）の厳格なZIP書き込みと、XHTML/CSS/マニフェストの一括パッケージング。
- **確認コマンド**: `python -m py_compile src/services/exporters/pure_epub_packer.py`
- **完了条件**: パッカーがコンパイルできること。

### Step 58: APIエンドポイント `POST /api/export/ebook` の新ビルダーへの切り替え
- **目的**: 既存の簡易EPUB出力を、商用縦書き組版エンジン `EpubCommercialBuilder` へ完全移行。
- **対象ファイル**: `src/backend/routers/export.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/export.py`
- **完了条件**: エンドポイントが更新されていること。

### Step 59: EPUB 商用組版エンジンの単体テスト作成
- **目的**: ルビ、傍点、縦中横、表紙、目次を含むEPUBファイルを生成し、ZIP構造の妥当性を検証。
- **対象ファイル**: `tests/unit/test_epub_commercial.py` (新規作成)
- **確認コマンド**: `pytest tests/unit/test_epub_commercial.py -v`
- **完了条件**: 全テストが PASS すること。

### Step 60: 【Checkpoint 5】Part 5 EPUB 3 組版エンジン動作検証
- **目的**: EPUB単体テストがすべて合格することを確認。
- **確認コマンド**: `pytest tests/unit/test_epub_commercial.py -v`
- **完了条件**: すべてのテストがオールグリーンであること。

---

## 🚀 Part 6: Kindle / 電子書籍リーダー互換性検証 & 第2段階 E2E 結合テスト (Step 61〜72)

### Step 61: EPUB バリデータ互換チェッカースクリプトの作成
- **目的**: 生成されたEPUBファイルのXML整形式、MIMEタイプ順序、メタデータ必須項目を自己診断するスクリプトを作成。
- **対象ファイル**: `scripts/validate_epub_commercial.py` (新規作成)
- **確認コマンド**: `python scripts/validate_epub_commercial.py --help`
- **完了条件**: ヘルプが表示されること。

### Step 62: Kindle（MOBI / KFX 変換）準拠のメタデータ（ASIN/UUID・言語コード）の最適化
- **目的**: Amazon Kindle Direct Publishing (KDP) にアップロードした際に警告が出ないよう `<dc:language>ja</dc:language>` 等のメタデータを最適化。
- **対象ファイル**: `src/services/exporters/epub_commercial_builder.py`
- **確認コマンド**: `python -m py_compile src/services/exporters/epub_commercial_builder.py`
- **完了条件**: メタデータが最適化されていること。

### Step 63: PDF 縦書きエクスポートの商用フォント埋め込み対応
- **目的**: PDF出力時、文字化けを防ぐためオープンソース日本語フォントを埋め込むスタイルシートを調整。
- **対象ファイル**: `src/services/exporters/pdf_exporter.py`
- **確認コマンド**: `python -m py_compile src/services/exporters/pdf_exporter.py`
- **完了条件**: コンパイルできること。

### Step 64: フロントエンド `ExportPanel.tsx` の電子書籍エクスポートUIの強化
- **目的**: 「縦書きEPUB 3（商用ライトノベル版）」「PDF（見開き版）」「ZIP（全アセット同梱）」の選択ラジオボタンとプレビュー機能を追加。
- **対象ファイル**: `frontend/src/components/ExportPanel.tsx`
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: コンポーネントが型チェックを通ること。

### Step 65: アセットパックZIP生成の並列化（画像・音声・eBookの並行ビルド）
- **目的**: 納品パッケージ生成時、複数アセットを `asyncio.gather` で並行処理し、ZIP生成時間を大幅短縮。
- **対象ファイル**: `src/services/exporters/zip_exporter.py`
- **確認コマンド**: `python -m py_compile src/services/exporters/zip_exporter.py`
- **完了条件**: 非同期並行処理が記述されていること。

### Step 66: 第2段階 包括的 E2E 結合テスト 1（画像生成パイプライン完全導通）
- **目的**: 本文生成 → シーン抽出 → プロンプト構築 → 画像生成 → アセット保存 → API取得の一気通貫テスト。
- **対象ファイル**: `tests/integration/test_phase2_illustration_e2e.py` (新規作成)
- **確認コマンド**: `pytest tests/integration/test_phase2_illustration_e2e.py -v`
- **完了条件**: E2Eテストが PASS すること。

### Step 67: 第2段階 包括的 E2E 結合テスト 2（音声合成・台詞抽出完全導通）
- **目的**: 本文生成 → セリフ分離 → 話者マッピング → 音声合成 → WAV結合 → ストリーミング再生の一気通貫テスト。
- **対象ファイル**: `tests/integration/test_phase2_audio_e2e.py` (新規作成)
- **確認コマンド**: `pytest tests/integration/test_phase2_audio_e2e.py -v`
- **完了条件**: E2Eテストが PASS すること。

### Step 68: 第2段階 包括的 E2E 結合テスト 3（商用EPUB 3 & 統合ZIP納品）
- **目的**: 本文・設定・挿絵画像・音声・EPUBを内包した完全ZIP納品パッケージの整合性テスト。
- **対象ファイル**: `tests/integration/test_phase2_deliverables_e2e.py` (新規作成)
- **確認コマンド**: `pytest tests/integration/test_phase2_deliverables_e2e.py -v`
- **完了条件**: E2Eテストが PASS すること。

### Step 69: フロントエンド & バックエンド全結合ビルド検証
- **目的**: フロントエンドの本番ビルドとバックエンドのインポート検証。
- **確認コマンド**: `npm run --prefix frontend build && python -m py_compile src/backend/server.py`
- **完了条件**: エラー0件でビルド完了すること。

### Step 70: コードベース全体のクリーンアップとフォーマット確認
- **目的**: リントおよびコードスタイル（Ruff）の検査。
- **確認コマンド**: `python -m ruff check src/ tests/ && npm run --prefix frontend lint`
- **完了条件**: リントエラー0件であること。

### Step 71: マルチモーダル機能マニュアルドキュメントの整備
- **目的**: 画像生成プロバイダ設定、VOICEVOX接続設定、EPUB縦書き設定の利用ガイドを整備。
- **対象ファイル**: `docs/multimedia.md`
- **確認コマンド**: `python -c "from pathlib import Path; assert Path('docs/multimedia.md').exists(); print('OK')"`
- **完了条件**: ドキュメントが存在すること。

### Step 72: 【Final Gate】第2段階 完了総合検証（100% ALL GREEN）
- **目的**: 第2段階で追加・改修された全テストスイートおよび既存の基幹テストを一括実行し、回帰がないことを確認。
- **確認コマンド**: `pytest tests/unit/test_image_clients.py tests/integration/test_illustration_pipeline.py tests/unit/test_voicevox_pipeline.py tests/unit/test_epub_commercial.py tests/integration/test_phase2_illustration_e2e.py tests/integration/test_phase2_audio_e2e.py tests/integration/test_phase2_deliverables_e2e.py -v -o "addopts="`
- **完了条件**: すべてのテストがオールグリーン（ALL GREEN）であること。
