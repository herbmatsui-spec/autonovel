# manual_processor/tests/test_ocr_processor.py
import pytest
import io
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from src.ocr_processor import (
    OCRProcessor,
    OCRResult,
    BoundingBox,
    OCRError,
    perform_ocr_on_image,
    process_pdf_with_ocr,
    _HAS_GOOGLE_VISION
)

@pytest.mark.skipif(not _HAS_GOOGLE_VISION, reason="google-cloud-vision is not installed")
class TestOCRProcessor:
    """OCRProcessor クラスのテスト"""

    def test_ocr_processor_initialization_success(self):
        """正常な初期化ができること"""
        with patch.dict('os.environ', {'GOOGLE_APPLICATION_CREDENTIALS': '/fake/path.json'}):
            with patch('src.ocr_processor.vision.ImageAnnotatorClient'):
                processor = OCRProcessor(project_id="test-project")
                assert processor.project_id == "test-project"
                assert processor.timeout == 30
                assert processor.max_results == 10

    def test_ocr_processor_initialization_missing_credentials(self):
        """認証情報がない場合にエラーになること"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(OCRError, match="Google Cloud認証情報が設定されていません"):
                OCRProcessor(project_id="test-project")

    def test_ocr_processor_is_service_available(self):
        """サービス利用可能チェックが機能すること"""
        with patch.dict('os.environ', {'GOOGLE_APPLICATION_CREDENTIALS': '/fake/path.json'}):
            with patch('src.ocr_processor.vision.ImageAnnotatorClient') as mock_client:
                mock_instance = Mock()
                mock_client.return_value = mock_instance
                mock_instance.document_text_detection.return_value = Mock()
                
                processor = OCRProcessor(project_id="test-project")
                assert processor.is_service_available() is True

    def test_ocr_processor_is_service_available_failure(self):
        """サービス利用不可時にFalseが返ること"""
        with patch.dict('os.environ', {'GOOGLE_APPLICATION_CREDENTIALS': '/fake/path.json'}):
            with patch('src.ocr_processor.vision.ImageAnnotatorClient') as mock_client:
                mock_instance = Mock()
                mock_client.return_value = mock_instance
                mock_instance.document_text_detection.side_effect = Exception("API error")
                
                processor = OCRProcessor(project_id="test-project")
                assert processor.is_service_available() is False

    def test_image_to_bytes(self):
        """画像をバイト列に変換できること"""
        with patch.dict('os.environ', {'GOOGLE_APPLICATION_CREDENTIALS': '/fake/path.json'}):
            with patch('src.ocr_processor.vision.ImageAnnotatorClient'):
                processor = OCRProcessor(project_id="test-project")
                img = Image.new('RGB', (10, 10), color='red')
                bytes_data = processor._image_to_bytes(img)
                assert isinstance(bytes_data, bytes)
                assert len(bytes_data) > 0

    def test_vision_result_to_ocr_result_empty(self):
        """空のVision APIレスポンスを処理できること"""
        with patch.dict('os.environ', {'GOOGLE_APPLICATION_CREDENTIALS': '/fake/path.json'}):
            with patch('src.ocr_processor.vision.ImageAnnotatorClient'):
                processor = OCRProcessor(project_id="test-project")
                # 空のレスポンスを作成
                response = Mock()
                response.full_text_annotation.text = ""
                response.full_text_annotation.pages = []
                
                result = processor._vision_result_to_ocr_result(response, page_number=1)
                assert result.text == ""
                assert result.confidence == 0.0
                assert result.page_number == 1
                assert result.bounding_boxes == []

    def test_vision_result_to_ocr_result_with_text(self):
        """テキストを含むVision APIレスポンスを処理できること"""
        with patch.dict('os.environ', {'GOOGLE_APPLICATION_CREDENTIALS': '/fake/path.json'}):
            with patch('src.ocr_processor.vision.ImageAnnotatorClient'):
                processor = OCRProcessor(project_id="test-project")
                
                # モックレスポンスの構造を作成
                response = Mock()
                response.full_text_annotation.text = "こんにちは世界"
                
                # ページ、ブロック、段落、単語のモック
                page = Mock()
                block = Mock()
                paragraph = Mock()
                word = Mock()
                symbol = Mock()
                
                symbol.text = "こ"
                symbol.__str__ = Mock(return_value="こ")
                word.symbols = [symbol]
                word.confidence = 0.9
                word.bounding_box.vertices = [
                    Mock(x=10, y=10),
                    Mock(x=20, y=10),
                    Mock(x=20, y=20),
                    Mock(x=10, y=20)
                ]
                paragraph.words = [word]
                block.paragraphs = [paragraph]
                page.blocks = [block]
                response.full_text_annotation.pages = [page]
                
                result = processor._vision_result_to_ocr_result(response, page_number=1)
                assert result.text == "こ"
                assert result.confidence == 0.9
                assert result.page_number == 1
                assert len(result.bounding_boxes) == 1
                assert result.bounding_boxes[0].x == 10.0
                assert result.bounding_boxes[0].y == 10.0
                assert result.bounding_boxes[0].width == 10.0
                assert result.bounding_boxes[0].height == 10.0

    def test_perform_ocr_on_image_success(self):
        """正常なOCR処理ができること"""
        with patch.dict('os.environ', {'GOOGLE_APPLICATION_CREDENTIALS': '/fake/path.json'}):
            with patch('src.ocr_processor.vision.ImageAnnotatorClient') as mock_client:
                # Vision APIレスポンスのモック
                mock_response = Mock()
                mock_response.error.message = ""
                mock_response.full_text_annotation.text = "テストテキスト"
                mock_response.full_text_annotation.pages = []
                
                mock_instance = Mock()
                mock_client.return_value = mock_instance
                mock_instance.document_text_detection.return_value = mock_response
                
                processor = OCRProcessor(project_id="test-project")
                img = Image.new('RGB', (100, 100), color='white')
                
                result = processor.perform_ocr_on_image(img)
                assert isinstance(result, OCRResult)
                assert result.text == "テストテキスト"
                assert result.confidence >= 0.0  # 実際の値はモック次第
                assert result.page_number == 1

    def test_perform_ocr_on_image_api_error(self):
        """APIエラー時にOCRErrorが送出されること"""
        with patch.dict('os.environ', {'GOOGLE_APPLICATION_CREDENTIALS': '/fake/path.json'}):
            with patch('src.ocr_processor.vision.ImageAnnotatorClient') as mock_client:
                mock_response = Mock()
                mock_response.error.message = "API エラーが発生しました"
                
                mock_instance = Mock()
                mock_client.return_value = mock_instance
                mock_instance.document_text_detection.return_value = mock_response
                
                processor = OCRProcessor(project_id="test-project")
                img = Image.new('RGB', (100, 100), color='white')
                
                with pytest.raises(OCRError, match="Vision APIエラー"):
                    processor.perform_ocr_on_image(img)

    def test_process_pdf_pages(self):
        """複数ページのOCR処理ができること"""
        with patch.dict('os.environ', {'GOOGLE_APPLICATION_CREDENTIALS': '/fake/path.json'}):
            with patch('src.ocr_processor.vision.ImageAnnotatorClient') as mock_client:
                # Vision APIレスポンスのモック
                mock_response = Mock()
                mock_response.error.message = ""
                mock_response.full_text_annotation.text = "ページテキスト"
                mock_response.full_text_annotation.pages = []
                
                mock_instance = Mock()
                mock_client.return_value = mock_instance
                mock_instance.document_text_detection.return_value = mock_response
                
                processor = OCRProcessor(project_id="test-project")
                images = [Image.new('RGB', (100, 100), color='white') for _ in range(3)]
                
                results = processor.process_pdf_pages(images)
                assert len(results) == 3
                for result in results:
                    assert isinstance(result, OCRResult)
                    assert result.text == "ページテキスト"

    def test_calculate_overall_confidence(self):
        """全体の信頼度計算が正しく行われること"""
        with patch.dict('os.environ', {'GOOGLE_APPLICATION_CREDENTIALS': '/fake/path.json'}):
            with patch('src.ocr_processor.vision.ImageAnnotatorClient'):
                processor = OCRProcessor(project_id="test-project")
                
                # テストデータ: 3ページ
                results = [
                    OCRResult(text="あいう", confidence=0.8, page_number=1, bounding_boxes=[]),
                    OCRResult(text="かきくけこ", confidence=0.9, page_number=2, bounding_boxes=[]),
                    OCRResult(text="さ", confidence=0.7, page_number=3, bounding_boxes=[])
                ]
                
                # 重み付き平均: (0.8*3 + 0.9*5 + 0.7*1) / (3+5+1) = (2.4 + 4.5 + 0.7) / 9 = 7.6/9 = 0.844...
                expected = (0.8*3 + 0.9*5 + 0.7*1) / (3+5+1)
                actual = processor.calculate_overall_confidence(results)
                assert abs(actual - expected) < 0.001

    def test_calculate_overall_confidence_empty(self):
        """空のリストの場合は0.0を返すこと"""
        with patch.dict('os.environ', {'GOOGLE_APPLICATION_CREDENTIALS': '/fake/path.json'}):
            with patch('src.ocr_processor.vision.ImageAnnotatorClient'):
                processor = OCRProcessor(project_id="test-project")
                assert processor.calculate_overall_confidence([]) == 0.0

# 便利関数のテスト
class TestConvenienceFunctions:
    """便利関数のテスト"""

    def test_perform_ocr_on_image_convenience(self):
        """便利関数が正しく動作すること"""
        with patch.dict('os.environ', {'GOOGLE_APPLICATION_CREDENTIALS': '/fake/path.json'}):
            with patch('src.ocr_processor.OCRProcessor') as mock_processor_class:
                mock_instance = Mock()
                mock_processor_class.return_value = mock_instance
                mock_result = OCRResult(text="テスト", confidence=0.9, page_number=1, bounding_boxes=[])
                mock_instance.perform_ocr_on_image.return_value = mock_result
                
                img = Image.new('RGB', (100, 100), color='white')
                result = perform_ocr_on_image(img, project_id="test", credentials_path="/fake/path.json")
                
                assert result == mock_result
                mock_processor_class.assert_called_once_with(project_id="test", credentials_path="/fake/path.json")
                mock_instance.perform_ocr_on_image.assert_called_once_with(img, None)

    def test_process_pdf_with_ocr_convenience(self):
        """PDF処理の便利関数が正しく動作すること"""
        with patch.dict('os.environ', {'GOOGLE_APPLICATION_CREDENTIALS': '/fake/path.json'}):
            with patch('src.ocr_processor.OCRProcessor') as mock_processor_class:
                mock_instance = Mock()
                mock_processor_class.return_value = mock_instance
                mock_results = [
                    OCRResult(text="ページ1", confidence=0.8, page_number=1, bounding_boxes=[]),
                    OCRResult(text="ページ2", confidence=0.9, page_number=2, bounding_boxes=[])
                ]
                mock_instance.process_pdf_pages.return_value = mock_results
                
                images = [Image.new('RGB', (100, 100), color='white') for _ in range(2)]
                results = process_pdf_with_ocr(images, project_id="test", credentials_path="/fake/path.json")
                
                assert results == mock_results
                mock_processor_class.assert_called_once_with(project_id="test", credentials_path="/fake/path.json")
                mock_instance.process_pdf_pages.assert_called_once_with(images, None, None)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])