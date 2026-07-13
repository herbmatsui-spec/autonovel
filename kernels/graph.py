from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class NarrativeState(Enum):
    """
    物語の構造的な状態を定義する。
    """
    DAILY = auto()        # 日常 / 導入
    INCIDENT = auto()    # 事件発生 / 転機
    CONFLICT = auto()     # 葛藤 / 展開
    PRE_CLIMAX = auto()   # クライマックス前夜 / 準備
    CLIMAX = auto()       # クライマックス / 最大衝突
    RESOLUTION = auto()  # 解決 / 後日談
from dataclasses import dataclass, field

from kernels.connection import ConnectionState


@dataclass
class NarrativeStateNode:
    """
    物語状態の定義を保持するノード。
    """
    state: NarrativeState
    name: str
    description: str
    required_conditions: List[str] = field(default_factory=list) # 遷移に必要な条件
    recommended_tone: str = "Neutral"                             # 推奨される感情トーン
    forbidden_elements: List[str] = field(default_factory=list) # 禁止される展開要素

@dataclass
class RelationEdge:
    """
    キャラクター間の有向関係性を定義する。
    """
    source: str
    target: str
    state: ConnectionState
    weight: float = 1.0 # 関係の強度/重要度

class NarrativeStateGraph:
    """
    物語の状態遷移グラフを管理し、プロットの構造的制御を行う。
    """
    def __init__(self):
        # state -> NarrativeStateNode
        self.nodes: Dict[NarrativeState, NarrativeStateNode] = {}
        # (from_state, to_state) -> (weight, path)
        self.edges: Dict[Tuple[NarrativeState, NarrativeState], Tuple[float, str]] = {}

    def add_node(self, node: NarrativeStateNode):
        self.nodes[node.state] = node

    def add_transition(self, from_state: NarrativeState, to_state: NarrativeState, weight: float = 1.0, path: str = "standard"):
        self.edges[(from_state, to_state)] = (weight, path)

    def get_valid_transitions(self, current_state: NarrativeState, path: Optional[str] = None) -> List[NarrativeState]:
        if path:
            return [to_state for (from_state, to_state), (weight, p) in self.edges.items()
                    if from_state == current_state and p == path]
        return [to_state for (from_state, to_state) in self.edges.keys() if from_state == current_state]

    def get_node(self, state: NarrativeState) -> Optional[NarrativeStateNode]:
        return self.nodes.get(state)

    def check_forbidden_elements(self, state: NarrativeState, content: str) -> List[str]:
        """
        指定された状態における禁止要素がコンテンツに含まれているかを簡易的にチェックする。
        実際にはLLMによる監査（Phase 21）で詳細に判定するが、ここではキーワードベースの一次フィルタリングを行う。
        """
        node = self.get_node(state)
        if not node or not node.forbidden_elements:
            return []

        found_violations = []
        for element in node.forbidden_elements:
            if element in content:
                found_violations.append(element)
        return found_violations

    def load_from_config(self, config_path: str):
        """
        JSON設定ファイルから状態ノードと遷移ルールをロードする。
        """
        import json
        import os

        if not os.path.exists(config_path):
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # ノードのロード
        states_data = data.get("narrative_states", {})
        for state_key, info in states_data.items():
            try:
                state_enum = NarrativeState[state_key]
                node = NarrativeStateNode(
                    state=state_enum,
                    name=info.get("name", state_key),
                    description=info.get("description", ""),
                    required_conditions=info.get("required_conditions", []),
                    recommended_tone=info.get("recommended_tone", "Neutral"),
                    forbidden_elements=info.get("forbidden_elements", [])
                )
                self.add_node(node)
            except KeyError:
                continue # 定義されていないEnum値はスキップ

        # 遷移のロード
        transitions = data.get("transitions", [])
        for trans in transitions:
            try:
                from_state = NarrativeState[trans["from"]]
                to_state = NarrativeState[trans["to"]]
                weight = trans.get("weight", 1.0)
                path = trans.get("path", "standard")
                self.add_transition(from_state, to_state, weight, path)
            except KeyError:
                continue

