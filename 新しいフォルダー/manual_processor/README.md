# 手書きマニュアル処理システム (Manual Processor)

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-win.svg)]()

スキャンされた手書きマニュアル（PDF）を読み込み、**Google Gemini API** を活用して高精度なOCR解析・初心者向けの要約および構造化を行い、**PDF**・**Word文書**・**音声ファイル(MP3)** の複数フォーマットで自動出力するWindows向けアプリケーションです。

---

## 🌟 主な機能

- 📄 **PDF画像抽出 & Multimodal Direct Processing**
  - PyMuPDF を用いてPDFを高解像度（300 DPI）画像に変換。
  - Gemini API (Multimodal) を利用し、日本語の手書き文字や英数字・図表テキストをOCR劣化なしで高精度に自動ダイレクト解析。
  - API呼び出しにリトライ機構（指数バックオフ）を搭載し、一時的なエラーに対応。
- 🧠 **AIによる要約・構造化**
  - 初心者にも直感的に理解できるよう、見出し・箇条書き・重要ポイント（要点）を自動整理。
  - Gemini 3.1 Flash Lite を採用し、高速かつ低コストで高品質な要約を実現。
- 🖨️ **マルチフォーマット出力 & QRコード連動**
  - **Word (.docx)**: 枠線付きテーブル（表）の自動描画、レイアウト整形、および文書先頭にスマホ音声再生用**QRコード**を自動埋め込み。
  - **音声 (.mp3)**: Gemini TTS / gTTS を活用し、要点・サマリーを読み上げる音声ファイルを自動生成。
  - **Google Drive / クラウド自動アップロード**: 生成された音声MP3をGoogle Drive Service Account API等経由で自動アップロードし、スマホでQRコードを読み取るだけで即座に音声解説を再生可能。
- 🔌 **USBドライブ監視 & バッチ処理**
  - USBメモリなどの接続を監視し、新規配置された手書きマニュアルPDFを自動検出・自動処理。
- 🖥️ **GUI & CLI の両対応**
  - **GUIモード**: 初心者でも使いやすい直感的なデスクトップ画面 (Tkinter)。
  - **CLIモード**: コマンドラインでの個別処理やバックグラウンド監視スクリプトとしての実行。
- 📦 **単一実行ファイル (.exe) 化対応**
  - PyInstallerを用いたワンクリックビルドで、環境構築不要のポータブルEXE (`DocumentProcessor.exe`) を作成可能。

---

## 💻 システム要件

