# 未完了残余タスク集約型 72ステップ詳細実装計画書
## （VOICEVOX音声合成基盤・商用縦書きEPUB 3組版刷新・マルチモーダル統合UI・三段階包括的E2E結合検証）

- **策定日**: 2026年9月11日
- **対象バージョン**: AutoNovel v4.8.2+
- **設計方針**: 低性能なLLMでも迷わず1ステップずつ確実に実装・検証できるよう、最小単位の作業（単一モジュール作成・単一関数追加・単一テスト作成）に分割。すべてのステップに対象ファイル、具体的コード/仕様、確認コマンド、完了条件を明記。12ステップごとに動作検証ゲート（Checkpoint）を設置。
- **総ステップ数**: 全72ステップ（6パート × 12ステップ）

---

## 📋 パート別構成概要

| パート | ステップ | テーマ | 主な対象ファイル | 目的 |
|---|---|---|---|---|
| **Part 1** | Step 1〜12 | VOICEVOX音声合成エンジンのローカル/リモートAPI接続 & セリフ抽出基盤 | `src/services/audio/base.py`<br>`src/services/audio/voicevox_client.py`<br>`src/services/audio/dialogue_extractor.py`<br>`tests/unit/test_voicevox_pipeline.py` | 小説本文から台詞・地の文を自動抽出してVOICEVOX API経由でWAV音声を合成するバックエンド基盤を確立 |
| **Part 2** | Step 13〜24 | 音声ファイル永続化・通し朗読結合・非同期タスク & 配信API | `src/services/audio/audio_storage.py`<br>`src/services/audio/audio_combiner.py`<br>`src/backend/routers/multimedia.py`<br>`src/backend/tasks/multimedia_tasks.py` | 複数音声クリップを章ごとの通し朗読WAVへ結合、ストレージ保存、ストリーミング配信エンドポイントを整備 |
| **Part 3** | Step 25〜36 | フロントエンド音声試聴プレイヤー & アセットパックUI統合 | `frontend/src/types/multimedia.ts`<br>`frontend/src/components/common/AudioPlayer.tsx`<br>`frontend/src/components/AssetPackPanel.tsx`<br>`frontend/src/components/editor/Editor.tsx` | 生成された章朗読音声の再生、シーク、音量調整、納品パッケージZIPへの音声自動同梱UIを実装 |
| **Part 4** | Step 37〜48 | 商用ライトノベル専用 EPUB 3 縦書き組版エンジン刷新（ルビ・傍点・縦中横・禁則） | `src/services/exporters/vertical_css_templates.py`<br>`src/services/exporters/ruby_parser.py`<br>`src/services/exporters/tcy_formatter.py`<br>`src/services/exporters/epub_commercial_builder.py` | `writing-mode: vertical-rl`、`｜漢字《ルビ》`、傍点、縦中横（半角2桁数字）、禁則処理、目次・表紙を含む完全なEPUB 3生成器を新設 |
| **Part 5** | Step 49〜60 | `ebooklib`非依存 ZIPベースEPUBパッカー & 商用電子書籍API完全切替 | `src/services/exporters/pure_epub_packer.py`<br>`src/backend/routers/export.py`<br>`src/backend/multimedia_service.py`<br>`tests/unit/test_epub_commercial.py` | 外部C拡張や重いライブラリに頼らずPure Pythonで標準準拠のEPUBアーカイブを生成し、エクスポートAPIに直結 |
| **Part 6** | Step 61〜72 | Phase 1〜3 包括的結合・カオスレジリエンス・E2E全自動検証 | `tests/integration/test_phase1_ux_e2e.py`<br>`tests/integration/test_phase2_multimodal_e2e.py`<br>`tests/integration/test_phase3_chaos_resilience.py`<br>`scripts/health_check_complete.py` | 商用投稿予約、マルチモーダル（画像・音声・電子書籍）、LLM自律復旧・カオス耐性の三位一体E2Eテストを実行し100%パスを達成 |

---

## 🎙️ Part 1: VOICEVOX音声合成エンジンのローカル/リモートAPI接続 & セリフ抽出基盤 (Step 1〜12)

### Step 1: 音声合成クライアント抽象基底インターフェース `AudioSynthesisClient` の定義
- **目的**: VOICEVOXエンジンやテスト用モックを透過的に切り替え可能な共通抽象クラスを定義する。
- **対象ファイル**: `src/services/audio/base.py` (新規作成)
- **変更内容**:
  ```python
  from abc import ABC, abstractmethod
  from dataclasses import dataclass

  @dataclass
  class AudioSynthesisRequest:
      text: str
      speaker_id: int = 3  # デフォルト: ずんだもん(ノーマル)または四国めたん
      speed_scale: float = 1.0
      pitch_scale: float = 0.0
      intonation_scale: float = 1.0

  @dataclass
  class AudioSynthesisResult:
      audio_bytes: bytes
      format: str = "wav"
      duration_seconds: float = 0.0
      sample_rate: int = 24000

  class AudioSynthesisClient(ABC):
      @abstractmethod
      async def synthesize(self, req: AudioSynthesisRequest) -> AudioSynthesisResult:
          pass
  ```
- **確認コマンド**: `python -c "from src.services.audio.base import AudioSynthesisClient; print('OK')"`
- **完了条件**: クラス定義がエラーなくインポートできること。

### Step 2: オフライン・テスト用モック音声クライアント `MockAudioSynthesisClient` の実装
- **目的**: VOICEVOXサーバーが起動していない環境やCI/CDテスト時に、ダミーの有効なWAVバイナリをオンメモリ生成して返すクライアントを作成する。
- **対象ファイル**: `src/services/audio/mock_client.py` (新規作成)
- **変更内容**: 標準ライブラリ `wave` と `io.BytesIO` を用い、指定秒数（デフォルト0.5秒）の無音WAVヘッダー付きバイナリを生成して `AudioSynthesisResult` として返却する。
- **確認コマンド**: `python -c "from src.services.audio.mock_client import MockAudioSynthesisClient; import asyncio; c = MockAudioSynthesisClient(); res = asyncio.run(c.synthesize(None)); assert len(res.audio_bytes) > 44; print('OK')"`
- **完了条件**: WAVヘッダーを含むバイナリが生成されPASSすること。

