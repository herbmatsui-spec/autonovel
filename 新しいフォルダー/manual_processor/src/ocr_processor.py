# manual_processor/src/ocr_processor.py
import io
import os
import logging
from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    from google.cloud import vision
    from google.api_core.exceptions import GoogleAPICallError, RetryError, DeadlineExceeded
    _HAS_GOOGLE_VISION = True
except ImportError:
    _HAS_GOOGLE_VISION = False
    vision = None
    GoogleAPICallError = Exception
    RetryError = Exception
    DeadlineExceeded = Exception

logger = logging.getLogger(__name__)

@dataclass
class BoundingBox:
    """テキスト領域のバウンディングボックス"""
    x: float
    y: float
    width: float
    height: float

@dataclass
class OCRResult:
    """OCR処理結果"""
    text: str
    confidence: float
    page_number: int
    bounding_boxes: List[BoundingBox]

class OCRError(Exception):
    """OCR処理関連のエラー"""
    pass

class OCRProcessor:
    """Google Cloud Vision APIを使用したOCR処理クラス"""
    
    def __init__(self, project_id: Optional[str] = None, credentials_path: Optional[str] = None, 
                 api_key: Optional[str] = None, timeout: int = 30, max_results: int = 10):
        """
        Args:
            project_id: Google Cloud プロジェクトID（オプショナル）
            credentials_path: サービスアカウントキーファイルのパス（オプショナル）
            api_key: Google Cloud / AI APIキー（オプショナル）
            timeout: API呼び出しタイムアウト（秒）
            max_results: 最大検出結果数
        """
        if not _HAS_GOOGLE_VISION:
            raise OCRError("google-cloud-vision ライブラリがインストールされていません")
        
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.timeout = timeout
        self.max_results = max_results
        
        # 認証情報の設定
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        
        effective_api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ and not effective_api_key:
            raise OCRError("Google Cloud認証情報が設定されていません")
        
        try:
            if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
                self.client = vision.ImageAnnotatorClient()
            elif effective_api_key:
                from google.api_core.client_options import ClientOptions
                options = ClientOptions(api_key=effective_api_key)
                self.client = vision.ImageAnnotatorClient(client_options=options)
            else:
                self.client = vision.ImageAnnotatorClient()
            
            logger.info("Google Cloud Vision クライアントを初期化しました")
        except Exception as e:
            if isinstance(e, OCRError):
                raise e
            logger.error(f"Vision クライアント初期化エラー: {e}")
            raise OCRError(f"Vision クライアントの初期化に失敗しました: {e}")

    def extract_text(self, image: Image.Image) -> str:
        """
        単一画像からプレーンテキストを抽出する
        
        Args:
            image: PIL Image オブジェクト
            
        Returns:
            抽出されたテキスト文字列
        """
        result = self.perform_ocr_on_image(image)
        return result.text if result and result.text else ""
    
    def is_service_available(self) -> bool:
        """Vision APIサービスが利用可能かチェック"""
        try:
            # 簡単なテストリクエストを送信
            test_image = vision.Image(content=b"test")
            self.client.document_text_detection(image=test_image, timeout=5)
            return True
        except Exception:
            return False
    
    def _image_to_bytes(self, image: Image.Image) -> bytes:
        """PIL Imageをバイト列に変換"""
        buffer = io.BytesIO()
        # JPEG形式で保存（効率的）
        image.save(buffer, format="JPEG", quality=95)
        return buffer.getvalue()
    
    def _vision_result_to_ocr_result(self, response, page_number: int) -> OCRResult:
        """Vision APIレスポンスをOCRResultに変換"""
        bounding_boxes = []
        total_confidence = 0.0
        word_count = 0
        word_texts = []
        
        if response.full_text_annotation:
            # ページ、ブロック、段落、単語、シンボルの階層を走査
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            word_text = "".join([getattr(symbol, 'text', str(symbol)) for symbol in word.symbols])
                            if word_text.strip():
                                word_texts.append(word_text)
                                # バウンディングボックス取得（正規化座標 0-1）
                                vertices = word.bounding_box.vertices
                                if len(vertices) >= 4:
                                    xs = [v.x for v in vertices]
                                    ys = [v.y for v in vertices]
                                    min_x, max_x = min(xs), max(xs)
                                    min_y, max_y = min(ys), max(ys)
                                    
                                    bounding_boxes.append(BoundingBox(
                                        x=float(min_x),
                                        y=float(min_y),
                                        width=float(max_x - min_x),
                                        height=float(max_y - min_y)
                                    ))
                                
                                # 信頼度計算（単語レベル）
                                if hasattr(word, 'confidence') and word.confidence:
                                    total_confidence += word.confidence
                                    word_count += 1
        
        # 平均信頼度を計算
        avg_confidence = total_confidence / word_count if word_count > 0 else 0.0
        full_text = "".join(word_texts) if word_texts else (response.full_text_annotation.text if response.full_text_annotation else "")
        
        return OCRResult(
            text=full_text.strip(),
            confidence=avg_confidence,
            page_number=page_number,
            bounding_boxes=bounding_boxes
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type((GoogleAPICallError, RetryError, DeadlineExceeded)),
        reraise=True
    )
    def perform_ocr_on_image(self, image: Image.Image, 
                            language_hints: List[str] = None) -> OCRResult:
        """
        単一画像に対してOCRを実行する
        
        Args:
            image: OCR対象のPIL Imageオブジェクト
            language_hints: 言語ヒント（デフォルト: ['ja', 'en']）
        
        Returns:
            OCR結果オブジェクト
        
        Raises:
            OCRError: API呼び出しに失敗した場合
            ValueError: 画像フォーマットがサポートされていない場合
        """
        if language_hints is None:
            language_hints = ['ja', 'en']
        
        try:
            # 画像をバイト列に変換
            image_bytes = self._image_to_bytes(image)
            
            # Vision APIリクエスト作成
            image_obj = vision.Image(content=image_bytes)
            
            # 言語ヒントを設定
            image_context = vision.ImageContext(language_hints=language_hints)
            
            # ドキュメントテキスト検出（手書き対応）
            response = self.client.document_text_detection(
                image=image_obj,
                image_context=image_context,
                timeout=self.timeout
            )
            
            # エラーチェック
            if response.error.message:
                raise OCRError(f"Vision APIエラー: {response.error.message}")
            
            # 結果をOCRResultに変換
            result = self._vision_result_to_ocr_result(response, page_number=1)
            logger.debug(f"OCR完了: 文字数={len(result.text)}, 信頼度={result.confidence:.2f}")
            return result
            
        except GoogleAPICallError as e:
            logger.error(f"Google API呼び出しエラー: {e}")
            raise OCRError(f"OCR API呼び出しに失敗しました: {e}")
        except RetryError as e:
            logger.error(f"リトライエラー: {e}")
            raise OCRError(f"OCR処理がタイムアウトしました: {e}")
        except DeadlineExceeded as e:
            logger.error(f"デッドライン超過: {e}")
            raise OCRError(f"OCR処理がタイムアウトしました: {e}")
        except Exception as e:
            logger.error(f"OCR処理中に予期せぬエラー: {e}")
            raise OCRError(f"OCR処理に失敗しました: {e}")
    
    def process_pdf_pages(self, images: List[Image.Image], 
                         language_hints: List[str] = None,
                         progress_callback: callable = None) -> List[OCRResult]:
        """
        複数ページの画像に対してOCRを順次実行
        
        Args:
            images: OCR対象のPIL Imageオブジェクトのリスト
            language_hints: 言語ヒント（デフォルト: ['ja', 'en']）
            progress_callback: 進捗コールバック
        
        Returns:
            各ページのOCR結果リスト
        """
        if language_hints is None:
            language_hints = ['ja', 'en']
        
        results = []
        total_pages = len(images)
        
        logger.info(f"複数ページOCR処理開始: {total_pages} ページ")
        
        for i, image in enumerate(images):
            page_number = i + 1
            try:
                result = self.perform_ocr_on_image(image, language_hints)
                result.page_number = page_number
                results.append(result)
                
                # 進捗報告
                if progress_callback:
                    try:
                        progress_callback(page_number, total_pages)
                    except Exception as e:
                        logger.warning(f"進捗コールバックエラー: {e}")
                
                logger.info(f"ページ {page_number}/{total_pages} OCR完了: "
                           f"{len(result.text)}文字, 信頼度={result.confidence:.2f}")
                
            except OCRError as e:
                logger.error(f"ページ {page_number} のOCRに失敗: {e}")
                # 失敗したページは空の結果として追加
                results.append(OCRResult(
                    text="",
                    confidence=0.0,
                    page_number=page_number,
                    bounding_boxes=[]
                ))
        
        logger.info(f"複数ページOCR処理完了: {len(results)} ページ処理")
        return results
    
    @staticmethod
    def calculate_overall_confidence(ocr_results: List[OCRResult]) -> float:
        """
        全ページのOCR結果から平均信頼度を計算（文字数で重み付け）
        
        Args:
            ocr_results: ページごとのOCR結果リスト
        
        Returns:
            重み付き平均信頼度 (0.0-1.0)
        """
        if not ocr_results:
            return 0.0
        
        total_weight = 0
        weighted_sum = 0.0
        
        for result in ocr_results:
            weight = len(result.text) if result.text else 1
            weighted_sum += result.confidence * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0


# 便利関数（後方互換性のため）
def perform_ocr_on_image(image: Image.Image, language_hints: List[str] = None,
                        project_id: str = None, credentials_path: str = None) -> OCRResult:
    """単一画像OCRの便利関数"""
    processor = OCRProcessor(project_id=project_id, credentials_path=credentials_path)
    return processor.perform_ocr_on_image(image, language_hints)

def process_pdf_with_ocr(pdf_images: List[Image.Image], language_hints: List[str] = None,
                        project_id: str = None, credentials_path: str = None, progress_callback: callable = None) -> List[OCRResult]:
    """PDF全体のOCR処理便利関数"""
    processor = OCRProcessor(project_id=project_id, credentials_path=credentials_path)
    return processor.process_pdf_pages(pdf_images, language_hints, progress_callback)