- **OS**: Windows 10 / 11
- **Python**: Python 3.8 以上
- **API Key**: [Google AI Studio](https://aistudio.google.com/) で取得した API キー
- **Google Drive Service Account**: Google Drive への音声自動アップロード機能（オプション）
- **メモリ**: 4GB 以上推奨（大量処理時）

---

## 📦 インストール方法

1. **リポジトリの取得**
   ```bash
   git clone https://github.com/your-repo/manual_processor.git
   cd manual_processor
   ```

2. **依存ライブラリのインストール**
   ```bash
   pip install -r requirements.txt
   ```
   または開発モードでパッケージとしてインストール:
   ```bash
   pip install -e .
   ```

---

## ⚙️ 環境設定 (.env)

プロジェクトルートに `.env` ファイルを作成し、APIキーを設定してください。（`config/template.env` を参考に作成できます）

```env
# Google AI Studio APIキー（必須）
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Google Drive 音声自動アップロード設定（オプション）
GOOGLE_DRIVE_CREDENTIALS_FILE=service_account_credentials.json
GOOGLE_DRIVE_FOLDER_ID=your_gdrive_folder_id_here
AUDIO_PUBLIC_BASE_URL=https://drive.google.com/drive/folders/your_folder_id

# 出力・一時保存フォルダの設定（オプション）
OUTPUT_DIRECTORY=./output
TEMP_DIRECTORY=./temp

# 解像度・ログ設定（オプション）
PDF_DPI=300
LOG_LEVEL=INFO
```

---

## 🚀 使用方法

### 1. GUI モード（デフォルト）

GUIウィンドウを起動して、画面上でPDFの選択や処理状況の確認を行えます。

```bash
# パッケージインストール後
manual-processor

# または直接スクリプトを実行
python main.py
```

### 2. CLI モード（単一ファイルの処理）

特定の手書きマニュアルPDFファイルを即座に処理する場合:

```bash
manual-processor --cli --input C:\path\to\manual.pdf --output ./output
```

### 3. CLI モード（ファイル監視）

USBドライブや指定フォルダの監視モードで起動する場合:

```bash
manual-processor --cli
```

### 4. 単一実行ファイル (.exe) のビルド

環境構築不要な実行ファイルを作成する場合:

`build_exe.bat` をダブルクリックするか、以下のコマンドを実行します。

```bash
python build_exe.py
```

ビルドが完了すると、 `dist/DocumentProcessor.exe` にスタンドアロン実行ファイルが作成されます。

---

## 📋 コマンドライン引数一覧

| 引数 | フラグ | 説明 |
| :--- | :--- | :--- |
| `--input` | `-i` | 処理対象のPDFファイルパス |
| `--output` | `-o` | 出力先ディレクトリルート（デフォルト: `output`） |
| `--api-key` | | Google AI Studio APIキー |
| `--cli` | | CLIモードで実行 |
| `--gui` | | GUIモードで実行（デフォルト） |
| `--verbose` | `-v` | 詳細ログ（DEBUGレベル）を出力 |
| `--version` | | バージョン情報を表示 |

---

## 📂 プロジェクト構造

```text
manual_processor/
├── config/                  # 設定管理・環境変数読込
│   ├── config.py
│   └── template.env
├── src/                     # アプリケーションソースコード
│   ├── config/              # プロンプト設定・定数管理
│   │   └── prompts.py
│   ├── gui/                 # Tkinter GUI実装
│   ├── processor/           # 処理パイプライン制御
│   ├── audio_generator.py   # MP3音声生成 (Gemini TTS / gTTS)
│   ├── audio_uploader.py    # 音声ファイルアップロード制御
│   ├── docx_generator.py    # Wordドキュメント生成
│   ├── error_handler.py     # エラーハンドリングモジュール
│   ├── exceptions.py        # カスタム例外定義
│   ├── gemini_ocr.py        # Gemini API OCR処理
│   ├── gemini_processor.py  # Gemini連携共通プロセッサ
│   ├── gemini_summarizer.py # テキスト要約・構造化
│   ├── logger.py            # ログ管理
│   ├── ocr_processor.py     # OCR・画像前処理統合
│   ├── orchestrator.py      # スレッド・キュー・進捗管理
│   ├── output_manager.py    # 出力ファイル構造管理
│   ├── qr_generator.py      # QRコード生成
│   ├── text_processor.py    # テキスト整形・後処理
│   └── usb_monitor.py       # USBドライブ検出・監視
├── tests/                   # ユニットテスト・統合テスト
├── 01_system_overview.md    # システム概要仕様書
├── 02_interface_definitions.md # インターフェース仕様書
├── 03_edge_cases.md         # エッジケース・異常系仕様書
├── 04_implementation_steps.md# 実装手順・タスク一覧
├── 05_test_requirements.md  # テスト要件仕様書
├── build_exe.py             # EXEビルド用スクリプト
├── build_exe.bat            # EXEビルドバッチファイル
├── main.py                  # メインエントリーポイント
├── requirements.txt         # 依存ライブラリ一覧
└── setup.py                 # セットアップスクリプト
```

---

## 🧪 テストの実行

`pytest` を使用してユニットテストを実行できます。

```bash
# 全テストの実行
pytest

# 詳細ログを表示して実行
pytest -v
```

---

## 📄 ドキュメント

プロジェクトの詳細な仕様および開発ドキュメントは以下を参照してください。

- [システム概要](01_system_overview.md)
- [インターフェース定義](02_interface_definitions.md)
- [エッジケース設計](03_edge_cases.md)
- [実装手順・タスク一覧](04_implementation_steps.md)
- [テスト要件仕様書](05_test_requirements.md)

---

## 📝 ライセンス

このプロジェクトは MIT ライセンスのもとで公開されています。