## 2. 完全なインターフェースと型定義

### TypeScriptインターフェース定義（TypeScript使用時）
```typescript
// OCR結果インターフェース
interface OCRResult {
  text: string;                    // 認識されたテキスト
  confidence: number;              // 信頼度 (0.0-1.0)
  pageNumber: number;              // ページ番号
  boundingBoxes: BoundingBox[];    // テキストボックス座標
}

interface BoundingBox {
  x: number;                       // X座標 (0-1)
  y: number;                       // Y座標 (0-1)
  width: number;                   // 幅 (0-1)
  height: number;                  // 高さ (0-1)
}

// Gemini処理結果インターフェース
interface GeminiResult {
  summary: string;                 // 要約テキスト
  keyPoints: string[];             // 重要ポイントのリスト
  sections: Section[];             // セクション構造
  difficultyLevel: 'beginner' | 'intermediate' | 'advanced';
}

interface Section {
  title: string;
  content: string;
  subsections?: Section[];
}

// 出力ファイルインターフェース
interface OutputFiles {
  pdfPath: string;                 // PDF出力パス
  docxPath: string;                // Word出力パス
  audioPath: string;               // 音声出力パス
  metadata: {
    sourceFile: string;            // 元ファイルパス
    processedAt: Date;             // 処理日時
    pageCount: number;             // ページ数
    wordCount: number;             // 語数
  }
}

// USB監視イベントインターフェース
interface USBFileEvent {
  type: 'created' | 'modified' | 'deleted';
  filePath: string;                // 完全パス
  fileName: string;                // ファイル名
  timestamp: Date;                 // イベントタイムスタンプ
}
```

### Python型定義（実際の実装ではこちらを使用）
```python
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass
class BoundingBox:
    x: float  # 0-1 normalized coordinates
    y: float  # 0-1 normalized coordinates
    width: float  # 0-1 normalized width
    height: float  # 0-1 normalized height

@dataclass
class OCRResult:
    text: str
    confidence: float
    page_number: int
    bounding_boxes: List[BoundingBox]

@dataclass
class Section:
    title: str
    content: str
    subsections: Optional[List['Section']] = None

@dataclass
class GeminiResult:
    summary: str
    key_points: List[str]
    sections: List[Section]
    difficulty_level: Literal['beginner', 'intermediate', 'advanced']

@dataclass
class OutputFiles:
    pdf_path: Path
    docx_path: Path
    audio_path: Path
    metadata: Dict[str, Any]

@dataclass
class USBFileEvent:
    event_type: Literal['created', 'modified', 'deleted']
    file_path: Path
    file_name: str
    timestamp: datetime

# 設定インターフェース
@dataclass
class AppConfig:
    # Google Cloud設定
    google_cloud_project_id: str
    vision_api: str
    google_application_credentials: str  # Path to service account JSON
    
    # OCR設定
    vision_api_timeout: int = 30
    vision_max_results: int = 10
    
    # Gemini設定
    gemini_model_name: str = "gemini-pro"
    gemini_temperature: float = 0.3
    gemini_max_output_tokens: int = 2048
    
    # 音声合成設定
    tts_language_code: str = "ja-JP"
    tts_voice_name: str = "ja-JP-Standard-A"
    tts_speaking_rate: float = 1.0
    tts_pitch: float = 0.0
    
    # ファイルパス設定
    usb_monitor_paths: List[str]  # 監視するUSBドライブパスリスト
    output_directory: Path
    temp_directory: Path
    
    # 処理設定
    pdf_dpi: int = 300  # PDFから画像への変換DPI
    max_file_size_mb: int = 50  # 処理可能な最大ファイルサイズ
    supported_extensions: List[str] = None
    
    def __post_init__(self):
        if self.supported_extensions is None:
            self.supported_extensions = ['.pdf']
```

