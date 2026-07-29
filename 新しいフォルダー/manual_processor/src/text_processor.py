# manual_processor/src/text_processor.py
import re
import logging
from typing import List, Any
from dataclasses import dataclass

try:
    from src.ocr_processor import OCRResult
except ImportError:
    OCRResult = Any

logger = logging.getLogger(__name__)

@dataclass
class Section:
    """ドキュメントのセクション"""
    title: str
    content: str
    subsections: List['Section'] = None

    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []

def combine_ocr_results(ocr_results: List[Any]) -> str:
    """
    OCR結果を結合して完全なテキストを生成する
    
    Args:
        ocr_results: ページごとのOCR結果リスト
    
    Returns:
        結合されたテキスト
    """
    if not ocr_results:
        return ""
    
    # ページ番号でソート（念のため）
    sorted_results = sorted(ocr_results, key=lambda x: x.page_number)
    
    # 各ページのテキストを結合
    combined_text = ""
    for i, result in enumerate(sorted_results):
        if result.text:
            # ページ間に適切な区切りを入れる（改行2つで段落区切り）
            if i > 0:
                combined_text += "\n\n"
            combined_text += result.text
    
    logger.debug(f"OCR結果を結合しました: {len(sorted_results)}ページ, {len(combined_text)}文字")
    return combined_text

def clean_extracted_text(text: str) -> str:
    """
    抽出されたテキストをクリーニングする
    
    Args:
        text: クリーニング対象のテキスト
    
    Returns:
        クリーニングされたテキスト
    """
    if not text:
        return ""
    
    # 1. 制御文字の除去（ただし改行とタブは保持）
    # ただし、連続する制御文字は空白に置換
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # 2. 全角スペースを半角スペースに変換
    text = text.replace('　', ' ')
    
    # 3. 連続する空白を単一のスペースに変換（ただし改行は保持）
    # 改行前後の空白は trim
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # 行頭・行末の空白を除去
        line = line.strip()
        # 行内の連続する空白を単一スペースに
        line = re.sub(r'\s+', ' ', line)
        cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # 4. 連続する改行を最大3つに制限（段落間の空行を保つため）
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    
    # 5. 行頭・行末の空白を除去
    text = text.strip()
    
    logger.debug(f"テキストをクリーニングしました: {len(text)}文字")
    return text

def normalize_japanese_text(text: str) -> str:
    """
    日本語テキストを正規化する（表記ゆれの吸収など）
    
    Args:
        text: 正規化対象のテキスト
    
    Returns:
        正規化されたテキスト
    """
    if not text:
        return ""
    
    # 1. 全角英数字を半角に変換
    # 英数字のみ対応（記号は別途処理が必要だが、ここでは簡易版）
    def convert_char(c):
        if 'Ａ' <= c <= 'Ｚ':
            return chr(ord(c) - ord('Ａ') + ord('A'))
        if 'ａ' <= c <= 'ｚ':
            return chr(ord(c) - ord('ａ') + ord('a'))
        if '０' <= c <= '９':
            return chr(ord(c) - ord('０') + ord('0'))
        return c
    
    text = ''.join(convert_char(c) for c in text)
    
    # 2. ひらがなとカタカナの変換は保守的に扱わない（文脈によるため）
    # 必要に応じて外部ライブラリ（jaconv等）を使用することを推奨
    
    logger.debug(f"日本語テキストを正規化しました: {len(text)}文字")
    return text

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    テキストからキーワードを抽出する（簡易実装）
    
    Args:
        text: キーワードを抽出するテキスト
        max_keywords: 抽出する最大キーワード数
    
    Returns:
        キーワードのリスト
    """
    if not text or max_keywords <= 0:
        return []
    
    # 簡易実装: 頻出単語を抽出（実際はTF-IDF等を使用するべき）
    # ここでは長めの単語（2文字以上）を抽出し、出現頻度でソート
    
    # 日本語とアルファベットの単語を抽出
    # 日本語: 連続するひらがな・カタカナ・漢字
    # アルファベット: 連続する英字
    words = re.findall(r'[あ-んア-ン一-龥]+|[a-zA-Z]+', text)
    
    # ストップワードの簡易リスト（実際はより充実させるべき）
    stop_words = {'の', 'に', 'は', 'を', 'た', 'が', 'で', 'て', 'と', 'し', 'れ', 'さ', 'ある', 'いる', 'も', 'する', 'から', 'な', 'こと', 'として', 'い', 'や', 'など', 'なら', 'もの', 'なぜなら', 'ただし', 'しかし'}
    
    # 単語の出現頻度を計算
    word_count = {}
    for word in words:
        if word.lower() not in stop_words and len(word) >= 2:
            word_count[word] = word_count.get(word, 0) + 1
    
    # 頻度でソートして上位を取得
    sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
    keywords = [word for word, count in sorted_words[:max_keywords]]
    
    logger.debug(f"キーワードを抽出しました: {keywords}")
    return keywords

def split_into_sentences(text: str) -> List[str]:
    """
    テキストを文に分割する
    
    Args:
        text: 分割対象のテキスト
    
    Returns:
        文のリスト
    """
    if not text:
        return []
    
    # 簡易的な文区切り（実際はより高度な処理が必要）
    # 日本語: 。！？で区切り、英語: .!?で区切り
    sentences = re.split(r'[。！？.!?]+', text)
    # 空の要素を除去
    sentences = [s.strip() for s in sentences if s.strip()]
    
    logger.debug(f"テキストを{len(sentences)}文に分割しました")
    return sentences

def remove_duplicate_lines(text: str) -> str:
    """
    重複行を削除する
    
    Args:
        text: 重複行を削除するテキスト
    
    Returns:
        重複行が削除されたテキスト
    """
    if not text:
        return ""
    
    lines = text.split('\n')
    seen = set()
    unique_lines = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)
    
    result = '\n'.join(unique_lines)
    logger.debug(f"重複行を削除しました: {len(lines)} -> {len(unique_lines)}行")
    return result