### Step 3: VOICEVOX HTTP APIクライアント `VoicevoxClient` の実装
- **目的**: ローカルまたはリモートのVOICEVOXエンジン（デフォルト: `http://localhost:50021`）の `POST /audio_query` および `POST /synthesis` に接続する非同期クライアントを作成する。
- **対象ファイル**: `src/services/audio/voicevox_client.py` (新規作成)
- **変更内容**:
  ```python
  import httpx
  from src.services.audio.base import AudioSynthesisClient, AudioSynthesisRequest, AudioSynthesisResult

  class VoicevoxClient(AudioSynthesisClient):
      def __init__(self, base_url: str = "http://localhost:50021", timeout: float = 30.0):
          self.base_url = base_url.rstrip("/")
          self.timeout = timeout

      async def synthesize(self, req: AudioSynthesisRequest) -> AudioSynthesisResult:
          async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
              query_res = await client.post("/audio_query", params={"text": req.text, "speaker": req.speaker_id})
              query_res.raise_for_status()
              query_data = query_res.json()
              query_data["speedScale"] = req.speed_scale
              query_data["pitchScale"] = req.pitch_scale
              query_data["intonationScale"] = req.intonation_scale

              synth_res = await client.post("/synthesis", params={"speaker": req.speaker_id}, json=query_data)
              synth_res.raise_for_status()
              audio_bytes = synth_res.content
              return AudioSynthesisResult(audio_bytes=audio_bytes, format="wav", sample_rate=24000)
  ```
- **確認コマンド**: `python -m py_compile src/services/audio/voicevox_client.py`
- **完了条件**: 構文エラーがなくコンパイルできること。

### Step 4: 音声合成プロバイダファクトリ `get_audio_client()` の実装
- **目的**: 設定値（`settings.ENABLE_AUDIO_SYNTH` や環境変数）に応じて、実機 `VoicevoxClient` または `MockAudioSynthesisClient` を安全に解決する。
- **対象ファイル**: `src/services/audio/factory.py` (新規作成)
- **変更内容**: `get_audio_client(provider_type: str | None = None) -> AudioSynthesisClient` を定義。プロバイダ未指定時は設定を参照。
- **確認コマンド**: `python -c "from src.services.audio.factory import get_audio_client; c = get_audio_client('mock'); assert c is not None; print('OK')"`
- **完了条件**: ファクトリからモッククライアントが返却されること。

### Step 5: アプリケーション設定 `Settings` へのVOICEVOX接続設定追加
- **目的**: VOICEVOXのURL、デフォルト話者ID、タイムアウト値等を環境設定に追加。
- **対象ファイル**: `src/backend/config.py`
- **変更内容**:
  ```python
  VOICEVOX_URL: str = "http://localhost:50021"
  VOICEVOX_DEFAULT_SPEAKER_ID: int = 3
  VOICEVOX_TIMEOUT_SECONDS: float = 30.0
  ```
- **確認コマンド**: `python -c "from src.backend.config import settings; print(settings.VOICEVOX_URL)"`
- **完了条件**: デフォルト設定が読み込めること。

### Step 6: セリフ・地の文パース用データ構造 `DialogueLine` の定義
- **目的**: 小説本文から抽出された発話行、話者属性、行番号を保持するデータモデルを定義する。
- **対象ファイル**: `src/services/audio/dialogue_extractor.py` (新規作成)
- **変更内容**:
  ```python
  from dataclasses import dataclass

  @dataclass
  class DialogueLine:
      line_index: int
      text: str
      is_dialogue: bool
      speaker_name: str  # キャラクター名または "narration"
      speaker_id: int = 3
  ```
- **確認コマンド**: `python -c "from src.services.audio.dialogue_extractor import DialogueLine; d = DialogueLine(0, 'テスト', False, 'narration'); print('OK')"`
- **完了条件**: データクラスがインポートできること。

### Step 7: 本文抽出パーサー `DialogueExtractor` の基本実装
- **目的**: かぎ括弧「……」および『……』で囲まれた部分をセリフとして抽出し、それ以外をナレーション（地の文）として行単位に分解する。
- **対象ファイル**: `src/services/audio/dialogue_extractor.py`
- **変更内容**: `extract_lines(chapter_text: str) -> list[DialogueLine]` メソッドを正規表現を用いて実装。
- **確認コマンド**: `python -c "from src.services.audio.dialogue_extractor import DialogueExtractor; lines = DialogueExtractor().extract_lines('「こんにちは」と彼は言った。'); assert len(lines) >= 2; print('OK')"`
- **完了条件**: セリフと地の文が正しく分解されること。

### Step 8: 直前・直後の文脈からの発話者推定（Speaker Resolution）の実装
- **目的**: 「〜〜」とアイリスは微笑んだ。などの直前・直後文脈から、地の文に含まれる登場人物名をマッチングして `speaker_name` を自動解決する。
- **対象ファイル**: `src/services/audio/dialogue_extractor.py`
- **変更内容**: キャラクター一覧 `character_names: list[str]` を引数に取り、発話者名を推定する補助ロジックを追加。
- **確認コマンド**: `python -c "from src.services.audio.dialogue_extractor import DialogueExtractor; lines = DialogueExtractor().extract_lines('「行くわよ」とアリスが叫んだ。', characters=['アリス']); assert lines[0].speaker_name == 'アリス'; print('OK')"`
- **完了条件**: キャラクター名が発話者として設定されること。

### Step 9: キャラクター属性・性別に応じたVOICEVOX話者IDマッパーの実装
- **目的**: 「アリス（女性・活発）」「魔王（男性・重低音）」「ナレーション」にそれぞれ適切なVOICEVOX Speaker ID（四国めたん、ずんだもん、青山龍星等）を割り当てる。
- **対象ファイル**: `src/services/audio/speaker_mapper.py` (新規作成)
- **変更内容**: `assign_speaker_id(speaker_name: str, gender: str = "female", role: str = "heroine") -> int` のマッピング関数を実装。
- **確認コマンド**: `python -c "from src.services.audio.speaker_mapper import assign_speaker_id; assert isinstance(assign_speaker_id('ナレーション', role='narrator'), int); print('OK')"`
- **完了条件**: 整数型の話者IDが返されること。

