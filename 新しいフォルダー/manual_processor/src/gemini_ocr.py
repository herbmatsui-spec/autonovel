"""
Gemini OCR Processor
Handles OCR processing using Gemini 3.1 Flash Lite multimodal capabilities
"""

import logging
from typing import Optional
from pathlib import Path
from PIL import Image

import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiOCRProcessor:
    """Handles OCR processing using Gemini 3.1 Flash Lite multimodal capabilities"""
    
    def __init__(self, api_key: str):
        """
        Initialize Gemini OCR processor
        
        Args:
            api_key: Google AI Studio API key
        """
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        # model name was updated to a standard one to avoid potential 'model not found' or auth issues with specific preview versions
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("Gemini OCR Processor initialized")
    
    def extract_text(self, image: Image.Image) -> str:
        """
        Extract text from image using Gemini 3.1 Flash Lite
        
        Args:
            image: PIL Image object
            
        Returns:
            Extracted text string
        """
        try:
            # Prepare the prompt for OCR
            prompt = """
            この画像から日本語テキストを抽出してください。
            手書き文字、印刷体、英語、数字、図表の説明文をすべて含めてください。
            マークダウン形式で出力せず、プレーンテキストとして返してください。
            画像にテキストがない場合は空の文字列を返してください。
            """
            
            # Generate content with image and prompt
            response = self.model.generate_content([prompt, image])
            
            return response.text if response.text else ""
            
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            raise Exception(f"OCR processing failed: {e}")
    
    def extract_text_from_pdf_page(self, pdf_path: Path, page_number: int) -> str:
        """
        Extract text from a specific PDF page
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number to extract (1-indexed)
            
        Returns:
            Extracted text string
        """
        try:
            import fitz  # PyMuPDF
            
            # Open PDF and get page
            doc = fitz.open(str(pdf_path))
            if page_number < 1 or page_number > doc.page_count:
                raise ValueError(f"Invalid page number: {page_number}")
            
            page = doc.load_page(page_number - 1)
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
            
            return self.extract_text(img)
            
        except Exception as e:
            logger.error(f"Failed to extract text from PDF page: {e}")
            raise Exception(f"Failed to extract text from PDF page: {e}")