class NarrativeStateManager:
    """
    物語の現在の状態を管理し、遷移を制御するマネージャー。
    """
    # 物語状態ごとのベースライン緊張度 (Tension) 定義
    TENSION_MAP = {
        NarrativeState.DAILY: 20,
        NarrativeState.INCIDENT: 50,
        NarrativeState.CONFLICT: 70,
        NarrativeState.PRE_CLIMAX: 80,
        NarrativeState.CLIMAX: 90,
        NarrativeState.RESOLUTION: 30,
    }

    # 物語状態ごとの描写密度 (Description Density) 定義
    DENSITY_MAP = {
        NarrativeState.DAILY: "High",
        NarrativeState.INCIDENT: "Medium",
        NarrativeState.CONFLICT: "Medium-High",
        NarrativeState.PRE_CLIMAX: "Medium-Low",
        NarrativeState.CLIMAX: "Low",
        NarrativeState.RESOLUTION: "High",
    }

    def __init__(self, graph: NarrativeStateGraph, initial_state: NarrativeState = NarrativeState.DAILY):
        self.graph = graph
        self.current_state = initial_state
        self.history: List[NarrativeState] = [initial_state]
        self.state_duration = 0  # 現在の状態に留まっているシーン数
        self.current_base_tension = self.TENSION_MAP.get(initial_state, 20)
        self.current_description_density = self.DENSITY_MAP.get(initial_state, "Medium")

    def get_history(self) -> List[NarrativeState]:
        """
        これまでの状態遷移履歴を返す。
        """
        return self.history

    def check_current_violations(self, content: str) -> List[str]:
        """
        現在の状態における禁止要素がコンテンツに含まれているかをチェックする。
        """
        return self.graph.check_forbidden_elements(self.current_state, content)

    def validate_transition(self, next_state: NarrativeState, path: Optional[str] = None) -> Tuple[bool, str]:
        """
        指定された状態への遷移がグラフ定義上有効かどうかを検証する。
        パスが指定されている場合は、そのパスでの有効性を検証する。
        """
        valid_transitions = self.graph.get_valid_transitions(self.current_state, path=path)
        if next_state in valid_transitions:
            return True, "Valid transition."

        # 状態が同じ場合は維持として有効とする
        if next_state == self.current_state:
            return True, "State maintained."

        return False, f"Invalid transition from {self.current_state.name} to {next_state.name} (path: {path}). Valid options: {[s.name for s in valid_transitions]}"

    def transition_to(self, next_state: NarrativeState):
        """
        状態を遷移させる。
        """
        # 状態が同じ場合は期間をカウントアップして終了
        if next_state == self.current_state:
            self.state_duration += 1
            return

        # 遷移パスの情報を取得（standard/twist）
        current_path = "standard"
        if (self.current_state, next_state) in self.graph.edges:
            current_path = self.graph.edges[(self.current_state, next_state)][1]

        is_valid, message = self.validate_transition(next_state, path=current_path)

        # 遷移ログの記録（トレーサー）
        path_info = f" [Path: {current_path}]" if 'current_path' in locals() else ""
        log_msg = f"[Narrative Transition] {self.current_state.name} -> {next_state.name} (duration: {self.state_duration}){path_info}"
        if not is_valid:
            log_msg += f" (INVALID TRANSITION - FORCED: {message})"
            print(f"Warning: {log_msg}")
        else:
            print(log_msg)

        self.current_state = next_state
        self.history.append(next_state)
        self.state_duration = 0  # 状態が変わったのでリセット
        # 状態遷移に伴いベースライン緊張度と描写密度を更新
        self.current_base_tension = self.TENSION_MAP.get(next_state, 20)
        self.current_description_density = self.DENSITY_MAP.get(next_state, "Medium")

    def force_state(self, state: NarrativeState):
        # 強制遷移時も緊張度と描写密度を更新
        self.current_base_tension = self.TENSION_MAP.get(state, 20)
        self.current_description_density = self.DENSITY_MAP.get(state, "Medium")
        """
        グラフの遷移ルールを無視して、強制的に指定した状態にジャンプさせる（デバッグ用）。
        """
        log_msg = f"[Narrative FORCED Jump] {self.current_state.name} -> {state.name}"
        print(f"DEBUG: {log_msg}")
        self.current_state = state
        self.history.append(state)

    def restore_history(self, history: List[NarrativeState]):
        """
        状態遷移履歴を復元し、現在の状態を履歴の最後に設定する。
        """
        if not history:
            return
        self.history = list(history)
        self.current_state = self.history[-1]

    def suggest_next_state(self, current_progress: float, forced_state: Optional[NarrativeState] = None, preferred_path: Optional[str] = None) -> NarrativeState:
        """
        現在の進行度とグラフに基づき、次にとるべき状態を提案する。
        慣性（state_duration）を考慮し、短期間での遷移を抑制する。
        
        Args:
            current_progress: 物語の全体進行度 (0.0 ~ 1.0)
            forced_state: ユーザーや外部ロジックによる強制状態
            preferred_path: 優先したい遷移パス ("standard" or "twist")
        """
        if forced_state:
            return forced_state

        # 慣性の導入: 最低でも2シーンは同じ状態を維持することを推奨（CLIMAXなど重要局面ではより長く）
        min_duration = 2
        if self.current_state == NarrativeState.CLIMAX:
            min_duration = 3

        if self.state_duration < min_duration:
            # まだ十分な描写時間が経過していない場合は、現在の状態を維持することを優先
            return self.current_state

        # パス指定がある場合は、そのパスに沿った遷移を優先的に取得
        valid_transitions = self.graph.get_valid_transitions(self.current_state, path=preferred_path)

        # 指定パスで遷移先がない場合は、全有効遷移から取得
        if not valid_transitions:
            valid_transitions = self.graph.get_valid_transitions(self.current_state)

        if not valid_transitions:
            return self.current_state

        # 進行度に基づく簡易的な状態決定ロジック
        if current_progress < 0.2 and NarrativeState.INCIDENT in valid_transitions:
            return NarrativeState.INCIDENT
        elif current_progress < 0.5 and NarrativeState.CONFLICT in valid_transitions:
            return NarrativeState.CONFLICT
        elif current_progress < 0.8 and NarrativeState.PRE_CLIMAX in valid_transitions:
            return NarrativeState.PRE_CLIMAX
        elif current_progress < 0.9 and NarrativeState.CLIMAX in valid_transitions:
            return NarrativeState.CLIMAX
        elif NarrativeState.RESOLUTION in valid_transitions:
            return NarrativeState.RESOLUTION

        return valid_transitions[0] if valid_transitions else self.current_state

    def get_current_node(self) -> Optional[NarrativeStateNode]:
        return self.graph.get_node(self.current_state)