### Step 10: 音声合成リクエストの自動分割（長文バッファオーバーフロー防止）
- **目的**: VOICEVOXは極端に長い文（300文字超）でエラーとなるため、句読点（。、！？）単位で安全に分割して合成キューに投入する機構を実装。
- **対象ファイル**: `src/services/audio/dialogue_extractor.py`
- **変更内容**: `split_long_sentence(text: str, max_length: int = 120) -> list[str]` を追加。
- **確認コマンド**: `python -c "from src.services.audio.dialogue_extractor import split_long_sentence; parts = split_long_sentence('長い文。' * 20, max_length=50); assert all(len(p) <= 60 for p in parts); print('OK')"`
- **完了条件**: 長文が句読点境界で適切に分割されること。

### Step 11: VOICEVOXパイプライン単体テストの作成
- **目的**: モッククライアント、セリフパーサー、話者マッピングの連携を包括検証する。
- **対象ファイル**: `tests/unit/test_voicevox_pipeline.py` (新規作成)
- **変更内容**: 発話抽出テスト、話者解決テスト、モック音声生成テストを実装。
- **確認コマンド**: `python -c "import tests.unit.test_voicevox_pipeline; print('OK')"`
- **完了条件**: テストモジュールがインポート可能であること。

### Step 12: 【Checkpoint 1】Part 1 音声合成基盤の動作検証
- **目的**: Part 1で追加されたすべてのモジュールが正常に動作し、テストがPASSすることを確認。
- **確認コマンド**: `python -c "from src.services.audio.factory import get_audio_client; from src.services.audio.dialogue_extractor import DialogueExtractor; import asyncio; c = get_audio_client('mock'); res = asyncio.run(c.synthesize(None)); print('Part 1 Checkpoint PASS')"`
- **完了条件**: `Part 1 Checkpoint PASS` が標準出力されること。

---

## 💾 Part 2: 音声ファイル永続化・通し朗読結合・非同期タスク & 配信API (Step 13〜24)

### Step 13: 音声ファイルストレージ管理クラス `AudioStorageService` の実装
- **目的**: 生成されたWAVクリップを `storage/multimedia/audio/{book_id}/ep_{num}_{line_idx}.wav` に保存・管理する。
- **対象ファイル**: `src/services/audio/audio_storage.py` (新規作成)
- **変更内容**: `save_audio_clip(book_id: int, episode: int, line_index: int, audio_bytes: bytes) -> str` および `get_audio_clip_path` メソッド。
- **確認コマンド**: `python -m py_compile src/services/audio/audio_storage.py`
- **完了条件**: コンパイルエラーがないこと。

### Step 14: Pure Python WAV結合モジュール `AudioCombiner` の実装
- **目的**: 外部コマンド（ffmpeg）や重いライブラリ（pydub）に依存せず、標準ライブラリ `wave` だけで複数WAVクリップ間に無音ポーズ（セリフ間0.4秒、段落間0.8秒）を挿入して1本の通し朗読WAVに結合する。
- **対象ファイル**: `src/services/audio/audio_combiner.py` (新規作成)
- **変更内容**:
  ```python
  import io
  import wave

  class AudioCombiner:
      @staticmethod
      def combine_wav_clips(clips: list[bytes], silence_duration_sec: float = 0.4) -> bytes:
          if not clips:
              return b""
          out_buf = io.BytesIO()
          # 1つ目のWAVからパラメータ取得
          with wave.open(io.BytesIO(clips[0]), 'rb') as first_wav:
              params = first_wav.getparams()
              nchannels, sampwidth, framerate = params.nchannels, params.sampwidth, params.framerate

          silence_frames = int(framerate * silence_duration_sec)
          silence_data = b'\x00' * (silence_frames * nchannels * sampwidth)

          with wave.open(out_buf, 'wb') as out_wav:
              out_wav.setparams(params)
              for i, clip in enumerate(clips):
                  with wave.open(io.BytesIO(clip), 'rb') as in_wav:
                      out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))
                  if i < len(clips) - 1:
                      out_wav.writeframes(silence_data)
          return out_buf.getvalue()
  ```
- **確認コマンド**: `python -c "from src.services.audio.audio_combiner import AudioCombiner; print('OK')"`
- **完了条件**: クラスが定義されインポートできること。

### Step 15: 通し朗読音声生成オーケストレータ `ChapterAudioSynthesizer` の実装
- **目的**: 1章分のテキストを受け取り、`DialogueExtractor` ➔ `AudioSynthesisClient`（並行または直列合成） ➔ `AudioCombiner` ➔ `AudioStorageService` の一連の処理を実行。
- **対象ファイル**: `src/services/audio/chapter_synthesizer.py` (新規作成)
- **変更内容**: `synthesize_chapter(book_id: int, episode_num: int, text: str, client: AudioSynthesisClient) -> str`（生成ファイルのフルパスを返却）。
- **確認コマンド**: `python -m py_compile src/services/audio/chapter_synthesizer.py`
- **完了条件**: 構文エラーがないこと。

### Step 16: 音声アセットメタデータDBモデル `AudioAssetModel` の新設
- **目的**: 生成された朗読音声のファイルパス、章番号、再生時間、ファイルサイズをDBに永続化する。
- **対象ファイル**: `src/backend/database/models.py`
- **変更内容**:
  ```python
  class AudioAssetModel(Base):
      __tablename__ = "audio_assets"
      id = Column(Integer, primary_key=True, autoincrement=True)
      book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
      episode_num = Column(Integer, nullable=False)
      file_path = Column(String(500), nullable=False)
      duration_seconds = Column(Float, nullable=False, default=0.0)
      file_size_bytes = Column(Integer, nullable=False, default=0)
      created_at = Column(DateTime, default=datetime.utcnow)
  ```
- **確認コマンド**: `python -c "from src.backend.database.models import AudioAssetModel; print(AudioAssetModel.__tablename__)"`
- **完了条件**: `audio_assets` が正常に出力されること。

### Step 17: Alembicマイグレーションスクリプト作成 (`0026_audio_assets.py`)
- **目的**: `audio_assets` テーブルを作成するためのマイグレーションファイルを生成。
- **対象ファイル**: `src/backend/alembic/versions/0026_audio_assets.py` (新規作成)
- **確認コマンド**: `python -m py_compile src/backend/alembic/versions/0026_audio_assets.py`
- **完了条件**: コンパイルエラーがないこと。

