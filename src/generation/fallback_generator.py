import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class FallbackGenerator:
    """
    LLM API エラー/タイムアウト時の静的ルールベース代替ストーリージェネレーター。
    プライマリジェネレーターが失敗した場合にフォールバックする。
    """

    def __init__(self, primary_generator: Optional[Callable] = None):
        """
        フォールバックジェネレーターを初期化。
        
        Args:
            primary_generator: プライマリジェネレーター関数。
                             Noneの場合は常にフォールバックを使用する。
        """
        self.primary_generator = primary_generator
        self.logger = logger
    
    def generate(self, genre: str, length: int, keywords: str = "") -> str:
        """
        ストーリーを生成する。プライマリジェネレーターが失敗した場合はフォールバックを使用する。
        
        Args:
            genre: ストーリーのジャンル
            length: 目標文字数
            keywords: キーワード（カンマ区切り）
            
        Returns:
            生成されたストーリーテキスト
        """
        if self.primary_generator is not None:
            try:
                return self.primary_generator(genre, length, keywords)
            except Exception as e:
                self.logger.warning(
                    f"プライマリジェネレーターが失敗しました: {e}. フォールバックを使用します。",
                    exc_info=True
                )
        
        # フォールバック: 静的ルールベースのストーリーを生成
        return self._generate_fallback_story(genre, length, keywords)
    
    def _generate_fallback_story(self, genre: str, length: int, keywords: str) -> str:
        """
        静的ルールベースのフォールバックストーリーを生成。
        実際の実装では、より高度なルールベースジェネレーターを使用するかもしれない。
        """
        # ジャンル別のテンプレート
        templates = {
            "ファンタジー": "古代の王国で、若き勇者は伝説の剣を求めて旅に出た。途中で魔物と戦い、仲間を得ながら目的の場所に到着した。",
            "ラブコメ": "高校に転入した主人公は、クラスの人気者と偶然出会い。誤解とすれ違いを繰り返しながら、次第に惹かれ合っていく。",
            "SF": "22世紀の宇宙開発時代、主人公は新惑星の調査隊に選抜される。未知の生命体との遭遇と、船内の陰謀が待っていた。",
            "ミステリー": "静かな田舎町で起こった連続殺人事件。探偵は証拠を集め、容疑者の証言を丁寧に分析して真相に迫る。",
            "歴史": "江戸時代末期、維新志士として生きる主人公は、新しい時代への変革を願いながら日々を過ごした。"
        }
        
        base_story = templates.get(genre, "これはサンプルストーリーです。")
        # 必要な長さになるまで繰り返す
        repeated = (base_story * ((length // len(base_story)) + 1))[:length]
        
        # キーワードを含める簡易的な処理（実際にはもっと高度にするかもしれない）
        if keywords:
            keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
            if keyword_list:
                # ストーリーの途中にキーワードを挿入する簡易的な試み
                # 実際にはもっと自然に組み込むべき
                insert_point = len(repeated) // 2
                keyword_text = " " + ", ".join(keyword_list) + " "
                repeated = repeated[:insert_point] + keyword_text + repeated[insert_point:]
                # 長さを調整（オーバーしたら切る）
                if len(repeated) > length:
                    repeated = repeated[:length]
        
        return repeated


# デフォルトのフォールバックジェネレーターインスタンス
default_fallback_generator = FallbackGenerator()


if __name__ == "__main__":
    # 簡単な動作テスト
    import logging
    logging.basicConfig(level=logging.INFO)
    
    generator = FallbackGenerator()
    
    # フォールバックのみを使用するテスト
    result = generator.generate("ファンタジー", 500, "魔法, 剣")
    print("生成結果:")
    print(result)
    print(f"長さ: {len(result)} 文字")