### 関数インターフェース定義
```python
# USB監視モジュール
def start_usb_monitor(paths: List[str], callback: Callable[[USBFileEvent], None]) -> Any:
    """USBドライブ監視を開始する
    
    Args:
        paths: 監視するディレクトリパスのリスト
        callback: ファイルイベント発生時に呼び出されるコールバック関数
    
    Returns:
        モニターオブジェクト（stop()メソッドで停止可能）
    """
    ...

# PDF処理モジュール
def extract_images_from_pdf(pdf_path: Path, dpi: int = 300) -> List[Image.Image]:
    """PDFからページごとに画像を抽出する
    
    Args:
        pdf_path: 処理対象のPDFファイルパス
        dpi: 画像変換時の解像度
    
    Returns:
        ページごとのPIL Imageオブジェクトのリスト
    
    Raises:
        FileNotFoundError: PDFファイルが見つからない場合
        ValueError: PDFファイルが破損している場合
    """
    ...

# Google Cloud Vision OCRモジュール
def perform_ocr_on_image(image: Image.Image, language_hints: List[str] = ['ja', 'en']) -> OCRResult:
    """単一画像に対してOCRを実行する
    
    Args:
        image: OCR対象のPIL Imageオブジェクト
        language_hints: 言語ヒント（デフォルト: 日本語と英語）
    
    Returns:
        OCR結果オブジェクト
    
    Raises:
        GoogleAPICallError: Google Cloud API呼び出しに失敗した場合
        ValueError: 画像フォーマットがサポートされていない場合
    """
    ...

def process_pdf_with_ocr(pdf_path: Path) -> List[OCRResult]:
    """PDFファイル全体に対してOCRを実行する
    
    Args:
        pdf_path: 処理対象のPDFファイルパス
    
    Returns:
        各ページのOCR結果リスト
    """
    ...

# テキスト処理モジュール
def combine_ocr_results(ocr_results: List[OCRResult]) -> str:
    """OCR結果を結合して完全なテキストを生成する
    
    Args:
        ocr_results: ページごとのOCR結果リスト
    
    Returns:
        結合されたテキスト
    """
    ...

# Gemini APIモジュール
def summarize_with_gemini(text: str, target_audience: str = "beginner") -> GeminiResult:
    """Gemini APIを使用してテキストを要約・構造化する
    
    Args:
        text: 要約対象のテキスト
        target_audience: 対象読者レベル（初心者向けがデフォルト）
    
    Returns:
        Gemini処理結果オブジェクト
    
    Raises:
        GoogleAPICallError: Google Cloud API呼び出しに失敗した場合
        ValueError: 入力テキストが空または無効な場合
    """
    ...

# 出力生成モジュール
def create_formatted_pdf(content: GeminiResult, output_path: Path, 
                        title: str = "処理済みマニュアル") -> Path:
    """整形済みコンテンツからPDFファイルを生成する
    
    Args:
        content: Gemini APIからの処理結果
        output_path: 出力ファイルパス
        title: PDFドキュメントのタイトル
    
    Returns:
        生成されたPDFファイルパス
    
    Raises:
        IOError: ファイル書き込みに失敗した場合
    """
    ...

def create_word_document(content: GeminiResult, output_path: Path,
                        title: str = "処理済みマニュアル") -> Path:
    """整形済みコンテンツからWord文書を生成する
    
    Args:
        content: Gemini APIからの処理結果
        output_path: 出力ファイルパス
        title: 文書タイトル
    
    Returns:
        生成されたWord文書パス
    """
    ...

def create_audio_summary(key_points: List[str], output_path: Path,
                        language_code: str = "ja-JP") -> Path:
    """重要ポイントから音声ファイルを生成する
    
    Args:
        key_points: 音声化する重要ポイントのリスト
        output_path: 出力ファイルパス
        language_code: 言語コード（デフォルト: 日本語）
    
    Returns:
        生成された音声ファイルパス
    """
    ...

# メイン処理オーケストレーター
def process_manual_pdf(input_pdf_path: Path, output_dir: Path, 
                      config: AppConfig) -> OutputFiles:
    """PDFマニュアルを処理して複数形式の出力を生成するメイン関数
    
    Args:
        input_pdf_path: 処理対象の入力PDFファイルパス
        output_dir: 出力ファイルを保存するディレクトリ
        config: アプリケーション設定オブジェクト
    
    Returns:
        生成された出力ファイル情報
    
    Raises:
        FileNotFoundError: 入力ファイルが見つからない場合
        ProcessingError: 処理中に何らかのエラーが発生した場合
    """
    ...
```

### 例外クラス定義
```python
class ProcessingError(Exception):
    """処理中に発生した一般的なエラー"""
    pass

class OCRError(ProcessingError):
    """OCR処理中に発生したエラー"""
    pass

class GeminiAPIError(ProcessingError):
    """Gemini API呼び出し中に発生したエラー"""
    pass

class TTSError(ProcessingError):
    """音声合成中に発生したエラー"""
    pass

class FileIOError(ProcessingError):
    """ファイル入出力中に発生したエラー"""
    pass

class ConfigurationError(ProcessingError):
    """設定に関するエラー"""
    pass
```