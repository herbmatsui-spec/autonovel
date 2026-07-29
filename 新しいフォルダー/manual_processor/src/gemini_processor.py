# manual_processor/src/gemini_processor.py
import logging
import re
from typing import List, Optional
from dataclasses import dataclass, field

try:
    from google import genai
    from google.api_core.exceptions import GoogleAPICallError, RetryError, DeadlineExceeded
    _HAS_GEMINI = True
except ImportError:
    _HAS_GEMINI = False
    genai = None
    GoogleAPICallError = Exception
    RetryError = Exception
    DeadlineExceeded = Exception

from .text_processor import Section

logger = logging.getLogger(__name__)

@dataclass
class GeminiResult:
    """Gemini API処理結果"""
    summary: str
    key_points: List[str]
    sections: List[Section]
    difficulty_level: str

class GeminiAPIError(Exception):
    """Gemini API関連のエラー"""
    pass

class GeminiProcessor:
    """Google Gemini APIを使用したテキスト要約・構造化クラス"""
    
    def __init__(self, api_key: Optional[str] = None, 
                 model_name: str = "gemini-3.1-flash-lite",
                 temperature: float = 0.3,
                 max_output_tokens: int = 2048):
        """
        Args:
            api_key: Google Gemini APIキー
            model_name: 使用するモデル名 (最新のSDKに合わせてデフォルトを調整)
            temperature: 生成温度（0.0-1.0）
            max_output_tokens: 最大出力トークン数
        """
        if not _HAS_GEMINI:
            raise GeminiAPIError("google-genai ライブラリがインストールされていません")
        
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        
        # APIクライアントの初期化
        api_key_to_use = api_key or __import__('os').environ.get("GOOGLE_API_KEY")
        if not api_key_to_use:
            raise GeminiAPIError("Gemini APIキーが設定されていません")
        
        try:
            self.client = genai.Client(api_key=api_key_to_use)
            logger.info(f"Geminiクライアントを初期化しました: {model_name}")
        except Exception as e:
            logger.error(f"Geminiクライアント初期化エラー: {e}")
            raise GeminiAPIError(f"Geminiクライアントの初期化に失敗しました: {e}")
    
    def _chunk_text(self, text: str, max_tokens: int = 3000) -> List[str]:
        """テキストをチャンクに分割する（トークン制限対応）"""
        if not text:
            return []
        
        # 簡易的なチャンク分割（1チャンクあたりの文字数で制限）
        # 1トークン ≈ 4文字 と仮定
        max_chars = max_tokens * 4
        
        if len(text) <= max_chars:
            return [text]
        
        # 段落で分割
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= max_chars:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        logger.debug(f"テキストを{len(chunks)}チャンクに分割しました")
        return chunks if chunks else [""]
    
    def summarize_text(self, text: str, target_audience: str = "beginner",
                      max_length: Optional[int] = None,
                      max_tokens: Optional[int] = None) -> str:
        """
        テキストを要約する
        """
        if not text or not text.strip():
            return ""
        
        # テキストが長すぎる場合はチャンクに分割
        max_tokens_to_use = (max_tokens * 20) if (max_tokens and max_tokens < 1000) else (max_tokens or 3000)
        chunks = self._chunk_text(text, max_tokens=max_tokens_to_use)
        
        summaries = []
        for i, chunk in enumerate(chunks):
            try:
                prompt = f"""
あなたは親切でわかりやすい説明が得意なインストラクターです。
次の技術文書を{target_audience}レベルの読者でも理解できるように、
重要なポイントを簡潔にまとめてください。

以下の点に注意してください：
1. 専門用語は必ず平易な言語に言い換えるか、説明を加える
2. 長い説明は箇条書きにして見やすくする
3. 重要な概念は強調する
4. 例やanalogiesを使って理解を助ける
5. 出力はMarkdown形式でフォーマットしてください

元のテキスト：
{chunk}
"""
                # google-genai SDKの形式で呼び出し
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config={
                        "temperature": self.temperature,
                        "max_output_tokens": self.max_output_tokens,
                    }
                )
                
                if response.text:
                    summary_part = response.text
                    if max_length and len(summary_part) > max_length:
                        summary_part = summary_part[:max_length]
                    summaries.append(summary_part)
                else:
                    logger.warning(f"チャンク {i+1} の要約でレスポンスが空でした")
                    
            except Exception as e:
                logger.error(f"チャンク {i+1} の要約中にエラー: {e}")
                raise GeminiAPIError(f"テキスト要約に失敗しました: {e}")
        
        combined_summary = "\n\n".join(summaries)
        logger.info(f"テキスト要約完了: {len(text)}文字 -> {len(combined_summary)}文字")
        return combined_summary
    
    def extract_key_points(self, text: str, max_points: int = 10) -> List[str]:
        """
        テキストから重要ポイントを抽出する
        """
        if not text or not text.strip():
            return []
        
        try:
            prompt = f"""
あなたは技術文書の重要ポイントを抽出する専門家です。
次のテキストから、初心者が最初に理解すべき重要なポイントを{max_points}つ以内で箇条書きにして抽出してください。

各ポイントは：
1. 1文で完結する簡潔な表現
2. 専門用語は避け、必要最低限の用語のみ使用
3. 具体的な数値や手順は含める
4. 主観的な評価ではなく、客観的な事実を述べる

出力形式：
- ポイント1
- ポイント2
- ポイント3
...

元のテキスト：
{text}
"""
            # google-genai SDKの形式で呼び出し
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_output_tokens,
                }
            )
            
            if not response.text:
                logger.warning("キーポイント抽出でレスポンスが空でした")
                return []
            
            # 箇条書き形式のレスポンスをパース
            lines = response.text.strip().split('\n')
            key_points = []
            for line in lines:
                line = line.strip()
                # 箇条書きのマーカーを除去
                line = re.sub(r'^[-•*]\s*', '', line)
                if line and len(key_points) < max_points:
                    key_points.append(line)
            
            logger.info(f"キーポイントを抽出しました: {len(key_points)}個")
            return key_points
            
        except Exception as e:
            logger.error(f"キーポイント抽出中にエラー: {e}")
            raise GeminiAPIError(f"キーポイント抽出に失敗しました: {e}")
    
    def process_document(self, text: str, target_audience: str = "beginner") -> GeminiResult:
        """
        テキストを処理して要約とキーポイントを抽出する
        """
        if not text or not text.strip():
            return GeminiResult(
                summary="",
                key_points=[],
                sections=[],
                difficulty_level=target_audience
            )
        
        try:
            # 要約を生成
            summary = self.summarize_text(text, target_audience)
            
            # キーポイントを抽出
            key_points = self.extract_key_points(text)
            
            # セクション構造を作成（簡易版）
            sections = []
            if summary:
                sections.append(Section(
                    title="概要",
                    content=summary,
                    subsections=[]
                ))
            
            if key_points:
                sections.append(Section(
                    title="重要ポイント",
                    content="\n".join(f"- {point}" for point in key_points),
                    subsections=[]
                ))
            
            result = GeminiResult(
                summary=summary,
                key_points=key_points,
                sections=sections,
                difficulty_level=target_audience
            )
            
            logger.info(f"ドキュメント処理完了: 要約={len(summary)}文字, ポイント={len(key_points)}個")
            return result
            
        except Exception as e:
            logger.error(f"ドキュメント処理中にエラー: {e}")
            raise GeminiAPIError(f"ドキュメント処理に失敗しました: {e}")