### Step 18: Huey非同期タスク `synthesize_chapter_audio_task` の新設
- **目的**: 音声合成処理をFastAPIイベントループから分離し、バックグラウンドワーカーで実行する。
- **対象ファイル**: `src/backend/tasks/multimedia_tasks.py` (新規作成)
- **変更内容**: `@huey.task()` デコレータを付与し、完了時に EventBus へ `audio.completed` イベントを発行。
- **確認コマンド**: `python -m py_compile src/backend/tasks/multimedia_tasks.py`
- **完了条件**: タスク関数が定義されていること。

### Step 19: 音声合成ジョブ投入API `POST /multimedia/audio/synthesize` の実装
- **目的**: 指定章の音声合成タスクをキューイングするAPIエンドポイントを公開。
- **対象ファイル**: `src/backend/routers/multimedia.py`
- **変更内容**: `book_id`, `episode_num` を受け取り、`synthesize_chapter_audio_task` をディスパッチ。
- **確認コマンド**: `python -m py_compile src/backend/routers/multimedia.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 20: 音声バイナリストリーミング配信API `GET /multimedia/audio/{audio_id}/stream` の実装
- **目的**: ブラウザのHTML5 `<audio>` タグで再生可能な `media_type="audio/wav"` のストリーミングレスポンスを返却。
- **対象ファイル**: `src/backend/routers/multimedia.py`
- **変更内容**: Rangeヘッダーをサポートするか、または `FileResponse` で安全に部分コンテンツ配信。
- **確認コマンド**: `python -m py_compile src/backend/routers/multimedia.py`
- **完了条件**: 配信エンドポイントがコンパイルできること。

### Step 21: 作品・章ごとの音声アセット取得API `GET /multimedia/audio/{book_id}/{episode_num}` の追加
- **目的**: 該当章に生成済み音声が存在するかどうか、存在する場合は再生URLと再生時間を返却。
- **対象ファイル**: `src/backend/routers/multimedia.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/multimedia.py`
- **完了条件**: エンドポイントが追加されていること。

### Step 22: `MultimediaService` への音声アセット統合
- **目的**: `MultimediaService.get_artifacts_by_book()` に `audio` 成果物を含めるよう拡張。
- **対象ファイル**: `src/backend/multimedia_service.py`
- **変更内容**: DBの `audio_assets` をクエリして成果物一覧にマージ。
- **確認コマンド**: `python -m py_compile src/backend/multimedia_service.py`
- **完了条件**: サービスが正常にコンパイルできること。

### Step 23: 音声永続化・結合機能の単体テスト作成
- **目的**: モックWAVの連結処理、無音挿入、ファイル保存、DBメタデータ記録をテスト。
- **対象ファイル**: `tests/unit/test_audio_storage_combiner.py` (新規作成)
- **確認コマンド**: `python -c "import tests.unit.test_audio_storage_combiner; print('OK')"`
- **完了条件**: テストファイルがインポートできること。

### Step 24: 【Checkpoint 2】Part 2 音声パイプライン結合動作確認
- **目的**: テキスト入力からWAV結合・保存・ストリーミングAPIまでの連携が正常に動作することを確認。
- **確認コマンド**: `python -c "from src.services.audio.audio_combiner import AudioCombiner; from src.services.audio.mock_client import MockAudioSynthesisClient; import asyncio; c = MockAudioSynthesisClient(); r1 = asyncio.run(c.synthesize(None)); r2 = asyncio.run(c.synthesize(None)); combined = AudioCombiner.combine_wav_clips([r1.audio_bytes, r2.audio_bytes]); assert len(combined) > len(r1.audio_bytes); print('Part 2 Checkpoint PASS')"`
- **完了条件**: `Part 2 Checkpoint PASS` が標準出力されること。

---

## 🎨 Part 3: フロントエンド音声試聴プレイヤー & アセットパックUI統合 (Step 25〜36)

### Step 25: フロントエンド音声アセット型定義 `AudioTrackInfo` の追加
- **目的**: 音声アセット情報、再生状態、合成リクエスト用のTypeScriptインターフェースを定義。
- **対象ファイル**: `frontend/src/types/multimedia.ts`
- **変更内容**:
  ```typescript
  export interface AudioTrackInfo {
    audio_id: number;
    book_id: number;
    episode_num: number;
    duration_seconds: number;
    stream_url: string;
    created_at: string;
  }
  ```
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: 型チェックがエラーなく通ること。

### Step 26: 音声合成・取得用APIクライアント関数の実装
- **目的**: 音声合成ジョブの投入、進捗取得、ストリーミングURL解決を行うAPI関数を作成。
- **対象ファイル**: `frontend/src/api/audio.ts` (新規作成)
- **変更内容**: `fetchChapterAudio(bookId, epNum)`, `triggerAudioSynthesis(bookId, epNum)`。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: 関数がエクスポートされ型エラーがないこと。

### Step 27: 共通オーディオプレイヤーコンポーネント `AudioPlayer.tsx` の新設
- **目的**: 再生/一時停止ボタン、シークバー（再生位置）、音量スライダー、再生速度変更（1.0x / 1.25x / 1.5x）を備えたスタイリッシュなミニプレイヤーを作成。
- **対象ファイル**: `frontend/src/components/common/AudioPlayer.tsx` (新規作成)
- **変更内容**: HTML5 `<audio>` 要素をReactの状態（`currentTime`, `duration`, `isPlaying`）とバインド。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: コンポーネントが型チェックを通過すること。

### Step 28: `AudioPlayer.tsx` のCSSスタイリング（ダークモード調・レスポンシブ）
- **目的**: プレミアム感のあるオーディオコントロールUIをスタイリング。
- **対象ファイル**: `frontend/src/components/common/AudioPlayer.css` (新規作成)
- **確認コマンド**: `npm run --prefix frontend build`
- **完了条件**: ビルドエラーがないこと。

### Step 29: アセットパック管理パネル `AssetPackPanel.tsx` への「オーディオ朗読」チェックボックス追加
- **目的**: ZIP納品パッケージ生成時に「章朗読音声（WAV）を含める」オプションを選択可能にする。
- **対象ファイル**: `frontend/src/components/AssetPackPanel.tsx`
- **変更内容**: `includeAudio` ステートとトグルスイッチを追加。
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: 型チェックが通過すること。

### Step 30: `AssetPackPanel.tsx` 内への「生成済み音声試聴セクション」追加
- **目的**: 生成された章朗読音声をパネル内で即座に試聴・ダウンロードできるリストUIを配置。
- **対象ファイル**: `frontend/src/components/AssetPackPanel.tsx`
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: リストと `AudioPlayer` が正常に配置されること。

### Step 31: 納品ZIP生成サービスへの音声ファイル同梱ロジックの追加
- **目的**: `MultimediaService.generate_asset_pack` 内で、音声ファイルが存在する場合にZIP内の `05_音声/` フォルダへ自動格納。
- **対象ファイル**: `src/backend/multimedia_service.py`
- **変更内容**: `include_audio` パラメータの追加とZIPアーカイブへの書き込み処理。
- **確認コマンド**: `python -m py_compile src/backend/multimedia_service.py`
- **完了条件**: コンパイルできること。

### Step 32: Studioエディタツールバー `InlineAiToolbar.tsx` への「音声朗読生成」ボタン追加
- **目的**: 執筆中の章を1クリックで「🔊 音声朗読を合成」できるトリガーをエディタ上部に配置。
- **対象ファイル**: `frontend/src/components/editor/InlineAiToolbar.tsx`
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: ツールバーにボタンが追加されていること。

### Step 33: Studioエディタ本文フッターへの「インライン音声プレイヤー」の埋め込み
- **目的**: 当該章の音声が生成済みの場合、エディタ下部にミニプレイヤーが自動出現し、執筆しながら耳で校正できるようにする。
- **対象ファイル**: `frontend/src/components/editor/Editor.tsx`
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: エディタコンポーネントが型チェックを通ること。

### Step 34: 音声合成進行中のリアルタイムトースト通知とローディング表示
- **目的**: 合成開始、完了、エラーをユーザーにフィードバックするトースト表示とスピナーUIを追加。
- **対象ファイル**: `frontend/src/hooks/useChapterAudio.ts` (新規作成)
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: カスタムフックが作成されること。

### Step 35: フロントエンドオーディオプレイヤーの単体テスト作成
- **目的**: `AudioPlayer.tsx` の再生トグル、速度変更、レンダリングをテスト。
- **対象ファイル**: `frontend/tests/components/AudioPlayer.test.tsx` (新規作成)
- **確認コマンド**: `npm run --prefix frontend test -- tests/components/AudioPlayer.test.tsx`
- **完了条件**: テストがPASSすること。

### Step 36: 【Checkpoint 3】Part 3 フロントエンド音声UIビルド検証
- **目的**: フロントエンド全体の型チェックと本番ビルドがエラー0件であることを確認。
- **確認コマンド**: `npm run --prefix frontend typecheck && npm run --prefix frontend build`
- **完了条件**: ビルドが正常に完了すること。

---

## 📖 Part 4: 商用ライトノベル専用 EPUB 3 縦書き組版エンジン刷新（ルビ・傍点・縦中横・禁則） (Step 37〜48)

### Step 37: 商用縦書き専用CSSテンプレート `vertical_css_templates.py` の新設
- **目的**: `writing-mode: vertical-rl;`、行間、字間、フォントファミリ（明朝体優先）、禁則処理を含む商用ライトノベル基準のスタイルシートを定義。
- **対象ファイル**: `src/services/exporters/vertical_css_templates.py` (新規作成)
- **変更内容**:
  ```python
  VERTICAL_EPUB_CSS = """
  @charset "utf-8";
  html {
      writing-mode: vertical-rl;
      -webkit-writing-mode: vertical-rl;
      line-break: strict;
      word-break: normal;
  }
  body {
      font-family: "Hiragino Mincho ProN", "Yu Mincho", "Noto Serif CJK JP", serif;
      font-size: 100%;
      line-height: 1.85;
      margin: 0;
      padding: 0;
  }
  p {
      text-indent: 1em;
      margin: 0;
      padding: 0;
  }
  p.dialogue {
      text-indent: 0;
  }
  ruby rt {
      font-size: 0.5em;
  }
  .bouten {
      text-emphasis-style: sesame;
      -webkit-text-emphasis-style: sesame;
  }
  .tcy {
      text-combine-upright: all;
      -webkit-text-combine: horizontal;
  }
  """
  ```
- **確認コマンド**: `python -c "from src.services.exporters.vertical_css_templates import VERTICAL_EPUB_CSS; assert 'vertical-rl' in VERTICAL_EPUB_CSS; print('OK')"`
- **完了条件**: CSS文字列がインポートできること。

### Step 38: 日本語ルビ記法パーサー `RubyParser` の実装
- **目的**: カクヨム・なろう標準の `｜親文字《るび》`、および `親文字《るび》`（漢字+山括弧）を XHTML `<ruby>親文字<rt>るび</rt></ruby>` に完全変換する。
- **対象ファイル**: `src/services/exporters/ruby_parser.py` (新規作成)
- **変更内容**: 正規表現 `r"｜([^《]+)《([^》]+)》"` および漢字直結ルビ `r"([一-龠々]+)《([^》]+)》"` を変換する関数 `parse_ruby_to_xhtml(text: str) -> str`。
- **確認コマンド**: `python -c "from src.services.exporters.ruby_parser import parse_ruby_to_xhtml; res = parse_ruby_to_xhtml('｜魔導《まどう》'); assert '<ruby>魔導<rt>まどう</rt></ruby>' in res; print('OK')"`
- **完了条件**: ルビタグ変換がPASSすること。

### Step 39: 傍点（圏点・ごま点）記法パーサーの実装
- **目的**: ライトノベルで多用される強調構文 `《《強調文字》》` を `<span class="bouten">強調文字</span>` に変換する。
- **対象ファイル**: `src/services/exporters/ruby_parser.py`
- **変更内容**: `parse_bouten(text: str) -> str` を追加。
- **確認コマンド**: `python -c "from src.services.exporters.ruby_parser import parse_bouten; res = parse_bouten('《《絶対》》'); assert 'class=\"bouten\">絶対<' in res; print('OK')"`
- **完了条件**: 傍点クラスへの変換が正常に動作すること。

### Step 40: 縦中横（Tate-chu-yoko）自動整形モジュール `TCYFormatter` の実装
- **目的**: 縦書き本文中の2桁以内の半角数字（`10`, `99`）および感嘆符（`!?`, `!!`）を横書きにする `<span class="tcy">10</span>` を自動適用する。
- **対象ファイル**: `src/services/exporters/tcy_formatter.py` (新規作成)
- **変更内容**: `apply_tatechuyoko(text: str) -> str` の正規表現置換（3桁以上の数字は漢数字変換またはそのまま維持）。
- **確認コマンド**: `python -c "from src.services.exporters.tcy_formatter import apply_tatechuyoko; res = apply_tatechuyoko('第12話!?'); assert 'class=\"tcy\">12<' in res and 'class=\"tcy\">!?<' in res; print('OK')"`
- **完了条件**: 縦中横タグが正しく付与されること。

### Step 41: 日本語約物・禁則処理および全角三点リーダー等の正規化
- **目的**: 三点リーダー（……）やダッシュ（――）が中途半端な点にならないよう偶数個に揃え、行頭の閉じ括弧を回避する事前正規化関数を実装。
- **対象ファイル**: `src/services/exporters/text_sanitizer.py` (新規作成)
- **確認コマンド**: `python -m py_compile src/services/exporters/text_sanitizer.py`
- **完了条件**: 構文エラーがないこと。

### Step 42: XHTMLエピソード本文ジェネレータの実装
- **目的**: 1話分のテキストに対し、エスケープ ➔ ルビ ➔ 傍点 ➔ 縦中横 ➔ 段落 `<p>` タグ化を施し、完全なXHTML（`item/xhtml/p-001.xhtml`）文字列を構築。
- **対象ファイル**: `src/services/exporters/epub_content_builder.py` (新規作成)
- **確認コマンド**: `python -m py_compile src/services/exporters/epub_content_builder.py`
- **完了条件**: ジェネレータがコンパイルできること。

### Step 43: EPUB 3 ナビゲーション文書 (`nav.xhtml`) の自動生成
- **目的**: EPUB 3規格準拠の `<nav epub:type="toc">` を含むナビゲーション文書を生成し、電子書籍リーダーでの目次ジャンプを可能にする。
- **対象ファイル**: `src/services/exporters/epub_manifest_builder.py` (新規作成)
- **確認コマンド**: `python -m py_compile src/services/exporters/epub_manifest_builder.py`
- **完了条件**: コンパイルエラーがないこと。

### Step 44: 旧規格互換用 NCX 目次 (`toc.ncx`) の二重生成
- **目的**: EPUB 2リーダーや古いKindle環境でも目次が壊れないよう、NCXファイルを同時出力して互換性を担保する。
- **対象ファイル**: `src/services/exporters/epub_manifest_builder.py`
- **確認コマンド**: `python -m py_compile src/services/exporters/epub_manifest_builder.py`
- **完了条件**: NCXビルダーがコンパイルできること。

### Step 45: 表紙ページ (`cover.xhtml`) の自動レイアウトとOPF登録
- **目的**: `cover.xhtml` を生成し、OPFマニフェストに `properties="cover-image"` を付与してKindleやiBooksで表紙が正しく認識されるようにする。
- **対象ファイル**: `src/services/exporters/epub_manifest_builder.py`
- **確認コマンド**: `python -m py_compile src/services/exporters/epub_manifest_builder.py`
- **完了条件**: 表紙メタデータ処理が実装されていること。

### Step 46: 口絵・章間挿絵の専用見開きレイアウト
- **目的**: 生成されたAI挿絵画像を本文途中で不自然に分断させず、独立したフルスクリーン画像ページ（`svg` 埋め込み）としてレンダリングする。
- **対象ファイル**: `src/services/exporters/epub_content_builder.py`
- **確認コマンド**: `python -m py_compile src/services/exporters/epub_content_builder.py`
- **完了条件**: 挿絵用XHTML生成ロジックが追加されていること。

### Step 47: ルビ・傍点・縦中横の結合単体テスト作成
- **目的**: 日本語特有の組版要素（ルビ・傍点・縦中横）が複合したテキストが妥当なXHTMLに変換されるかを検証。
- **対象ファイル**: `tests/unit/test_ruby_tcy_parsers.py` (新規作成)
- **確認コマンド**: `python -c "import tests.unit.test_ruby_tcy_parsers; print('OK')"`
- **完了条件**: テストモジュールがインポートできること。

### Step 48: 【Checkpoint 4】Part 4 縦書き組版要素のパース検証
- **目的**: ルビ、傍点、縦中横の全パーサーが期待通りに動作することを確認。
- **確認コマンド**: `python -c "from src.services.exporters.ruby_parser import parse_ruby_to_xhtml, parse_bouten; from src.services.exporters.tcy_formatter import apply_tatechuyoko; t = '｜勇者《ゆうしゃ》は《《覚醒》》し第12章へ'; t = apply_tatechuyoko(parse_bouten(parse_ruby_to_xhtml(t))); assert '<ruby>' in t and '<span class=\"bouten\">' in t and '<span class=\"tcy\">' in t; print('Part 4 Checkpoint PASS')"`
- **完了条件**: `Part 4 Checkpoint PASS` が標準出力されること。

---

## 📦 Part 5: `ebooklib`非依存 ZIPベースEPUBパッカー & 商用電子書籍API完全切替 (Step 49〜60)

### Step 49: Pure Python EPUB 3 パッカー `PureEpubPacker` の実装
- **目的**: 外部ライブラリ `ebooklib` なしで、標準ライブラリ `zipfile` を用いて厳格なEPUB規格（先頭無圧縮 `mimetype`、`META-INF/container.xml`、XHTML、CSS、画像）アーカイブを生成する。
- **対象ファイル**: `src/services/exporters/pure_epub_packer.py` (新規作成)
- **変更内容**:
  ```python
  import zipfile
  import io

  class PureEpubPacker:
      def __init__(self):
          self.entries: list[tuple[str, bytes, int]] = []  # (path, content, compress_type)

      def add_file(self, arcname: str, data: bytes, compress: bool = True):
          c_type = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
          self.entries.append((arcname, data, c_type))

      def build_epub_bytes(self) -> bytes:
          buf = io.BytesIO()
          with zipfile.ZipFile(buf, "w") as zf:
              # 1. 規格必須: mimetype は無圧縮かつ先頭
              zf.writestr("mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED)
              for path, data, c_type in self.entries:
                  if path == "mimetype":
                      continue
                  zf.writestr(path, data, compress_type=c_type)
          return buf.getvalue()
  ```
- **確認コマンド**: `python -c "from src.services.exporters.pure_epub_packer import PureEpubPacker; p = PureEpubPacker(); b = p.build_epub_bytes(); assert b.startswith(b'PK'); print('OK')"`
- **完了条件**: パッカーがZIPバイナリを返却すること。

### Step 50: `META-INF/container.xml` の標準ジェネレータ
- **目的**: OPFファイルの位置を指し示す `container.xml` を自動生成。
- **対象ファイル**: `src/services/exporters/pure_epub_packer.py`
- **確認コマンド**: `python -m py_compile src/services/exporters/pure_epub_packer.py`
- **完了条件**: コンパイルできること。

### Step 51: 商用EPUB 3 統合ビルダー `CommercialEpubBuilder` の実装
- **目的**: 書籍情報、チャプター配列、挿絵画像バイナリを受け取り、XHTML群・CSS・マニフェスト・ナビゲーションを組み立てて完全な `.epub` バイナリを出力する高水準クラス。
- **対象ファイル**: `src/services/exporters/epub_commercial_builder.py` (新規作成)
- **変更内容**: `build_commercial_epub(novel_meta: dict, chapters: list[dict], images: list[dict] | None = None) -> bytes` メソッドを実装。
- **確認コマンド**: `python -m py_compile src/services/exporters/epub_commercial_builder.py`
- **完了条件**: クラスが定義されていること。

### Step 52: Kindle準拠のメタデータ最適化（ASIN/UUID・右開き指定）
- **目的**: OPFの `spine` に `page-progression-direction="rtl"`（右開き・縦書き標準）を付与し、Amazon KDP にアップロードした際に横書きとして誤認されるのを防ぐ。
- **対象ファイル**: `src/services/exporters/epub_manifest_builder.py`
- **確認コマンド**: `python -m py_compile src/services/exporters/epub_manifest_builder.py`
- **完了条件**: 右開きメタデータが付与されていること。

### Step 53: EPUB 3 組版エンジンの単体テスト作成
- **目的**: 実際にダミー小説からEPUBバイナリを生成し、ZIP内部構造、`mimetype`、`container.xml`、XHTMLが整形式であることを検証。
- **対象ファイル**: `tests/unit/test_epub_commercial.py` (新規作成)
- **確認コマンド**: `python -c "import tests.unit.test_epub_commercial; print('OK')"`
- **完了条件**: テストモジュールがインポートできること。

### Step 54: `MultimediaService.export_ebook` の新エンジンへの切り替え
- **目的**: 従来の簡易EPUBエクスポーターから、新設した `CommercialEpubBuilder` へ委譲を切り替える。
- **対象ファイル**: `src/backend/multimedia_service.py`
- **確認コマンド**: `python -m py_compile src/backend/multimedia_service.py`
- **完了条件**: サービス層がコンパイルできること。

### Step 55: APIエンドポイント `POST /api/export/ebook` の新エンジンへの直結
- **目的**: 外部からのEPUBエクスポートAPIが商用縦書きEPUB 3を返却するように確認・更新。
- **対象ファイル**: `src/backend/routers/export.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/export.py`
- **完了条件**: ルータがコンパイルできること。

### Step 56: EPUBダウンロードエンドポイントのContent-Disposition設定
- **目的**: ブラウザからダウンロードした際に、書籍タイトルを含んだ日本語ファイル名（`{title}.epub`）で保存されるようヘッダーを最適化。
- **対象ファイル**: `src/backend/routers/export.py`
- **確認コマンド**: `python -m py_compile src/backend/routers/export.py`
- **完了条件**: ヘッダー処理が更新されていること。

### Step 57: フロントエンド `ExportPanel.tsx` への「縦書きEPUB 3」プレビュー項目の追加
- **目的**: ユーザーが電子書籍出力形式を選ぶ際、「商用縦書きEPUB 3（ルビ・傍点対応）」を明示的に選択・確認できるようにする。
- **対象ファイル**: `frontend/src/components/ExportPanel.tsx`
- **確認コマンド**: `npm run --prefix frontend typecheck`
- **完了条件**: コンポーネントが型チェックを通ること。

### Step 58: アセットパック納品ZIPへの商用EPUB 3の自動同梱
- **目的**: `POST /multimedia/asset-pack` で生成される納品ZIPの `04_電子書籍/` 配下に新エンジン生成のEPUB 3ファイルを確実に格納。
- **対象ファイル**: `src/backend/multimedia_service.py`
- **確認コマンド**: `python -m py_compile src/backend/multimedia_service.py`
- **完了条件**: ZIP格納ロジックがコンパイルできること。

### Step 59: EPUB生成パフォーマンステスト（100話一括生成のメモリ検証）
- **目的**: 100話（約30万字）の長編小説でもメモリ枯渇を起こさず、5秒以内にEPUBファイルを生成できることを検証。
- **対象ファイル**: `tests/unit/test_epub_commercial.py`
- **確認コマンド**: `python -c "from tests.unit.test_epub_commercial import test_large_book_epub_build; print('OK')"`
- **完了条件**: パフォーマンステスト関数が定義されていること。

### Step 60: 【Checkpoint 5】Part 5 EPUB 3 生成機能の完全動作確認
- **目的**: 商用EPUB 3がエラーなく生成され、ZIP解凍後のファイル構成が100% EPUB 3規格を満たすことを確認。
- **確認コマンド**: `python -c "from src.services.exporters.epub_commercial_builder import CommercialEpubBuilder; b = CommercialEpubBuilder().build_commercial_epub({'title':'テスト作','author':'AI'}, [{'title':'第1話','content':'｜魔導《まどう》覚醒。'}]); assert len(b) > 1000; print('Part 5 Checkpoint PASS')"`
- **完了条件**: `Part 5 Checkpoint PASS` が標準出力されること。

---

## 🛡️ Part 6: Phase 1〜3 包括的結合・カオスレジリエンス・E2E全自動検証 (Step 61〜72)

### Step 61: Phase 1 E2Eテスト `test_phase1_ux_e2e.py` の新設
- **目的**: 投稿スケジュール予約 ➔ ステータス一覧 ➔ 実行ワーカー ➔ BookScoreレーダーチャート ➔ IFルート分岐マージの全フローを一気通貫で検証する。
- **対象ファイル**: `tests/integration/test_phase1_ux_e2e.py` (新規作成)
- **変更内容**: `pytest-asyncio` を用いたエンドツーエンド統合テスト。
- **確認コマンド**: `python -c "import tests.integration.test_phase1_ux_e2e; print('OK')"`
- **完了条件**: テストモジュールがインポートできること。

### Step 62: Phase 2 E2Eテスト `test_phase2_multimodal_e2e.py` の新設
- **目的**: 本文執筆 ➔ シーン画像生成 ➔ VOICEVOX音声合成 ➔ 商用EPUB 3生成 ➔ 納品ZIPパッケージ化の全マルチモーダルパイプラインを結合テスト。
- **対象ファイル**: `tests/integration/test_phase2_multimodal_e2e.py` (新規作成)
- **確認コマンド**: `python -c "import tests.integration.test_phase2_multimodal_e2e; print('OK')"`
- **完了条件**: テストモジュールがインポートできること。

### Step 63: カオス障害注入ヘルパー `ChaosInjector` の新設
- **目的**: テスト中に一時的なHTTP 429（Rate Limit）、500（Server Error）、ネットワーク切断を模擬するユーティリティを作成。
- **対象ファイル**: `tests/fixtures/chaos_injector.py` (新規作成)
- **確認コマンド**: `python -c "from tests.fixtures.chaos_injector import ChaosInjector; print('OK')"`
- **完了条件**: ヘルパーがインポートできること。

### Step 64: Phase 3 カオステスト `test_phase3_chaos_resilience.py` の新設
- **目的**: LLM APIが突然死した際の代替プロバイダへの即時自動迂回（フェイルオーバー）と、ワーカー停止時のWALチェックポイント自動復帰を実証。
- **対象ファイル**: `tests/integration/test_phase3_chaos_resilience.py` (新規作成)
- **確認コマンド**: `python -c "import tests.integration.test_phase3_chaos_resilience; print('OK')"`
- **完了条件**: テストモジュールがインポートできること。

### Step 65: Phase 3 フル回帰テスト `test_phase3_full_regression.py` の新設
- **目的**: NetworkXグラフ探索、8専門オーディター動的ルーティング、コストガードによるモデルダウングレードの包括的回帰検証。
- **対象ファイル**: `tests/integration/test_phase3_full_regression.py` (新規作成)
- **確認コマンド**: `python -c "import tests.integration.test_phase3_full_regression.py; print('OK')"`
- **完了条件**: テストモジュールがインポートできること。

### Step 66: システム全機能診断スクリプト `scripts/health_check_complete.py` の新設
- **目的**: サーバー起動時に全エンドポイント（`/health`, `/metrics`, `/commercial/schedules`, `/multimedia/...`, `/api/cost/...`）の死活を自己診断するスクリプト。
- **対象ファイル**: `scripts/health_check_complete.py` (新規作成)
- **確認コマンド**: `python scripts/health_check_complete.py --help`
- **完了条件**: ヘルプが表示されること。

### Step 67: フロントエンド本番ビルド & 型チェック完全検証
- **目的**: 追加した `AudioPlayer`、アセットパックUI、EPUBエクスポートUIを含むフロントエンド全体の型整合性を検証。
- **確認コマンド**: `npm run --prefix frontend typecheck && npm run --prefix frontend build`
- **完了条件**: ビルドがエラー0件で完了すること。

### Step 68: バックエンド全モジュールの構文・インポート完全検証
- **目的**: 新規追加した全Pythonファイルに構文エラーやインポートエラーが存在しないことを検証。
- **確認コマンド**: `python -c "import src.backend.server; import src.services.audio.voicevox_client; import src.services.exporters.epub_commercial_builder; print('All Imports OK')"`
- **完了条件**: `All Imports OK` が出力されること。

### Step 69: 新機能ドキュメント `docs/MULTIMODAL_AUDIO_EPUB_GUIDE.md` の作成
- **目的**: VOICEVOXエンジンの接続手順、話者マッピングのカスタマイズ方法、商用縦書きEPUBの出力仕様をマニュアル化。
- **対象ファイル**: `docs/MULTIMODAL_AUDIO_EPUB_GUIDE.md` (新規作成)
- **確認コマンド**: `python -c "from pathlib import Path; assert Path('docs/MULTIMODAL_AUDIO_EPUB_GUIDE.md').exists(); print('OK')"`
- **完了条件**: ドキュメントが存在すること。

### Step 70: コードフォーマットと未使用インポートの自動整形
- **目的**: プロジェクト全体のコード品質を保つため、リンター（Ruff等）を実行してスタイルを標準化。
- **確認コマンド**: `python -m ruff check src/services/audio/ src/services/exporters/ tests/`
- **完了条件**: エラー0件であること。

### Step 71: 【Final Pre-Gate】新規単体・統合テストの一括実行
- **目的**: 本計画書で新設されたテスト（音声、EPUB、フェーズ1〜3結合）を一括実行。
- **確認コマンド**: `pytest tests/unit/test_voicevox_pipeline.py tests/unit/test_epub_commercial.py tests/integration/test_phase1_ux_e2e.py tests/integration/test_phase2_multimodal_e2e.py tests/integration/test_phase3_chaos_resilience.py -v`
- **完了条件**: すべてのテストが PASS すること。

### Step 72: 【Grand Final Gate】AutoNovel 全システム総合検証（100% ALL GREEN）
- **目的**: 既存の全テストスイートおよび新設テストスイートを完全実行し、リグレッションが一切ない状態でリリース可能であることを証明する。
- **確認コマンド**: `pytest tests/unit/ tests/integration/ -v -o "addopts="`
- **完了条件**: すべてのテストがオールグリーン（ALL GREEN）であること。
