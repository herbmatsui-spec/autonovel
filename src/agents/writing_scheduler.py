"""Writing scheduler for managing episode writing dependencies and execution order."""


class WritingScheduler:
    """スケジューラー - エピソードの依存関係と実行順序を管理する"""
    
    def __init__(self):
        """スケジューラーを初期化"""
        self.tasks = {}  # episode -> depends_on list
    
    def add_task(self, episode: int, depends_on: list[int]):
        """
        タスクを追加する。
        
        Args:
            episode: エピソード番号
            depends_on: 依存するエピソード番号のリスト
        """
        self.tasks[episode] = depends_on.copy() if depends_on else []
    
    def get_execution_order(self) -> list[int]:
        """
        依存関係に基づく実行順序をトポロジカルソートで取得する。
        
        Returns:
            実行すべきエピソード番号のリスト
        """
        # トポロジカルソート (Kahn's algorithm)
        # 入次数を計算
        in_degree = {episode: 0 for episode in self.tasks}
        for episode, dependencies in self.tasks.items():
            for dep in dependencies:
                if dep in self.tasks:
                    in_degree[episode] += 1
        
        # 入次数が0のノードをキューに追加
        queue = [episode for episode, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            # ここでは単純に最初の要素を取る（優先順位などのロジックは省略）
            episode = queue.pop(0)
            result.append(episode)
            
            # このエピソードに依存しているタスクの入次数を減らす
            for dependent_episode, dependencies in self.tasks.items():
                if episode in dependencies:
                    in_degree[dependent_episode] -= 1
                    if in_degree[dependent_episode] == 0:
                        queue.append(dependent_episode)
        
        # サイクルがある場合は、残りのタスクを追加（循環依存がある場合でも処理を続ける）
        if len(result) < len(self.tasks):
            # サイクルがあるエピソードを追加
            remaining = [ep for ep in self.tasks if ep not in result]
            result.extend(remaining)
        
        return result