class GlobalStoryGraph:
    """
    物語の構造的状態（NarrativeStateGraph）と、キャラクター間の動的関係（RelationGraph）を統合管理する。
    """
    def __init__(self, narrative_graph: NarrativeStateGraph):
        self.narrative_graph = narrative_graph
        self.relation_graph = RelationGraph()
        self.global_history: List[Tuple[NarrativeState, float]] = [] # (state, progress)

    def update_relation(self, char_a: str, char_b: str, state: ConnectionState):
        self.relation_graph.add_relation(char_a, char_b, state)

    def get_global_tension(self) -> float:
        return self.relation_graph.get_global_tension()

    def sync_narrative_state(self, state: NarrativeState, progress: float):
        self.global_history.append((state, progress))

    def get_tension_analysis(self) -> str:
        tension = self.get_global_tension()
        state = self.relation_graph.get_correlation_map()
        return f"Global Tension: {tension:.2f}. Relations: {state}"

class RelationGraph:
    """
    物語全体のキャラクター相関図を管理し、構造的な制御を行う。
    """

    def __init__(self):
        # (source, target) -> RelationEdge
        self.edges: Dict[Tuple[str, str], RelationEdge] = {}
        self.characters: List[str] = []

    def add_relation(self, char_a: str, char_b: str, state: ConnectionState):
        """
        関係性を追加または更新する。
        """
        for c in [char_a, char_b]:
            if c not in self.characters:
                self.characters.append(c)

        self.edges[(char_a, char_b)] = RelationEdge(char_a, char_b, state)

    def get_relation(self, char_a: str, char_b: str) -> Optional[ConnectionState]:
        edge = self.edges.get((char_a, char_b))
        return edge.state if edge else None

    def get_global_tension(self) -> float:
        """
        物語全体の平均緊張度を算出する（物語のフェーズ判定に利用）。
        """
        if not self.edges:
            return 50.0
        total_tension = sum(edge.state.tension for edge in self.edges.values())
        return total_tension / len(self.edges)

    def suggest_dynamic_shift(self, target_phase: str) -> List[str]:
        """
        物語のフェーズ（例: "climax"）に合わせて、調整すべき関係性を提案する。
        """
        suggestions = []
        if target_phase == "climax":
            for (src, tgt), edge in self.edges.items():
                if edge.state.tension < 70:
                    suggestions.append(f"{src}と{tgt}の間の緊張を高め、衝突させるべきです。")
                if edge.state.affection > 80 and edge.state.trust < 50:
                    suggestions.append(f"{src}と{tgt}の間の不信感を爆発させ、共鳴イベントを誘発させてください。")

        return suggestions

    def get_correlation_map(self) -> Dict[str, Dict[str, str]]:
        """
        人間関係の簡易マップを生成する。
        """
        map_data = {}
        for (src, tgt), edge in self.edges.items():
            if src not in map_data: map_data[src] = {}

            # ステータスを文字列に要約
            summary = f"Aff:{int(edge.state.affection)} Tru:{int(edge.state.trust)}"
            map_data[src][tgt] = summary

        return map_data


