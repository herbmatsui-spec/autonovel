"""
フックテンプレート辞書
"""

from __future__ import annotations

from typing import Dict, List

# フックテンプレート辞書
HOOK_TEMPLATES: Dict[str, List[str]] = {
    "mystery": [
        "なぜ、彼女は俺の名を知っていたのか──",
        "この鍵は、何を開けるために存在するのか？",
        "真犯人は、まさかあの人物だったとは…",
        "この声の主は、誰なのか？",
        "時間は戻らない。だが、真実だけは明らかになる"
    ],
    "threat": [
        "その時、空が裂けた。奴が来る",
        "警告は無視された。代償は大きすぎた",
        "影が動いた。これは、ただの偶然ではない",
        "彼らは俺の弱点を知っている。そして、それを狙っている",
        " silence は破られた。今、反撃の時が来た"
    ],
    "emotion": [
        "『……もう、離さない』彼女の手が、震えていた",
        "この思いを、言葉にすることはできないだろうか",
        "たとえ世界が終わっても、私はこの手を離さない",
        "涙は、言葉では表現しきれない想いの証だ",
        "たとえ傷ついても、また立ち上がる。なぜなら、君がいるから"
    ]
}


def get_hook_templates(hook_type: str) -> List[str]:
    """
    指定されたタイプのフックテンプレートを取得する
    
    Args:
        hook_type: フックタイプ ("mystery", "threat", "emotion")
        
    Returns:
        フックテンプレートのリスト
        
    Raises:
        ValueError: 不正なフックタイプが指定された場合
    """
    if hook_type not in HOOK_TEMPLATES:
        raise ValueError(f"Invalid hook type: {hook_type}. Must be one of {list(HOOK_TEMPLATES.keys())}")
    
    return HOOK_TEMPLATES[hook_type]


def get_all_hook_types() -> List[str]:
    """
    すべてのフックタイプを取得する
    
    Returns:
        フックタイプのリスト
    """
    return list(HOOK_TEMPLATES.keys())