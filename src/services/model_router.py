from config import get_config


class ModelTier:
    """タスク難易度に応じたモデル層の定義"""

    @classmethod
    def get_tier_model(cls, tier: int) -> str:
        cfg = get_config()
        if tier == 1:
            # 高度な推論、プロット構築、監査
            return cfg.model_planning
        elif tier == 2:
            # 通常の本文生成、バランス型
            return cfg.model_writing
        else:
            # 高速な校正、要約、単純な抽出 (Ollama / vLLM などのローカル軽量モデルやクラウドAPI)
            return cfg.model_ultra_stable

class ModelRouter:
    """タスクの性質と難易度に基づいて最適なモデルをルーティングする"""

    @classmethod
    def get_model_for_task(cls, task_type: str, difficulty_score: int = 50, current_tension: int = 0) -> str:
        """
        タスクの難易度や重要性（ストレス値）に応じてモデルを選択する
        
        Args:
            task_type: タスクの種類 ("planning", "writing", "audit", "formatting" など)
            difficulty_score: プロットの複雑さや重要度 (0-100)
            current_tension: 現在の累積緊張値
        """
        # 1. 企画立案、論理監査などの高難易度タスクは一律 Tier 1
        if task_type in ["planning", "audit", "critique", "plot_expansion"]:
            return ModelTier.get_tier_model(1)

        # 2. 本文生成タスクは文脈に応じて分岐
        elif task_type == "writing":
            # 難易度が高い（情報が複雑）、またはストレスが閾値に近い場合は Tier 1
            cfg = get_config()
            if difficulty_score >= 80 or current_tension >= cfg.stress_catharsis_threshold:
                return ModelTier.get_tier_model(1)
            # 標準的な執筆は Tier 2
            return ModelTier.get_tier_model(2)

        # 3. テキスト整形や要約などの単純処理は Tier 3
        elif task_type in ["formatting", "summarization", "style_extraction", "sanitizer"]:
            return ModelTier.get_tier_model(3)

        # デフォルトはバランス型
        return ModelTier.get_tier_model(2)