# ==========================================
# 商用快感情管理：カタルシス・グラフ（ステップ16）
# ==========================================
from dataclasses import dataclass, field
from typing import Optional


class PleasureType(Enum):
    """快感情の種類"""
    CATHARSIS = "catharsis"           # カタルシス（浄化）
    TENSION_RELEASE = "tension_release"  # 緊張解放
    SCHADENFREUDE = "schadenfreude"   # 傍観者的快楽（ざまぁ）
    SUPERIORITY = "superiority"       # 優越感
    NOSTALGIA = "nostalgia"           # 懐かしさ・郷愁
    AWE = "awe"                       # 畏怖・感動
    COMFORT = "comfort"               # 安心感・温かさ
    TENSION = "tension"               # 緊張・期待
    SADNESS = "sadness"               # 悲しみ（共感的）
    EXCITEMENT = "excitement"         # 興奮


@dataclass
class PleasureNode:
    """快不快イベントを表現するノード"""
    node_id: str
    pleasure_type: PleasureType
    intensity: float  # 0.0 - 100.0
    description: str
    trigger_keywords: List[str] = field(default_factory=list)
    story_position: float = 0.0  # 物語全体における位置（0.0-1.0）
    characters_involved: List[str] = field(default_factory=list)
    commercial_role_source: Optional[str] = None  # この快感を発生させた商用役割


@dataclass
class PleasureEdge:
    """快感情イベント間の因果関係を定義"""
    source_node: str
    target_node: str
    causality_strength: float  # 因果の強さ 0.0-1.0
    delay_ticks: int = 0  # 効果発生までの遅延tick数
    amplification_factor: float = 1.0  # 快感増幅係数


