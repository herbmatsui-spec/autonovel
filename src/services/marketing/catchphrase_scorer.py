from src.config.kakuyomu_syntax_patterns import (
    CATCHPHRASE_MAX_LENGTH,
    CATCHPHRASE_OPTIMAL_MIN,
    CATCHPHRASE_OPTIMAL_MAX,
    CATCHPHRASE_POWER_WORDS,
)


def score_catchphrase_ctr(catchphrase: str) -> int:
    """
    カクヨム特化キャッチコピーCTRスコアリングエンジン（0〜100点）
    
    Args:
        catchphrase: 評価対象のキャッチコピー文字列
        
    Returns:
        int: CTRスコア（0〜100点）
    """
    # 35文字以内厳守（36字以上は0点判定）
    if len(catchphrase) > CATCHPHRASE_MAX_LENGTH:
        return 0
    
    score = 0
    
    # スマホ視認性（15〜32字で満点加算）
    if CATCHPHRASE_OPTIMAL_MIN <= len(catchphrase) <= CATCHPHRASE_OPTIMAL_MAX:
        score += 40
    elif len(catchphrase) < CATCHPHRASE_OPTIMAL_MIN:
        # 15字未満は減点
        score += max(0, 40 - (CATCHPHRASE_OPTIMAL_MIN - len(catchphrase)) * 2)
    else:
        # 33-35字は減点
        score += max(0, 40 - (len(catchphrase) - CATCHPHRASE_OPTIMAL_MAX) * 2)
    
    # パワーワード含有判定（各ワード10点、最大30点）
    power_word_count = sum(1 for word in CATCHPHRASE_POWER_WORDS if word in catchphrase)
    score += min(power_word_count * 10, 30)
    
    # カギ括弧「」や記号（――、！？）のフック判定（各5点、最大20点）
    hook_chars = ['「', '」', '――', '！', '？']
    hook_count = sum(1 for char in hook_chars if char in catchphrase)
    score += min(hook_count * 5, 20)
    
    # 基礎点（最低限の評価）
    score += 10
    
    # 100点を超えないように調整
    return min(score, 100)