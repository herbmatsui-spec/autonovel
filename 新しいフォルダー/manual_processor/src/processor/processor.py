"""
Processor Module
Main processing logic integrating OCR, summarization, and output generation
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from config.config import Config
from src.gemini_summarizer import GeminiSummarizer, GeminiSummaryResult
from src.docx_generator import create_word_document
from src.audio_generator import create_audio_summary
from src.qr_generator import generate_qr_code
from src.audio_uploader import upload_audio_summary

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Main document processor"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.get_instance()
        self.summarizer = GeminiSummarizer(self.config.gemini_api_key)
        logger.info("DocumentProcessor initialized")
    
    def process_pdf(self, pdf_path: Path, compact_layout: bool = False, use_emojis: bool = False, is_business_doc: bool = False, include_tables: bool = False, remove_markdown_bold: bool = True) -> Dict:
        """
        Process a PDF file through the complete pipeline
        
        Args:
            pdf_path: Path to the PDF file
            compact_layout: If True, generate compact layout with larger text and less whitespace
            use_emojis: If True, insert emojis into generated documents
            is_business_doc: If True, process as a standard business document instead of a manual
            include_tables: If True, include table extraction in summarization
            remove_markdown_bold: If True, remove markdown bold markers (**) from Word output
            
        Returns:
            Dictionary containing processing results
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            logger.info(f"Starting processing of {pdf_path} (is_business_doc={is_business_doc}, include_tables={include_tables})")
            
            # Step 1: Extract images from PDF for Multimodal Gemini processing
            extracted_images = self._extract_images_from_pdf(pdf_path)
            logger.info(f"PDF image extraction completed: {len(extracted_images)} pages extracted")
            
            # Step 2: Summarize and structure directly from images
            summary_result = self.summarizer.process_document(extracted_images, is_business_doc=is_business_doc, include_tables=include_tables)
            logger.info(f"Summarization completed: {len(summary_result.key_points)} key points found")
            
            # Step 3: Generate output files
            output_files = self._generate_outputs(summary_result, pdf_path, compact_layout=compact_layout, use_emojis=use_emojis, remove_markdown_bold=remove_markdown_bold, is_business_doc=is_business_doc)
            
            default_title = "業務文書" if is_business_doc else "手書きマニュアル"
            return {
                "success": True,
                "input_file": str(pdf_path),
                "title": getattr(summary_result, "title", default_title),
                "extracted_images_count": len(extracted_images),
                "summary": summary_result.summary,
                "key_points": summary_result.key_points,
                "sections": summary_result.sections,
                "glossary": getattr(summary_result, "glossary", []),
                "output_files": output_files
            }
        except Exception as e:
            logger.error(f"Processing failed for {pdf_path}: {e}")
            return {
                "success": False,
                "input_file": str(pdf_path),
                "error": str(e)
            }
            
    def process_batch(self, pdf_paths: list, compact_layout: bool = False, use_emojis: bool = False, is_business_doc: bool = False, include_tables: bool = False, remove_markdown_bold: bool = True) -> list:
        """
        Process multiple PDF files sequentially
        """
        results = []
        for pdf_path in pdf_paths:
            path_obj = Path(pdf_path)
            if path_obj.exists() and path_obj.suffix.lower() == ".pdf":
                result = self.process_pdf(path_obj, compact_layout=compact_layout, use_emojis=use_emojis, is_business_doc=is_business_doc, include_tables=include_tables, remove_markdown_bold=remove_markdown_bold)
                results.append(result)
        return results

    def process_directory(self, dir_path: Path, recursive: bool = True, compact_layout: bool = False, use_emojis: bool = False, is_business_doc: bool = False, include_tables: bool = False, remove_markdown_bold: bool = True) -> list:
        """
        Process all PDF files inside a directory
        """
        if not dir_path.exists() or not dir_path.is_dir():
            raise NotADirectoryError(f"Directory not found: {dir_path}")
        
        pattern = "**/*.pdf" if recursive else "*.pdf"
        pdf_files = list(dir_path.glob(pattern))
        logger.info(f"Found {len(pdf_files)} PDF files in directory: {dir_path}")
        return self.process_batch(pdf_files, compact_layout=compact_layout, use_emojis=use_emojis, is_business_doc=is_business_doc, include_tables=include_tables, remove_markdown_bold=remove_markdown_bold)
    
    def _extract_images_from_pdf(self, pdf_path: Path) -> list:
        """Extract images from all pages of a PDF"""
        import fitz  # PyMuPDF
        from PIL import Image
        import io
        
        images = []
        try:
            with fitz.open(str(pdf_path)) as doc:
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    pix = None
                    img = None
                    try:
                        pix = page.get_pixmap(dpi=self.config.pdf_dpi)
                        img_data = pix.tobytes("png")
                        img = Image.open(io.BytesIO(img_data))
                        images.append(img.copy())
                    finally:
                        if pix:
                            pix = None
                        if img:
                            img.close()
        except Exception as e:
            logger.error(f"PDF reading failed for {pdf_path}: {e}")
            raise
        
        return images
    
    def _generate_outputs(self, summary_result: GeminiSummaryResult, pdf_path: Path, compact_layout: bool = False, use_emojis: bool = False, remove_markdown_bold: bool = True, is_business_doc: bool = False) -> Dict[str, str]:
        """Generate Word and audio output files (PDF generation removed)"""
        import re
        output_dir = self.config.output_directory
        default_doc_title = "整理業務文書" if is_business_doc else "処理済みマニュアル"
        doc_title = getattr(summary_result, "title", default_doc_title)
        
        # 安全なファイル名を生成
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', doc_title).strip()
        base_name = f"{pdf_path.stem}_{safe_title}" if safe_title else pdf_path.stem
        
        # 整形テキストの構築
        content_lines = []
        content_lines.append(f"概要\n{summary_result.summary}\n")
        
        if summary_result.key_points:
            key_points_header = "## 経営・業務上の要点" if is_business_doc else "## 初心者向け重要ポイント"
            content_lines.append(key_points_header)
            for kp in summary_result.key_points:
                content_lines.append(f"- {kp}")
            content_lines.append("")
            
        for sec in summary_result.sections:
            content_lines.append(f"## {sec['title']}")
            content_lines.append(sec['content'])
            content_lines.append("")
            
        glossary = getattr(summary_result, "glossary", [])
        if glossary:
            glossary_header = "## 専門用語・補足定義" if is_business_doc else "## 用語集（解説）"
            content_lines.append(glossary_header)
            for item in glossary:
                content_lines.append(f"- {item['term']}: {item['explanation']}")
            content_lines.append("")
            
        full_content_text = "\n".join(content_lines)
        outputs = {}
        
        # 1. Generate Audio file first
        audio_output = None
        audio_url = ""
        qr_code_path = None
        
        try:
            audio_text = f"【{doc_title}】\n\n{summary_result.summary}"
            if summary_result.key_points:
                audio_text += "\n\n重要なポイントをまとめます。\n" + "\n".join([f"ポイント: {point}" for point in summary_result.key_points])
            
            audio_output = output_dir / f"{base_name}.mp3"
            create_audio_summary(audio_text, audio_output)
            outputs["audio"] = str(audio_output)
            logger.info(f"Audio file generated: {audio_output}")
            
            # 2. Upload/resolve public Cloud Audio URL (Plan C)
            audio_url = upload_audio_summary(audio_output)
            outputs["audio_url"] = audio_url
            
            # 3. Generate QR Code Image PNG
            if audio_url:
                qr_output_path = self.config.temp_directory / f"qr_{base_name}.png"
                qr_code_path = generate_qr_code(audio_url, qr_output_path)
                if qr_code_path:
                    outputs["qr_code"] = str(qr_code_path)
        except Exception as e:
            logger.warning(f"Audio/QR generation failed: {e}")
            outputs["audio"] = None
        
        # 4. Generate Word Document embedding the QR Code PNG
        try:
            docx_output = output_dir / f"{base_name}.docx"
            create_word_document(
                full_content_text,
                docx_output,
                title=doc_title,
                compact_layout=compact_layout,
                use_emojis=use_emojis,
                remove_markdown_bold=remove_markdown_bold,
                qr_code_path=qr_code_path,
                qr_audio_url=audio_url
            )
            outputs["docx"] = str(docx_output)
            logger.info(f"Word document with QR code generated: {docx_output}")
        except Exception as e:
            logger.warning(f"Word generation failed: {e}")
            outputs["docx"] = None
        
        return outputs