class PleasureGraph:
    """
    カタルシス（快感情）のグラフを管理する。
    ノード: 快不快イベント
    エッジ: 因果関係（ある快感情が別の快感情を促進/抑制する）
    """

    def __init__(self):
        self.nodes: Dict[str, PleasureNode] = {}
        self.edges: List[PleasureEdge] = []
        self.neg_edges: List[PleasureEdge] = []  # 抑制関係
        self._node_counter = 0

    def add_pleasure_node(
        self,
        pleasure_type: PleasureType,
        intensity: float,
        description: str,
        trigger_keywords: Optional[List[str]] = None,
        story_position: float = 0.0,
        characters: Optional[List[str]] = None,
        commercial_role: Optional[str] = None
    ) -> str:
        """快感情ノードを追加"""
        node_id = f"pleasure_{self._node_counter}"
        self._node_counter += 1

        node = PleasureNode(
            node_id=node_id,
            pleasure_type=pleasure_type,
            intensity=min(100.0, max(0.0, intensity)),
            description=description,
            trigger_keywords=trigger_keywords or [],
            story_position=story_position,
            characters_involved=characters or [],
            commercial_role_source=commercial_role
        )
        self.nodes[node_id] = node
        return node_id

    def add_causal_link(
        self,
        source_id: str,
        target_id: str,
        strength: float = 0.5,
        delay: int = 0,
        amplification: float = 1.0
    ) -> bool:
        """因果リンクを追加（sourceが発生するとtargetが引起る）"""
        if source_id not in self.nodes or target_id not in self.nodes:
            return False

        edge = PleasureEdge(source_id, target_id, strength, delay, amplification)
        self.edges.append(edge)
        return True

    def add_inhibition_link(
        self,
        source_id: str,
        target_id: str,
        strength: float = 0.5
    ) -> bool:
        """抑制リンクを追加（sourceが発生するとtargetが抑制される）"""
        if source_id not in self.nodes or target_id not in self.nodes:
            return False

        edge = PleasureEdge(source_id, target_id, strength, 0, 1.0)
        self.neg_edges.append(edge)
        return True

    def calculate_pleasure_at_position(self, story_position: float) -> float:
        """特定位置での総快感情強度を計算"""
        total_pleasure = 0.0

        for node_id, node in self.nodes.items():
            # 位置に基づく減衰（中心から離れるほど減少）
            distance = abs(node.story_position - story_position)
            position_factor = max(0.0, 1.0 - (distance * 2))

            # 因果関係の伝播を計算
            causal_boost = self._calculate_causal_boost(node_id, story_position)

            node_pleasure = node.intensity * position_factor * causal_boost
            total_pleasure += node_pleasure

        return min(100.0, total_pleasure)

    def _calculate_causal_boost(self, node_id: str, current_position: float) -> float:
        """ノードの因果的強化を計算"""
        boost = 1.0

        # このノードを引き起こす上位ノードをチェック
        for edge in self.edges:
            if edge.target_node == node_id:
                source_node = self.nodes.get(edge.source_node)
                if source_node and source_node.story_position <= current_position:
                    # 因果元のノードが既に発生している場合
                    time_factor = 1.0 if edge.delay_ticks == 0 else 0.8
                    boost += (source_node.intensity / 100.0) * edge.causality_strength * edge.amplification_factor * time_factor

        return boost

    def get_pleasure_graph_summary(self) -> Dict[str, Any]:
        """快感情グラフの概要を返す"""
        if not self.nodes:
            return {"node_count": 0, "total_intensity": 0.0, "peak_position": 0.0, "pleasure_types": {}}

        pleasure_by_type = {}
        for node in self.nodes.values():
            ptype = node.pleasure_type.value
            pleasure_by_type[ptype] = pleasure_by_type.get(ptype, 0.0) + node.intensity

        total_intensity = sum(node.intensity for node in self.nodes.values())
        max_node = max(self.nodes.values(), key=lambda n: n.intensity)

        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "total_intensity": total_intensity,
            "peak_node_id": max_node.node_id,
            "peak_position": max_node.story_position,
            "peak_intensity": max_node.intensity,
            "pleasure_types": pleasure_by_type,
            "commercially_generated_nodes": sum(1 for n in self.nodes.values() if n.commercial_role_source),
        }

    def validate_graph_balance(self) -> Dict[str, Any]:
        """快感情グラフのバランスを検証
        
        問題点：
        - 緊張（Tension）が溜まりっぱなしで解放されない
        - 快感情が偏りすぎる
        - クライマックス附近的快感不足
        """
        issues = []
        suggestions = []

        tension_nodes = [n for n in self.nodes.values() if n.pleasure_type == PleasureType.TENSION]
        catharsis_nodes = [n for n in self.nodes.values() if n.pleasure_type == PleasureType.CATHARSIS]

        # 緊張に対してカタルシス不足
        if len(tension_nodes) > 3 and len(catharsis_nodes) < 1:
            issues.append("緊張ノードが多いがカタルシスノードが不足")
            suggestions.append("クライマックス前にカタルシス解放を追加することを推奨")

        # 後半の快感密度が低い
        late_pleasure = sum(
            n.intensity for n in self.nodes.values()
            if n.story_position > 0.7
        )
        early_pleasure = sum(
            n.intensity for n in self.nodes.values()
            if n.story_position < 0.3
        )

        if late_pleasure < early_pleasure * 0.5:
            issues.append("物語終盤の快感情が前半の50%未満")
            suggestions.append("終盤に更强的カタルシスまたは満足感の提供を追加することを推奨")

        # 快感種類の偏り
        type_counts = {}
        for node in self.nodes.values():
            ptype = node.pleasure_type.value
            type_counts[ptype] = type_counts.get(ptype, 0) + 1

        if max(type_counts.values()) > len(self.nodes) * 0.6:
            dominant_type = max(type_counts, key=type_counts.get)
            issues.append(f"{dominant_type}系の快感が60%を超えている")
            suggestions.append("快感情種類の多様性を增加（例如：comfort、nostalgiaを追加）")

        return {
            "is_balanced": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "graph_stats": self.get_pleasure_graph_summary()
        }


