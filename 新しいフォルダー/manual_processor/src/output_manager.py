# manual_processor/src/output_manager.py
import logging
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass

from .gemini_processor import GeminiResult
from .pdf_generator import create_formatted_pdf, PDFGenerationError
from .docx_generator import create_word_document, DocxGenerationError
from .audio_generator import AudioGenerator, TTSError

logger = logging.getLogger(__name__)

@dataclass
class OutputFiles:
    """生成された出力ファイル情報"""
    pdf_path: Path
    docx_path: Path
    audio_path: Path
    metadata: Dict[str, Any]

@dataclass
class OutputConfig:
    """出力設定"""
    output_directory: Path
    base_name: str
    include_pdf: bool = True
    include_docx: bool = True
    include_audio: bool = True
    language_code: str = "ja-JP"
    voice_name: str = "ja-JP-Standard-A"
    speaking_rate: float = 1.0
    pitch: float = 0.0

def save_all_formats(content: GeminiResult, base_output_path: Path,
                    config: OutputConfig,
                    title: str = "処理済みマニュアル",
                    compact_layout: bool = False,
                    use_emojis: bool = False) -> OutputFiles:
    """
    すべての出力形式（PDF, Word, Audio）を一括で保存するメイン関数
    
    Args:
        content: Gemini APIからの処理結果
        base_output_path: 出力ベースパス（拡張子なし）
        config: 出力設定
        title: ドキュメントタイトル
    
    Returns:
        生成された出力ファイル情報
    
    Raises:
        FileIOError: ディスク書き込みエラー
    """
    # 出力ディレクトリの作成
    config.output_directory.mkdir(parents=True, exist_ok=True)
    
    # 出力ファイルパスの生成
    base_name = config.base_name or base_output_path.stem
    pdf_path = config.output_directory / f"{base_name}.pdf"
    docx_path = config.output_directory / f"{base_name}.docx"
    audio_path = config.output_directory / f"{base_name}.mp3"
    
    errors = []
    
    # PDF生成
    if config.include_pdf:
        try:
            pdf_path = create_formatted_pdf(content, pdf_path, title, compact_layout=compact_layout, use_emojis=use_emojis)
            logger.info(f"PDF出力完了: {pdf_path}")
        except PDFGenerationError as e:
            logger.error(f"PDF生成失敗: {e}")
            errors.append(f"PDF: {str(e)}")
        except Exception as e:
            logger.error(f"PDF生成中の予期せぬエラー: {e}")
            errors.append(f"PDF: 予期せぬエラー - {str(e)}")
    
    # Word文書生成
    if config.include_docx:
        try:
            docx_path = create_word_document(content, docx_path, title, compact_layout=compact_layout, use_emojis=use_emojis)
            logger.info(f"Word出力完了: {docx_path}")
        except DocxGenerationError as e:
            logger.error(f"Word生成失敗: {e}")
            errors.append(f"Word: {str(e)}")
        except Exception as e:
            logger.error(f"Word生成中の予期せぬエラー: {e}")
            errors.append(f"Word: 予期せぬエラー - {str(e)}")
    
    # 音声生成
    if config.include_audio:
        try:
            audio_generator = AudioGenerator(
                language_code=config.language_code,
                voice_name=config.voice_name,
                speaking_rate=config.speaking_rate,
                pitch=config.pitch
            )
            audio_path = audio_generator.create_audio_summary(
                content.key_points,
                audio_path,
                language_code=config.language_code,
                voice_name=config.voice_name
            )
            logger.info(f"音声出力完了: {audio_path}")
        except TTSError as e:
            logger.error(f"音声生成失敗: {e}")
            errors.append(f"Audio: {str(e)}")
        except Exception as e:
            logger.error(f"音声生成中の予期せぬエラー: {e}")
            errors.append(f"Audio: 予期せぬエラー - {str(e)}")
    
    # エラーがあれば警告を出す
    if errors:
        logger.warning(f"出力生成でエラーが発生: {errors}")
    
    # メタデータの作成
    metadata = {
        "source_file": str(base_output_path),
        "processed_at": str(Path(base_output_path).stat().st_mtime) if base_output_path.exists() else 0,
        "page_count": len(content.sections),
        "word_count": len(content.summary) if content.summary else 0,
        "key_point_count": len(content.key_points),
        "errors": errors if errors else []
    }
    
    return OutputFiles(
        pdf_path=pdf_path,
        docx_path=docx_path,
        audio_path=audio_path,
        metadata=metadata
    )

def save_single_format(content: GeminiResult, output_path: Path,
                       format_type: str,
                       title: str = "処理済みマニュアル",
                       compact_layout: bool = False,
                       use_emojis: bool = False) -> Path:
    """
    単一の出力形式のみを保存する関数
    
    Args:
        content: Gemini APIからの処理結果
        output_path: 出力ファイルパス
        format_type: 出力形式 ('pdf', 'docx', 'audio')
        title: ドキュメントタイトル
    
    Returns:
        生成された出力ファイルパス
    
    Raises:
        ValueError: 不正な形式タイプが指定された場合
    """
    format_type = format_type.lower()
    
    if format_type == 'pdf':
        return create_formatted_pdf(content, output_path, title, compact_layout=compact_layout, use_emojis=use_emojis)
    elif format_type == 'docx':
        return create_word_document(content, output_path, title, compact_layout=compact_layout, use_emojis=use_emojis)
    elif format_type == 'audio':
        audio_generator = AudioGenerator()
        return audio_generator.create_audio_summary(content.key_points, output_path)
    else:
        raise ValueError(f"サポートされていない出力形式です: {format_type}")