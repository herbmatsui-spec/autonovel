"""
Gemini Summarizer
Handles text summarization and structuring using Gemini 3.1 Flash Lite
"""

import logging
from typing import List, Optional
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    from google import genai
    _HAS_GENAI = True
except ImportError:
    _HAS_GENAI = False
    import google.generativeai as genai

logger = logging.getLogger(__name__)

@dataclass
class GeminiSummaryResult:
    """Result of summarization and structuring"""
    title: str
    summary: str
    key_points: List[str]
    sections: List[dict]  # Each section is a dict with 'title' and 'content'
    glossary: Optional[List[dict]] = None  # List of {'term': str, 'explanation': str}

class GeminiSummarizer:
    """Handles text summarization and structuring using Google AI Studio Gemini 3.1 Flash Lite"""
    
    def __init__(self, api_key: str, model_name: str = "gemini-3.1-flash-lite"):
        """
        Initialize Gemini summarizer
        
        Args:
            api_key: Google AI Studio API key
            model_name: Gemini model name (default: gemini-3.1-flash-lite)
        """
        self.api_key = api_key
        self.model_name = model_name
        if _HAS_GENAI:
            self.client = genai.Client(api_key=self.api_key)
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        logger.info(f"Gemini Summarizer initialized ({self.model_name})")
    
    def _generate(self, prompt: str, images: Optional[List] = None) -> str:
        """Internal helper to generate text with gemini-3.1-flash-lite"""
        contents = [prompt] + (images if images else [])
        if _HAS_GENAI:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents
            )
            return response.text.strip() if response.text else ""
        else:
            response = self.model.generate_content(contents)
            return response.text.strip() if response.text else ""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def _generate_with_retry(self, prompt: str, images: Optional[List] = None) -> str:
        """Internal helper with retry support for API calls including images"""
        contents = [prompt] + (images if images else [])
        if _HAS_GENAI:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents
            )
            return response.text.strip() if response.text else ""
        else:
            response = self.model.generate_content(contents)
            return response.text.strip() if response.text else ""
    
    def generate_title(self, text: str, is_business_doc: bool = False) -> str:
        """
        テキストから内容を的確に表すタイトルを自動生成
        """
        default_title = "整理業務文書" if is_business_doc else "処理済みマニュアル"
        if not text.strip():
            return default_title
        try:
            doc_type = "業務文書" if is_business_doc else "マニュアル"
            prompt = f"""
            以下のテキストの内容を読み取り、内容を的確かつ簡潔に表す適切な「{doc_type}のタイトル」を1つ生成してください。
            記号や余計な解説は省き、タイトル名のみを出力してください。
            
            テキスト:
            {text[:1500]}
            """
            title = self._generate_with_retry(prompt).strip()
            # クリーニング
            import re
            title = re.sub(r'^[【「\[\(]*(.*?)[】」\]\)]*$', r'\1', title)
            return title if title else default_title
        except Exception as e:
            logger.warning(f"タイトル自動生成失敗: {e}")
            return default_title
    
    def summarize(self, text: str, max_length: Optional[int] = None) -> str:
        """
        Summarize text for beginners
        """
        if not text.strip():
            return ""
        
        try:
            prompt = f"""
            以下の手書きマニュアルテキストを、完全な初心者でも迷わずに理解・実行できるように整理してください。
            
            指示:
            1. 元のテキストに含まれる具体例、数値、注意事項、例外ケースは一切省略せず、すべて含めてください。
            2. 専門用語や難しい言葉は、中学生でも理解できる平易な言葉に置き換えるか簡単な説明を添えてください。
            3. 手順やポイントは分かりやすく箇条書きで示してください。
            4. 抽象的なまとめ文に逃げず、元の情報量と解像度を保持したまま分かりやすくリライトしてください。
            5. 日本語で出力してください。
            
            テキスト:
            {text}
            """
            
            summary = self._generate_with_retry(prompt)
            
            if max_length and len(summary) > max_length:
                summary = summary[:max_length]
                
            return summary
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            raise Exception(f"Summarization failed: {e}")
    
    def extract_key_points(self, text: str, max_points: int = 10) -> List[str]:
        """
        Extract key points from text
        """
        if not text.strip():
            return []
        
        try:
            prompt = f"""
            以下のテキストから、初心者が絶対に押さえるべき重要ポイント・注意点を{max_points}つ以内で箇条書きにして抽出してください。
            
            制約:
            - 日本語で出力してください
            - 各ポイントは1文で分かりやすく記述してください
            - 各行は「- 」で始めてください
            - 元のテキストに含まれる重要な条件や数値、例外規定を勝手に端折らないでください
            
            テキスト:
            {text}
            """
            
            result_text = self._generate_with_retry(prompt)
            lines = result_text.split('\n')
            key_points = []
            for line in lines:
                line = line.strip()
                if line.startswith('- ') or line.startswith('• '):
                    point = line[2:].strip()
                    if point:
                        key_points.append(point)
                elif line and not line.startswith(' '):
                    key_points.append(line)
            
            return key_points[:max_points]
        except Exception as e:
            logger.error(f"Key point extraction failed: {e}")
            raise Exception(f"Key point extraction failed: {e}")
    
    def process_document(self, content_input: Any, include_tables: bool = False, is_business_doc: bool = False) -> GeminiSummaryResult:
        """
        Process document (images or text) to get title, summary, key points, beginner sections, and glossary
        
        Args:
            content_input: Input PIL Images list or raw text string
            include_tables: If True, include table generation in the output
            is_business_doc: If True, format prompt and structure specifically for business documents
        """
        images = []
        text_content = ""
        
        if isinstance(content_input, list):
            images = content_input
        elif isinstance(content_input, str):
            text_content = content_input
            if not text_content.strip():
                return GeminiSummaryResult(
                    title="空のドキュメント",
                    summary="",
                    key_points=[],
                    sections=[],
                    glossary=[]
                )
        
        if not images and not text_content:
            return GeminiSummaryResult(
                title="空のドキュメント",
                summary="",
                key_points=[],
                sections=[],
                glossary=[]
            )
        
        try:
            table_instruction = """
            [TABLES]
            表形式やリスト比較で整理すると分かりやすい情報がある場合、必ずMarkdown形式の表（| 項目 | 説明 | 形式）で出力してください。
            例:
            | 項目 | 内容 | 注意点 |
            |------|------|--------|
            | 手順1 | 準備作業 | 漏れなく確認 |
            """ if include_tables else ""
            
            # ステップ1: すべての重要要素・数値・手順・注意事項・図解の意味を一切省略せずに抽出
            if images:
                extraction_prompt = """
                あなたは情報の網羅性を徹底するデータ抽出アナリストです。
                添付された画像（マニュアル・文書のスキャン画像）を詳細に読み取り、含まれている事実、具体的な数値、手順、図解や矢印の意味、例外規定、注意点、専門用語などのすべての要素を、一切省略せずに箇条書きでリストアップしてください。
                
                【重要制約】
                - 情報をまとめたり抽象化したりせず、元の情報の解像度をそのまま維持してください。
                - 「その他」「等」でまとめず、該当する項目をすべて書き出してください。
                - 図表や表に含まれる行・列の情報もすべて文字化して列挙してください。
                - 評価や推敲は不要です。要素の漏れなき抽出のみを行ってください。
                """
                extracted_elements = self._generate_with_retry(extraction_prompt, images=images)
            else:
                extraction_prompt = f"""
                あなたは情報の網羅性を徹底するデータ抽出アナリストです。
                以下のテキストを読み取り、含まれている事実、具体的な数値、手順、例外規定、注意点、専門用語などのすべての要素を、一切省略せずに箇条書きでリストアップしてください。
                
                テキスト:
                {text_content}
                """
                extracted_elements = self._generate_with_retry(extraction_prompt)
            
            # ステップ2: 抽出要素リストおよび画像/テキストを元に構造化文書を生成
            if is_business_doc:
                prompt = f"""
            あなたは優れたビジネスアナリスト・文書整理コンサルタントです。
            抽出された重要要素リストおよび元のドキュメントを読み取り、役員・担当者・関係者が迅速かつ正確に内容を把握できるよう、整理・構造化して以下のフォーマットで出力してください。

            【出力フォーマット絶対遵守】
            ・抽出要素リストにある情報（具体的な数値、担当者、期限、例外規定、リスク等）は一切省略せず、適切なセクションにすべて組み込んでください。
            ・端折った大雑把な要約にせず、元の文書の解像度と網羅性を完全に保持してください。
            ・箇条書きは必ず `- ` (ハイフン＋スペース) で始めてください。

            [TITLE]
            文書の本質を的確に表す簡潔なビジネス文書タイトル（1行）

            [SUMMARY]
            この文書の要約・目的・結論を、主要な決定事項や数値を含めて客観的なビジネス文体で3-4文で説明してください。

            [KEY_POINTS]
            - 経営・業務上で重要となる要点、決定事項、主要な数値や結論（省略せず網羅的に箇条書き）

            [SECTIONS]
            ## 1. 目的・背景
            この文書が作成された背景、経緯、目的を詳細を省かずに整理して記述

            ## 2. 主要トピック・詳細内容
            業務内容、決定事項、現状分析、または主要な報告内容を論理的かつ具体例・数値を含めて記述

            ## 3. 業務上の影響・注意事項
            関係部署への影響、留意すべきリスクや遵守事項などを細部まで記述

            ## 4. 今後の対応・スケジュール
            今後のアクションプラン、担当者、タスク、期限などを漏れなく記述
            {table_instruction}

            [GLOSSARY]
            - 専門用語・社内略語: 必要に応じてビジネス用語や略語の定義・解説（該当がなければ省略可）

            抽出された重要要素リスト:
            {extracted_elements}
            """
            else:
                prompt = f"""
            あなたは初心者に優しく教えるエキスパートインストラクターです。
            抽出された重要要素リストおよび元のドキュメントを読み取り、初心者向けに完全整理・再構成して以下のフォーマットで出力してください。

            【出力フォーマット絶対遵守】
            ・抽出要素リストにある具体例、数値、注意事項、条件分岐は一切省略せず、適切なセクションにすべて含めてください。
            ・抽象的な短文にまとめず、初心者が迷わないように元の解像度を保持して分かりやすく記述してください。
            ・箇条書きは必ず `- ` (ハイフン＋スペース) で始めてください。

            [TITLE]
            初心者にもわかりやすいマニュアルのタイトル（1行）

            [SUMMARY]
            このマニュアルの全体像と目的を、必要なステップや重要条件を含めて親しみやすい言葉で3-4文で説明してください。

            [KEY_POINTS]
            - 初心者がまず覚えるべき重要ポイントや注意点（省略せず具体的に箇条書き）

            [SECTIONS]
            ## 1. 準備・必要なもの
            内容や必要な道具・条件を詳細に記述

            ## 2. 実行手順
            順番にステップバイステップで、細かい注意点も含めて記述

            ## 3. トラブルシューティング・注意点
            困ったときの対応や例外ケースを具体的に記述
            {table_instruction}

            [GLOSSARY]
            - 専門用語: 初心者向けの易しい解説

            抽出された重要要素リスト:
            {extracted_elements}
            """
            
            result_text = self._generate_with_retry(prompt, images=images if images else None)
            
            title = "手書き整理マニュアル"
            summary = ""
            key_points = []
            sections = []
            glossary = []
            
            # Parsing markers
            import re
            
            if "[TITLE]" in result_text:
                parts = result_text.split("[TITLE]")
                rest = parts[1]
                
                if "[SUMMARY]" in rest:
                    title_part, rest = rest.split("[SUMMARY]", 1)
                    title = title_part.strip().split('\n')[0].strip()
                    title = re.sub(r'^[【「\[\(]*(.*?)[】」\]\)]*$', r'\1', title)
                    
                    if "[KEY_POINTS]" in rest:
                        summary_part, rest = rest.split("[KEY_POINTS]", 1)
                        summary = summary_part.strip()
                        
                        if "[SECTIONS]" in rest:
                            keypoints_part, rest = rest.split("[SECTIONS]", 1)
                            for line in keypoints_part.strip().split('\n'):
                                line_s = line.strip()
                                if line_s.startswith('- ') or line_s.startswith('• '):
                                    point = line_s[2:].strip()
                                    if point:
                                        key_points.append(point)
                            
                            if "[GLOSSARY]" in rest:
                                sections_part, glossary_part = rest.split("[GLOSSARY]", 1)
                                
                                # Parse glossary
                                for line in glossary_part.strip().split('\n'):
                                    if ':' in line or '：' in line:
                                        sep = ':' if ':' in line else '：'
                                        term_parts = line.split(sep, 1)
                                        term = re.sub(r'^[-•*]\s*', '', term_parts[0]).strip()
                                        exp = term_parts[1].strip()
                                        if term and exp:
                                            glossary.append({'term': term, 'explanation': exp})
                            else:
                                sections_part = rest
                            
                            # Parse sections
                            current_section = None
                            for line in sections_part.strip().split('\n'):
                                if line.startswith('## '):
                                    if current_section:
                                        sections.append(current_section)
                                    sec_title = line[3:].strip()
                                    current_section = {'title': sec_title, 'content': []}
                                elif current_section is not None:
                                    if line.strip():
                                        current_section['content'].append(line.strip())
                            if current_section:
                                sections.append(current_section)
                            
                            for section in sections:
                                section['content'] = '\n'.join(section['content'])
            else:
                summary = result_text
                title = self.generate_title(text)
            
            if not title:
                title = self.generate_title(text, is_business_doc=is_business_doc)
                
            return GeminiSummaryResult(
                title=title,
                summary=summary,
                key_points=key_points,
                sections=sections,
                glossary=glossary
            )
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            raise Exception(f"Document processing failed: {e}")