def build_default_pleasure_graph(
    story_arc_type: str = "exile_rise",
    target_length_ticks: int = 100
) -> PleasureGraph:
    """stories arc タイプに応じたデフォルトのカタルシスグラフを構築"""
    graph = PleasureGraph()

    if story_arc_type == "exile_rise":
        # 追放→成り上がりパターンの快感情グラフ
        # 序盤：屈辱・共感（軽い）
        graph.add_pleasure_node(
            PleasureType.TENSION, 60, "不当な追放と屈辱",
            trigger_keywords=["追放", "屈辱", "無理解"],
            story_position=0.1,
            characters=["protagonist"],
            commercial_role="HATE_MAGNET"
        )

        # 中盤：緊張の蓄積と微かな希望
        graph.add_pleasure_node(
            PleasureType.TENSION, 50, "旧勢力からの妨害",
            trigger_keywords=["妨害", "陰謀", "試練"],
            story_position=0.35
        )
        graph.add_pleasure_node(
            PleasureType.COMFORT, 40, "支援者との出会い",
            trigger_keywords=["支援", "仲間", "信頼"],
            story_position=0.45,
            commercial_role="UNCONDITIONAL_SUPPORTER"
        )

        # 中盤後半：微かな勝利
        graph.add_pleasure_node(
            PleasureType.SUPERIORITY, 55, "初勝利と能力の覚醒",
            trigger_keywords=["覚醒", "勝利", "成長"],
            story_position=0.55,
            commercial_role="AVATAR_OF_DESIRE"
        )

        # 終盤：緊張の爆発的大释放
        graph.add_pleasure_node(
            PleasureType.TENSION, 80, "最終決戦前の絶望的状況",
            trigger_keywords=["絶望", "限界", "最終テスト"],
            story_position=0.75
        )

        # クライマックス：最大カタルシス
        graph.add_pleasure_node(
            PleasureType.SCHADENFREUDE, 95, "敵の完全な崩壊と断罪",
            trigger_keywords=["ざまぁ", "断罪", "報復"],
            story_position=0.85,
            commercial_role="HATE_MAGNET"
        )
        graph.add_pleasure_node(
            PleasureType.CATHARSIS, 90, "完全なる立场逆転と称賛",
            trigger_keywords=["逆転", "成功", "歴史に残る"],
            story_position=0.9,
            commercial_role="STATUS_FLIP_TRIGGER"
        )

        # 結末：温かい凪
        graph.add_pleasure_node(
            PleasureType.COMFORT, 70, "穏やかな結末と称賛",
            trigger_keywords=["完了", "称賛", "平和"],
            story_position=1.0
        )

        # 因果リンク
        graph.add_causal_link("pleasure_0", "pleasure_3", strength=0.3, delay=5)  # 屈辱→微かな勝利
        graph.add_causal_link("pleasure_3", "pleasure_5", strength=0.5)  # 初勝利→最終決戦
        graph.add_causal_link("pleasure_4", "pleasure_5", strength=0.6)  # 絶望的状況→最終決戦

        # 快感連鎖：終盤の快感が増幅される
        graph.add_causal_link("pleasure_5", "pleasure_6", strength=0.8, amplification=1.5)  # 最終決戦→敵崩壊

    return graph

