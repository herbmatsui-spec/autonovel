"""
IFルート分岐システム
小説の分岐ルートを管理し、読者の選択に応じてストーリーを変化させる
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from src.easy_mode.pipeline import EpisodeResult, SeriesResult

logger = logging.getLogger(__name__)


class BranchType(str, Enum):
    """分岐タイプ"""
    CHOICE = "choice"           # 読者の選択肢
    CONDITIONAL = "conditional"  # 条件分岐（フラグ・数値判定）
    RANDOM = "random"            # 確率分岐
    LOOP = "loop"                # ループ分岐（周回プレイ）
    MERGE = "merge"              # ルート合流


class ConditionOperator(str, Enum):
    """条件演算子"""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "ge"
    LESS_EQUAL = "le"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"


@dataclass
class BranchCondition:
    """分岐条件"""
    variable: str
    operator: ConditionOperator
    value: Any
    description: str = ""

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """条件判定（ネストしたキー対応）"""
        # ネストしたキーを取得（ドット区切り対応）
        var_value = context
        for key in self.variable.split('.'):
            if isinstance(var_value, dict) and key in var_value:
                var_value = var_value[key]
            else:
                var_value = None
                break

        if var_value is None:
            return False

        if self.operator == ConditionOperator.EQUALS:
            return var_value == self.value
        elif self.operator == ConditionOperator.NOT_EQUALS:
            return var_value != self.value
        elif self.operator == ConditionOperator.GREATER_THAN:
            return var_value > self.value
        elif self.operator == ConditionOperator.LESS_THAN:
            return var_value < self.value
        elif self.operator == ConditionOperator.GREATER_EQUAL:
            return var_value >= self.value
        elif self.operator == ConditionOperator.LESS_EQUAL:
            return var_value <= self.value
        elif self.operator == ConditionOperator.CONTAINS:
            return self.value in str(var_value)
        elif self.operator == ConditionOperator.NOT_CONTAINS:
            return self.value not in str(var_value)
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable": self.variable,
            "operator": self.operator.value,
            "value": self.value,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BranchCondition":
        return cls(
            variable=data["variable"],
            operator=ConditionOperator(data["operator"]),
            value=data["value"],
            description=data.get("description", "")
        )


@dataclass
class RouteChoice:
    """選択肢"""
    id: str
    text: str
    conditions: List[BranchCondition] = field(default_factory=list)
    target_node_id: str = ""
    effects: Dict[str, Any] = field(default_factory=dict)  # 選択時の副作用（フラグ変更等）
    priority: int = 0  # 表示優先度

    def is_available(self, context: Dict[str, Any]) -> bool:
        """選択可能か判定"""
        if not self.conditions:
            return True
        return all(c.evaluate(context) for c in self.conditions)

    def apply_effects(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """副作用を適用（ネストしたキー対応）"""
        new_context = json.loads(json.dumps(context))  # 深いコピー

        for key, value in self.effects.items():
            keys = key.split('.')
            target = new_context
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            target[keys[-1]] = value

        return new_context


@dataclass
class RouteNode:
    """ルートノード"""
    id: str
    episode_num: int
    content: str
    branch_type: BranchType
    choices: List[RouteChoice] = field(default_factory=list)
    merge_target: Optional[str] = None  # MERGEタイプの場合の合流先
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_ids: List[str] = field(default_factory=list)

    def get_available_choices(self, context: Dict[str, Any]) -> List[RouteChoice]:
        """利用可能な選択肢を取得"""
        return [c for c in self.choices if c.is_available(context)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "episode_num": self.episode_num,
            "content": self.content,
            "branch_type": self.branch_type.value,
            "choices": [
                {
                    "id": c.id,
                    "text": c.text,
                    "conditions": [cond.to_dict() for cond in c.conditions],
                    "target_node_id": c.target_node_id,
                    "effects": c.effects,
                    "priority": c.priority
                }
                for c in self.choices
            ],
            "merge_target": self.merge_target,
            "metadata": self.metadata,
            "parent_ids": self.parent_ids
        }


@dataclass
class IFRouteGraph:
    """IFルートグラフ（分岐構造全体）"""
    nodes: Dict[str, RouteNode] = field(default_factory=dict)
    entry_node_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: RouteNode) -> None:
        self.nodes[node.id] = node

    def get_node(self, node_id: str) -> Optional[RouteNode]:
        return self.nodes.get(node_id)

    def get_next_nodes(self, node_id: str, context: Dict[str, Any]) -> List[RouteNode]:
        """次のノード群を取得"""
        node = self.get_node(node_id)
        if not node:
            return []

        if node.branch_type == BranchType.MERGE and node.merge_target:
            target = self.get_node(node.merge_target)
            return [target] if target else []

        next_nodes = []
        for choice in node.get_available_choices(context):
            target = self.get_node(choice.target_node_id)
            if target:
                # 副作用を適用した新しいコンテキストで評価
                new_context = choice.apply_effects(context)
                next_nodes.append(target)
        return next_nodes

    def validate(self) -> List[str]:
        """グラフの整合性チェック"""
        errors = []

        # エントリーノード存在確認
        if self.entry_node_id and self.entry_node_id not in self.nodes:
            errors.append(f"Entry node {self.entry_node_id} not found")

        # 孤立ノードチェック
        reachable = set()
        def traverse(node_id: str, visited: Set[str] = None):
            if visited is None:
                visited = set()
            if node_id in visited or node_id not in self.nodes:
                return
            visited.add(node_id)
            reachable.add(node_id)
            node = self.nodes[node_id]
            for choice in node.choices:
                if choice.target_node_id:
                    traverse(choice.target_node_id, visited)
            if node.merge_target:
                traverse(node.merge_target, visited)

        if self.entry_node_id:
            traverse(self.entry_node_id)

        for node_id in self.nodes:
            if node_id not in reachable:
                errors.append(f"Unreachable node: {node_id}")

        # 選択肢のターゲット存在確認
        for node in self.nodes.values():
            for choice in node.choices:
                if choice.target_node_id and choice.target_node_id not in self.nodes:
                    errors.append(f"Node {node.id}: choice {choice.id} targets missing node {choice.target_node_id}")

        return errors


class IFRouteGenerator:
    """IFルート生成器"""

    def __init__(self, genre: str, preset: Dict[str, Any]):
        self.genre = genre
        self.preset = preset
        self.graph = IFRouteGraph()
        self._context: Dict[str, Any] = {}
        self._flags: Dict[str, Any] = {}
        self._variables: Dict[str, Any] = {}

    def set_initial_context(self, context: Dict[str, Any]) -> None:
        """初期コンテキスト設定"""
        self._context = context.copy()
        self._flags = context.get("flags", {}).copy()
        self._variables = context.get("variables", {}).copy()

    def generate_from_series(self, series: SeriesResult) -> IFRouteGraph:
        """シリーズ結果からIFルートグラフを生成"""
        self.graph = IFRouteGraph()

        # エントリーノード作成（プロローグ）
        entry_node = self._create_prologue_node(series)
        self.graph.entry_node_id = entry_node.id
        self.graph.add_node(entry_node)

        # 各話のノード作成
        prev_node_id = entry_node.id
        for i, episode in enumerate(series.episodes):
            episode_nodes = self._create_episode_nodes(episode, i + 1, prev_node_id, series)
            for node in episode_nodes:
                self.graph.add_node(node)
                if node.parent_ids and prev_node_id in node.parent_ids:
                    prev_node_id = node.id

        # 不足しているターゲットノードを追加
        self._add_missing_target_nodes(series)

        # 検証
        errors = self.graph.validate()
        if errors:
            logger.warning(f"IF route graph validation errors: {errors}")

        return self.graph

    def _create_prologue_node(self, series: SeriesResult) -> RouteNode:
        """プロローグノード作成"""
        content = series.metadata.get("prologue", "") or f"{series.title} - 始まりの物語"

        # 最初の選択肢：物語の始まり方を選ぶ
        choices = [
            RouteChoice(
                id="prologue_normal",
                text="普通に始める",
                target_node_id="ep1_main",
                priority=10
            ),
            RouteChoice(
                id="prologue_flashback",
                text="過去の回想から始める",
                target_node_id="ep1_flashback",
                effects={"start_type": "flashback"},
                priority=5
            ),
            RouteChoice(
                id="prologue_action",
                text="アクションシーンから始める",
                target_node_id="ep1_action",
                effects={"start_type": "action"},
                priority=5
            )
        ]

        # ジャンル別の追加選択肢
        if self.genre == "loop":
            choices.append(RouteChoice(
                id="prologue_true_route",
                text="最初のループから始める（真エンドルート）",
                target_node_id="ep1_true_route",
                effects={"route_type": "true_end", "loop_count": 1},
                priority=1
            ))
        elif self.genre == "aku_reijo":
            choices.append(RouteChoice(
                id="prologue_flag_avoid",
                text="断罪フラグを最初から回避する",
                target_node_id="ep1_flag_avoid",
                effects={"route_type": "flag_avoid"},
                priority=1
            ))

        return RouteNode(
            id="prologue",
            episode_num=0,
            content=content,
            branch_type=BranchType.CHOICE,
            choices=choices,
            metadata={"type": "prologue", "genre": self.genre}
        )

    def _create_episode_nodes(
        self,
        episode: EpisodeResult,
        ep_num: int,
        prev_node_id: str,
        series: SeriesResult
    ) -> List[RouteNode]:
        """エピソードのノード群を作成"""
        nodes = []

        # メインルートノード
        main_node = RouteNode(
            id=f"ep{ep_num}_main",
            episode_num=ep_num,
            content=episode.content,
            branch_type=BranchType.CHOICE,
            parent_ids=[prev_node_id],
            metadata={"route": "main", "original_episode": ep_num}
        )

        # カタルシス話の場合、分岐を追加
        if episode.metadata.get("plot", {}).get("is_catharsis", False):
            main_node.choices.extend(self._create_catharsis_choices(ep_num, series))
        else:
            main_node.choices.extend(self._create_normal_choices(ep_num, series))

        nodes.append(main_node)

        # サブルート（条件分岐）作成
        if self._should_create_subroute(ep_num, series):
            sub_nodes = self._create_subroute_nodes(ep_num, main_node.id, series)
            nodes.extend(sub_nodes)

        # 合流ノード作成（最終話付近）
        if ep_num >= len([e for e in series.episodes]) - 1:
            merge_node = self._create_merge_node(ep_num, nodes)
            if merge_node:
                nodes.append(merge_node)

        return nodes

    def _create_catharsis_choices(self, ep_num: int, series: SeriesResult) -> List[RouteChoice]:
        """カタルシス話用の選択肢"""
        choices = []

        # ザマァ系のカタルシス選択肢
        if self.genre == "zarma":
            choices.extend([
                RouteChoice(
                    id=f"ep{ep_num}_catharsis_complete",
                    text="完全なザマァで終わらせる",
                    target_node_id=f"ep{ep_num}_catharsis_complete",
                    effects={"catharsis_level": "complete", "satisfaction": "max"},
                    priority=10
                ),
                RouteChoice(
                    id=f"ep{ep_num}_catharsis_merciful",
                    text="情けをかけて終わらせる",
                    target_node_id=f"ep{ep_num}_catharsis_merciful",
                    effects={"catharsis_level": "merciful", "flag_mercy": True},
                    priority=5
                ),
                RouteChoice(
                    id=f"ep{ep_num}_catharsis_twist",
                    text="さらなる裏切りを暴く",
                    target_node_id=f"ep{ep_num}_catharsis_twist",
                    effects={"catharsis_level": "twist", "hidden_truth": True},
                    priority=3
                )
            ])
        elif self.genre == "aku_reijo":
            choices.extend([
                RouteChoice(
                    id=f"ep{ep_num}_happy_end",
                    text="ハッピーエンド（溺愛ルート）",
                    target_node_id=f"ep{ep_num}_happy_end",
                    effects={"ending": "happy", "yuri_flag": True},
                    priority=10
                ),
                RouteChoice(
                    id=f"ep{ep_num}_bittersweet",
                    text="ビターエンド（犠牲の愛）",
                    target_node_id=f"ep{ep_num}_bittersweet",
                    effects={"ending": "bittersweet", "sacrifice": True},
                    priority=5
                ),
                RouteChoice(
                    id=f"ep{ep_num}_open_end",
                    text="オープンエンド（続編へ）",
                    target_node_id=f"ep{ep_num}_open_end",
                    effects={"ending": "open", "sequel_hook": True},
                    priority=3
                )
            ])
        else:
            # 汎用カタルシス選択肢
            choices.extend([
                RouteChoice(
                    id=f"ep{ep_num}_catharsis_standard",
                    text="王道のカタルシス",
                    target_node_id=f"ep{ep_num}_catharsis_standard",
                    effects={"catharsis": "standard"},
                    priority=10
                ),
                RouteChoice(
                    id=f"ep{ep_num}_catharsis_subvert",
                    text="あえてカタルシスを裏切る",
                    target_node_id=f"ep{ep_num}_catharsis_subvert",
                    effects={"catharsis": "subverted", "dark_turn": True},
                    priority=3
                )
            ])

        return choices

    def _create_normal_choices(self, ep_num: int, series: SeriesResult) -> List[RouteChoice]:
        """通常話用の選択肢"""
        choices = [
            RouteChoice(
                id=f"ep{ep_num}_continue_main",
                text="メインストーリーを進める",
                target_node_id=f"ep{ep_num+1}_main" if ep_num < 8 else "ending_main",
                priority=10
            ),
            RouteChoice(
                id=f"ep{ep_num}_side_event",
                text="サイドイベントを見る",
                target_node_id=f"ep{ep_num}_side",
                effects={"side_event": True, "bonus_content": True},
                priority=5
            )
        ]

        # ジャンル別の特別選択肢
        if self.genre == "loop":
            choices.append(RouteChoice(
                id=f"ep{ep_num}_loop_optimize",
                text="ループ知識を使って最適化する",
                target_node_id=f"ep{ep_num}_optimized",
                effects={"optimization_level": ep_num, "knowledge_retention": True},
                priority=8
            ))
        elif self.genre == "cheat_tensei":
            choices.append(RouteChoice(
                id=f"ep{ep_num}_skill_experiment",
                text="新しいスキル組み合わせを試す",
                target_node_id=f"ep{ep_num}_skill_combo",
                effects={"skill_experiment": True, "new_combo": True},
                priority=5
            ))
        elif self.genre == "ts_tensei":
            choices.append(RouteChoice(
                id=f"ep{ep_num}_yuri_deepen",
                text="百合関係を深める",
                target_node_id=f"ep{ep_num}_yuri_scene",
                effects={"yuri_progress": True, "intimacy_up": True},
                priority=8
            ))

        return choices

    def _should_create_subroute(self, ep_num: int, series: SeriesResult) -> bool:
        """サブルート作成判定"""
        # 3話、5話、7話あたりでサブルート作成
        if ep_num in [3, 5, 7]:
            return True
        # ジャンル特有の分岐点
        if self.genre == "loop" and ep_num == 1:
            return True
        if self.genre == "aku_reijo" and ep_num in [2, 4]:
            return True
        return False

    def _create_subroute_nodes(self, ep_num: int, parent_id: str, series: SeriesResult) -> List[RouteNode]:
        """サブルートノード作成"""
        nodes = []

        # 隠しルート
        hidden_node = RouteNode(
            id=f"ep{ep_num}_hidden",
            episode_num=ep_num,
            content=f"[隠しルート] {series.episodes[ep_num-1].content[:200]}...（展開が変わる）",
            branch_type=BranchType.CONDITIONAL,
            parent_ids=[parent_id],
            metadata={"route": "hidden", "unlock_condition": "special_flag"}
        )

        # 条件分岐
        hidden_node.choices = [
            RouteChoice(
                id=f"ep{ep_num}_hidden_continue",
                text="隠しルートを進む",
                target_node_id=f"ep{ep_num+1}_hidden",
                effects={"hidden_route": True},
                conditions=[
                    BranchCondition(
                        variable="flags.hidden_unlocked",
                        operator=ConditionOperator.EQUALS,
                        value=True,
                        description="隠しフラグが立っている"
                    )
                ],
                priority=1
            ),
            RouteChoice(
                id=f"ep{ep_num}_return_main",
                text="メインルートに戻る",
                target_node_id=f"ep{ep_num+1}_main",
                priority=5
            )
        ]

        nodes.append(hidden_node)

        # IF分岐（バッドエンドルート）
        if ep_num >= 4:
            bad_node = RouteNode(
                id=f"ep{ep_num}_bad",
                episode_num=ep_num,
                content="[バッドエンド分岐] 選択を誤った場合の結末...",
                branch_type=BranchType.CHOICE,
                parent_ids=[parent_id],
                metadata={"route": "bad_end", "ending_type": "bad"}
            )

            bad_node.choices = [
                RouteChoice(
                    id=f"ep{ep_num}_bad_accept",
                    text="この結末を受け入れる",
                    target_node_id=f"ending_bad_{ep_num}",
                    effects={"ending": "bad", "ep_num": ep_num},
                    priority=3
                ),
                RouteChoice(
                    id=f"ep{ep_num}_bad_retry",
                    text="やり直す（ループ/ロード）",
                    target_node_id=f"ep{ep_num}_main",
                    effects={"retry": True, "knowledge": True},
                    priority=7
                )
            ]

            nodes.append(bad_node)

        return nodes

    def _add_missing_target_nodes(self, series: SeriesResult) -> None:
        """不足しているターゲットノードを追加（連鎖的に解決）"""
        changed = True
        while changed:
            changed = False
            # 既存ノードIDを収集
            existing_ids = set(self.graph.nodes.keys())

            # 参照されているが存在しないノードIDを収集
            missing_ids = set()
            for node in self.graph.nodes.values():
                for choice in node.choices:
                    if choice.target_node_id and choice.target_node_id not in existing_ids:
                        missing_ids.add(choice.target_node_id)

            # 不足ノードを作成
            for node_id in missing_ids:
                node = self._create_target_node(node_id, series)
                if node:
                    self.graph.add_node(node)
                    changed = True

    def _create_target_node(self, node_id: str, series: SeriesResult) -> Optional[RouteNode]:
        """ターゲットノード作成"""
        # エンディング系
        if node_id.startswith("ending_"):
            return self._create_ending_node(node_id, series)

        # カタルシスバリエーション
        if "_catharsis_" in node_id:
            return self._create_catharsis_variant_node(node_id, series)

        # エンディング分岐（ハッピー、ビター、オープン等）
        if node_id.endswith(("_happy_end", "_bittersweet", "_open_end", "_true_route", "_flag_avoid")):
            return self._create_ending_variant_node(node_id, series)

        # プロローグ分岐（フラッシュバック、アクション開始等）
        if node_id in ["ep1_flashback", "ep1_action", "ep1_true_route"]:
            return self._create_prologue_variant_node(node_id)

        # サイドイベント
        if "_side" in node_id and not node_id.endswith("_side_event"):
            return self._create_side_event_node(node_id)

        # 最適化ルート
        if "_optimized" in node_id:
            return self._create_optimized_node(node_id)

        # スキルコンボ
        if "_skill_combo" in node_id:
            return self._create_skill_combo_node(node_id)

        # 百合シーン
        if "_yuri_scene" in node_id:
            return self._create_yuri_scene_node(node_id)

        # 隠しルート続き
        if "_hidden" in node_id and not node_id.endswith("_hidden"):
            return self._create_hidden_continuation_node(node_id)

        # バッドエンド
        if node_id.startswith("ending_bad_"):
            return self._create_bad_ending_node(node_id)

        # 真エンド・ノーマルエンド
        if node_id in ["ending_true", "ending_normal", "ending_main"]:
            return self._create_final_ending_node(node_id, series)

        # メインルート続き（ep{N+1}_main）
        if node_id.endswith("_main") and node_id.startswith("ep"):
            return self._create_main_continuation_node(node_id)

        # サイドイベントノード
        if node_id.endswith("_side"):
            return self._create_side_node(node_id)

        # 隠しルート続き（ep{N+1}_hidden）
        if node_id.endswith("_hidden") and node_id.startswith("ep"):
            return self._create_hidden_continuation_node(node_id)

        # フラッシュバック・アクション開始ノード
        if node_id in ["ep1_flashback", "ep1_action"]:
            return self._create_prologue_variant_node(node_id)

        return None

    # ===== ターゲットノード作成ヘルパー =====

    def _create_ending_node(self, node_id: str, series: SeriesResult) -> RouteNode:
        """エンディングノード作成"""
        ending_type = node_id.replace("ending_", "")

        endings = {
            "true": ("真のエンディング", "全ての因果が解決し、真の幸福を掴む"),
            "normal": ("ノーマルエンディング", "平穏な日常が戻り、新たな日々が始まる"),
            "main": ("メインエンディング", "物語の主軸は完結したが、余韻が残る"),
            "bad_1": ("バッドエンド1", "選択を誤り、取り返しのつかない結末を迎える"),
            "bad_2": ("バッドエンド2", "守るべきものを失い、絶望の中で終わる"),
            "bad_3": ("バッドエンド3", "全てを失い、虚無だけが残る"),
        }

        title, desc = endings.get(ending_type, (f"エンディング: {ending_type}", "物語の結末"))

        return RouteNode(
            id=node_id,
            episode_num=99,
            content=f"{title}\n\n{desc}\n\n――終わり――",
            branch_type=BranchType.MERGE,
            choices=[],
            metadata={"type": "ending", "ending_type": ending_type, "final": True}
        )

    def _create_catharsis_variant_node(self, node_id: str, series: SeriesResult) -> RouteNode:
        """カタルシスバリエーションノード"""
        variant = node_id.split("_catharsis_")[-1]

        variants = {
            "complete": ("完全カタルシス", "悪党は完全に制圧され、主人公の完全勝利"),
            "merciful": ("慈悲のカタルシス", "情けをかけたが、それもまた強さの証"),
            "twist": ("裏切りのカタルシス", "さらなる真実が暴かれ、更なるカタルシスへ"),
            "standard": ("標準カタルシス", "王道のざまぁ展開で完結"),
            "subverted": ("裏切られたカタルシス", "期待を裏切るダークな展開"),
        }

        title, desc = variants.get(variant, (f"カタルシス: {variant}", "カタルシスの変奏"))

        return RouteNode(
            id=node_id,
            episode_num=99,
            content=f"{title}\n\n{desc}\n\n物語は次の段階へ——",
            branch_type=BranchType.CHOICE,
            choices=[
                RouteChoice(
                    id=f"{node_id}_continue",
                    text="次へ進む",
                    target_node_id="ending_main",
                    priority=10
                )
            ],
            metadata={"type": "catharsis_variant", "variant": variant}
        )

    def _create_ending_variant_node(self, node_id: str, series: SeriesResult) -> RouteNode:
        """エンディングバリエーションノード"""
        if "happy_end" in node_id:
            return RouteNode(
                id=node_id,
                episode_num=99,
                content="ハッピーエンド\n\n全てが報われ、愛する者たちと永遠の幸せを掴む。\n\n――完――",
                branch_type=BranchType.MERGE,
                choices=[],
                metadata={"type": "ending", "variant": "happy", "final": True}
            )
        elif "bittersweet" in node_id:
            return RouteNode(
                id=node_id,
                episode_num=99,
                content="ビターエンド\n\n大切なものを守るため、自らを犠牲にする。\nその愛は永遠に語り継がれる。\n\n――完――",
                branch_type=BranchType.MERGE,
                choices=[],
                metadata={"type": "ending", "variant": "bittersweet", "final": True}
            )
        elif "open_end" in node_id:
            return RouteNode(
                id=node_id,
                episode_num=99,
                content="オープンエンド\n\n物語はここで一区切り。だが、彼らの冒険はまだ続く。\n\n――続く――",
                branch_type=BranchType.MERGE,
                choices=[],
                metadata={"type": "ending", "variant": "open", "final": True}
            )
        elif "true_route" in node_id:
            return RouteNode(
                id=node_id,
                episode_num=99,
                content="真ルート\n\n全てのフラグを回収し、真実のエンディングへ到達。\n全ての謎が解け、真の救済を得る。\n\n――真・完――",
                branch_type=BranchType.MERGE,
                choices=[],
                metadata={"type": "ending", "variant": "true", "final": True}
            )
        elif "flag_avoid" in node_id:
            return RouteNode(
                id=node_id,
                episode_num=99,
                content="フラグ回避ルート\n\n断罪フラグを完全回避し、隠しキャラとの溺愛ルートへ。\n\n――甘い完――",
                branch_type=BranchType.MERGE,
                choices=[],
                metadata={"type": "ending", "variant": "flag_avoid", "final": True}
            )

        return RouteNode(
            id=node_id,
            episode_num=99,
            content="特別なエンディング",
            branch_type=BranchType.MERGE,
            choices=[],
            metadata={"type": "ending", "variant": "special"}
        )

    def _create_side_event_node(self, node_id: str) -> RouteNode:
        """サイドイベントノード"""
        ep_num = node_id.split("_")[0].replace("ep", "")

        return RouteNode(
            id=node_id,
            episode_num=int(ep_num) if ep_num.isdigit() else 0,
            content="[サイドイベント] 本編とは別の視点で描かれるもう一つの物語。\nキャラクターの新たな一面が見える——",
            branch_type=BranchType.CHOICE,
            choices=[
                RouteChoice(
                    id=f"{node_id}_back",
                    text="メインに戻る",
                    target_node_id=f"ep{ep_num}_main" if ep_num.isdigit() else "ending_main",
                    priority=10
                )
            ],
            metadata={"type": "side_event"}
        )

    def _create_optimized_node(self, node_id: str) -> RouteNode:
        return RouteNode(
            id=node_id,
            episode_num=0,
            content="[最適化ルート] ループ知識を活用し、最短・最効率で目標を達成。\n無駄のない完璧な立ち回りで、敵を圧倒する——",
            branch_type=BranchType.CHOICE,
            choices=[
                RouteChoice(
                    id=f"{node_id}_continue",
                    text="次の最適化へ",
                    target_node_id=node_id.replace("_optimized", "_main"),
                    priority=10
                )
            ],
            metadata={"route": "optimized"}
        )

    def _create_skill_combo_node(self, node_id: str) -> RouteNode:
        return RouteNode(
            id=node_id,
            episode_num=0,
            content="[スキル実験] 新たなスキル組み合わせを発見。\n予想外の相乗効果で、未知の力を開花させる——",
            branch_type=BranchType.CHOICE,
            choices=[
                RouteChoice(
                    id=f"{node_id}_continue",
                    text="実戦投入",
                    target_node_id=node_id.replace("_skill_combo", "_main"),
                    priority=10
                )
            ],
            metadata={"route": "skill_experiment"}
        )

    def _create_yuri_scene_node(self, node_id: str) -> RouteNode:
        return RouteNode(
            id=node_id,
            episode_num=0,
            content="[百合シーン] 二人の距離が縮まる、尊く甘いひととき。\n指先が触れ合うだけで、世界が色づく——",
            branch_type=BranchType.CHOICE,
            choices=[
                RouteChoice(
                    id=f"{node_id}_continue",
                    text="余韻に浸る",
                    target_node_id=node_id.replace("_yuri_scene", "_main"),
                    priority=10
                )
            ],
            metadata={"route": "yuri", "mood": "sweet"}
        )

    def _create_prologue_variant_node(self, node_id: str) -> RouteNode:
        """プロローグバリエーションノード作成（フラッシュバック、アクション開始等）"""
        variant_map = {
            "ep1_flashback": ("回想から始める", "過去の記憶が蘇る——かつての平穏な日々が、今、甦る。", "flashback"),
            "ep1_action": ("アクションから始める", "剣閃、魔法炸裂——いきなり戦場の只中へ放り込まれる。", "action"),
            "ep1_true_route": ("真ルートから始める", "全てを知った状態で、最初の選択をやり直す。", "true_route"),
        }

        title, desc, variant = variant_map.get(node_id, ("特別な始まり", "特別な幕開け——", "special"))

        return RouteNode(
            id=node_id,
            episode_num=1,
            content=f"{title}\n\n{desc}\n\n物語は動き出す——",
            branch_type=BranchType.CHOICE,
            choices=[
                RouteChoice(
                    id=f"{node_id}_continue",
                    text="第1話へ進む",
                    target_node_id="ep1_main",
                    priority=10
                )
            ],
            metadata={"type": "prologue_variant", "variant": variant}
        )

    def _create_hidden_continuation_node(self, node_id: str) -> RouteNode:
        ep_part = node_id.split("_hidden")[0]

        return RouteNode(
            id=node_id,
            episode_num=0,
            content="[隠しルート継続] 秘められた真実の続き。\nメインルートでは見えなかった世界の裏側——",
            branch_type=BranchType.CONDITIONAL,
            choices=[
                RouteChoice(
                    id=f"{node_id}_continue",
                    text="隠しルートを進む",
                    target_node_id=f"{ep_part}_hidden",
                    conditions=[
                        BranchCondition("flags.hidden_unlocked", ConditionOperator.EQUALS, True)
                    ],
                    priority=1
                ),
                RouteChoice(
                    id=f"{node_id}_return",
                    text="メインに戻る",
                    target_node_id=f"{ep_part}_main",
                    priority=5
                )
            ],
            metadata={"route": "hidden_continuation"}
        )

    def _create_bad_ending_node(self, node_id: str) -> RouteNode:
        ep_num = node_id.replace("ending_bad_", "")

        return RouteNode(
            id=node_id,
            episode_num=int(ep_num) if ep_num.isdigit() else 99,
            content=f"バッドエンド（分岐点: 第{ep_num}話）\n\n選択を誤った代償はあまりに大きかった。\n守るべきものを失い、後悔だけが残る——\n\n――悪い終わり――",
            branch_type=BranchType.MERGE,
            choices=[
                RouteChoice(
                    id=f"{node_id}_retry",
                    text="やり直す（ロード/ループ）",
                    target_node_id=f"ep{ep_num}_main" if ep_num.isdigit() else "prologue",
                    effects={"retry": True},
                    priority=7
                ),
                RouteChoice(
                    id=f"{node_id}_accept",
                    text="この結末を受け入れる",
                    target_node_id="ending_bad_final",
                    priority=1
                )
            ],
            metadata={"type": "ending", "variant": "bad", "ep_num": ep_num}
        )

    def _create_final_ending_node(self, node_id: str, series: SeriesResult) -> RouteNode:
        if node_id == "ending_true":
            return RouteNode(
                id=node_id,
                episode_num=99,
                content="真のエンディング\n\n全ての因果が収束し、真の救済を得る。\n全フラグ回収、確率1の必然——\n\n――真・完――",
                branch_type=BranchType.MERGE,
                choices=[],
                metadata={"type": "ending", "variant": "true", "final": True}
            )
        elif node_id == "ending_normal":
            return RouteNode(
                id=node_id,
                episode_num=99,
                content="ノーマルエンディング\n\n物語はひとまずの決着を見る。\n日常が戻り、新たな朝が来る——\n\n――完――",
                branch_type=BranchType.MERGE,
                choices=[],
                metadata={"type": "ending", "variant": "normal", "final": True}
            )
        else:  # ending_main
            return RouteNode(
                id=node_id,
                episode_num=99,
                content="メインエンディング\n\n主要な因果は解決したが、余韻は残る。\n彼らの物語はまだ続いていく——\n\n――一区切り――",
                branch_type=BranchType.MERGE,
                choices=[],
                metadata={"type": "ending", "variant": "main", "final": True}
            )

    def _create_main_continuation_node(self, node_id: str) -> RouteNode:
        ep_part = node_id.replace("_main", "")
        ep_num = ep_part.replace("ep", "")
        next_ep = int(ep_num) + 1 if ep_num.isdigit() else 1

        return RouteNode(
            id=node_id,
            episode_num=next_ep,
            content=f"第{next_ep}話 メインルート継続\n\n物語は次の段階へと進む——",
            branch_type=BranchType.CHOICE,
            choices=[
                RouteChoice(
                    id=f"{node_id}_continue",
                    text="次へ",
                    target_node_id=f"ep{next_ep}_main" if next_ep <= 8 else "ending_main",
                    priority=10
                )
            ],
            metadata={"route": "main", "continuation": True}
        )

    def _create_side_node(self, node_id: str) -> RouteNode:
        return self._create_side_event_node(node_id)

    def _create_hidden_continuation_node(self, node_id: str) -> RouteNode:
        ep_part = node_id.replace("_hidden", "")
        ep_num = ep_part.replace("ep", "")
        next_ep = int(ep_num) + 1 if ep_num.isdigit() else 1

        if next_ep > 8:
            hidden_target = "ending_true"
            main_target = "ending_main"
        else:
            hidden_target = f"ep{next_ep}_hidden"
            main_target = f"ep{next_ep}_main"

        return RouteNode(
            id=node_id,
            episode_num=next_ep,
            content=f"第{next_ep}話 隠しルート継続\n\nメインでは見えなかった真実の続き——",
            branch_type=BranchType.CONDITIONAL,
            choices=[
                RouteChoice(
                    id=f"{node_id}_continue",
                    text="隠しルートを進む",
                    target_node_id=hidden_target,
                    conditions=[
                        BranchCondition("flags.hidden_unlocked", ConditionOperator.EQUALS, True)
                    ],
                    priority=1
                ),
                RouteChoice(
                    id=f"{node_id}_return",
                    text="メインに戻る",
                    target_node_id=main_target,
                    priority=5
                )
            ],
            metadata={"route": "hidden", "continuation": True}
        )

    def _create_merge_node(self, ep_num: int, nodes: List[RouteNode]) -> Optional[RouteNode]:
        """合流ノード作成"""
        # 全ルートを合流させるノード
        merge_node = RouteNode(
            id=f"ep{ep_num}_merge",
            episode_num=ep_num,
            content="様々な選択の果てに、物語は一つの地点へ収束する——",
            branch_type=BranchType.MERGE,
            parent_ids=[n.id for n in nodes if n.branch_type != BranchType.MERGE],
            metadata={"type": "merge", "convergence": True}
        )

        merge_node.choices = [
            RouteChoice(
                id=f"ep{ep_num}_merge_true",
                text="真のエンディングへ",
                target_node_id="ending_true",
                effects={"ending": "true", "all_flags_resolved": True},
                priority=10
            ),
            RouteChoice(
                id=f"ep{ep_num}_merge_normal",
                text="ノーマルエンディングへ",
                target_node_id="ending_normal",
                effects={"ending": "normal"},
                priority=5
            )
        ]

        return merge_node


class IFRoutePlayer:
    """IFルートプレイヤー（実行エンジン）"""

    def __init__(self, graph: IFRouteGraph):
        self.graph = graph
        self.current_node_id = graph.entry_node_id
        self.context: Dict[str, Any] = {
            "flags": {},
            "variables": {},
            "history": [],
            "stats": {}
        }
        self.save_points: List[Dict[str, Any]] = []

    def get_current_node(self) -> Optional[RouteNode]:
        return self.graph.get_node(self.current_node_id)

    def get_available_choices(self) -> List[RouteChoice]:
        node = self.get_current_node()
        if not node:
            return []
        return node.get_available_choices(self.context)

    def make_choice(self, choice_id: str) -> bool:
        """選択を実行"""
        node = self.get_current_node()
        if not node:
            return False

        choice = next((c for c in node.choices if c.id == choice_id), None)
        if not choice:
            return False

        if not choice.is_available(self.context):
            return False

        # セーブポイント作成
        self.save_points.append({
            "node_id": self.current_node_id,
            "context": self.context.copy(),
            "timestamp": datetime.now().isoformat()
        })

        # 副作用適用
        self.context = choice.apply_effects(self.context)

        # 履歴記録
        self.context["history"].append({
            "node_id": self.current_node_id,
            "choice_id": choice_id,
            "choice_text": choice.text,
            "timestamp": datetime.now().isoformat()
        })

        # 次のノードへ
        if choice.target_node_id:
            self.current_node_id = choice.target_node_id

            # 自動進行（選択肢がないノード）
            next_node = self.get_current_node()
            if next_node and next_node.branch_type == BranchType.MERGE and next_node.merge_target:
                self.current_node_id = next_node.merge_target

        return True

    def load_save(self, index: int) -> bool:
        """セーブロード"""
        if 0 <= index < len(self.save_points):
            save = self.save_points[index]
            self.current_node_id = save["node_id"]
            self.context = save["context"]
            return True
        return False

    def get_state(self) -> Dict[str, Any]:
        """現在状態取得"""
        node = self.get_current_node()
        return {
            "current_node": node.to_dict() if node else None,
            "available_choices": [
                {"id": c.id, "text": c.text, "available": c.is_available(self.context)}
                for c in self.get_available_choices()
            ],
            "context": self.context,
            "save_points_count": len(self.save_points)
        }

    def export_playthrough(self) -> Dict[str, Any]:
        """プレイスルー記録出力"""
        return {
            "genre": self.graph.metadata.get("genre", "unknown"),
            "path": self.context.get("history", []),
            "final_ending": self.context.get("ending", "unknown"),
            "flags": self.context.get("flags", {}),
            "variables": self.context.get("variables", {}),
            "stats": self.context.get("stats", {}),
            "timestamp": datetime.now().isoformat()
        }


def create_if_route_system(genre: str, series: SeriesResult, preset: Dict[str, Any]) -> IFRouteGraph:
    """IFルートシステム作成のエントリーポイント"""
    generator = IFRouteGenerator(genre, preset)

    # 初期コンテキスト設定
    initial_context = {
        "genre": genre,
        "title": series.title,
        "flags": {},
        "variables": {}
    }
    generator.set_initial_context(initial_context)

    return generator.generate_from_series(series)
