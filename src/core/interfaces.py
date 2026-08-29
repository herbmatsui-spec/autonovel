"""
core/interfaces.py - 依存性注入のためのインターフェース（Protocol）定義
"""

from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

from src.models.base import GenerateResult
from src.models.db import BibleDbModel, BookDbModel, ChapterDbModel, CharacterDbModel, PlotDbModel
from src.models.plot import ArcList, PlotDetail


class ILLMClient(Protocol):
    """LLM呼び出しのインターフェース (LLMClientProtocol からのリネームと型厳格化)"""

    async def generate_json(
        self,
        purpose: str,
        prompt: str,
        response_schema: Optional[Any] = None,
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        expected_ep_num: Optional[int] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]: ...

    async def generate_text(
        self,
        purpose: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        stream_callback: Optional[Callable[[str], None]] = None,
        **kwargs: Any,
    ) -> str: ...


class IPromptManager(Protocol):
    """プロンプト管理のインターフェース"""

    def get_style_instruction(self, style_key: str) -> str: ...
    def get_villain_instruction(self, genre: str) -> str: ...
    def build_refinement_prompt(
        self, content: str, style_key: str, is_light: bool, target_word_count: int
    ) -> str: ...
    def get_plot_common_rules(self) -> str: ...
    def build_final_writing_prompt(
        self,
        ep_num: int,
        plot_data: Dict[str, Any],
        script_text: str,
        target_word_count: int,
        **kwargs: Any,
    ) -> Tuple[str, str]: ...
    def build_bible_extraction_prompt(self, content: str) -> str: ...
    def build_producer_audit_prompt(
        self, genre: str, keywords: str, trend_memo: str, archetype: str = "", **kwargs: Any
    ) -> str: ...
    def build_plot_integrity_audit_prompt(
        self, synopsis: str, world_settings_json: str, schema_json: Any, **kwargs: Any
    ) -> str: ...
    def build_global_repair_prompt(
        self, conflict_report: str, synopsis: str, world_rules: str, mc_profile: str, **kwargs: Any
    ) -> str: ...
    def build_logical_audit_prompt(self, past_facts: str, plot_bp: str, script: str) -> str: ...
    def build_critic_feedback_prompt(
        self, issue_list: Any, draft_content: str, blueprint: str
    ) -> str: ...
    def build_foreshadowing_audit_prompt(
        self, f_map: List[Dict[str, Any]], content: str
    ) -> str: ...
    def build_misunderstanding_validation_prompt(self, content: str, gap_desc: str) -> str: ...
    def build_marketing_pack_prompt(
        self, book_title: str, synopsis: str, latest_ep: int
    ) -> str: ...
    def build_title_generation_prompt(self, genre: str, keywords: str) -> str: ...
    def build_style_dna_analysis_prompt(self, sample_text: str) -> str: ...
    def build_world_creation_prompt(
        self, genre: str, keywords: str, response_schema: Any, **kwargs: Any
    ) -> str: ...
    def build_mc_creation_prompt(
        self, world_rules_json: str, genre: str, keywords: str, concept: str = "", **kwargs: Any
    ) -> str: ...
    def build_sub_char_creation_prompt(
        self,
        world_rules_json: str,
        mc_data_json: str,
        causality_map: List[str],
        mc_name: str,
        **kwargs: Any,
    ) -> str: ...
    def build_bible_creation_prompt(
        self,
        bible_core_schema: Any,
        world_rules_json: str,
        concept: str,
        target_eps: int,
        **kwargs: Any,
    ) -> str: ...
    def build_marketing_ab_test_prompt(self, bible_core_concept: str, **kwargs: Any) -> str: ...
    def build_roadmap_prompt(
        self,
        bible_core_title: str,
        bible_core_synopsis: str,
        target_eps: int,
        roadmap_list_schema: Any,
        **kwargs: Any,
    ) -> str: ...
    def build_plot_expansion_prompt(
        self,
        book_title: str,
        ep_num: int,
        ep_info: Dict[str, Any],
        past_plots: List[Any],
        arcs: List[Any],
        book_genre: str,
        **kwargs: Any,
    ) -> str: ...
    def build_arc_generation_prompt(
        self, title: str, synopsis: str, target_eps: int, **kwargs: Any
    ) -> str: ...
    def build_rebuild_plot_outline_prompt(
        self,
        book_title: str,
        start_ep: int,
        new_total_eps: int,
        book_synopsis: str,
        keywords: str,
        trend_memo: str,
        pending_foreshadowing: List[str],
    ) -> str: ...
    def build_amplify_prompt(
        self, final_content: str, current_target_word_count: int, fix_inst: str = ""
    ) -> str: ...
    def build_analyze_import_chapter_prompt(
        self, cleaned_content: str, episode_draft_schema: Any
    ) -> str: ...
    def build_critique_quality_prompt(self, book_title: str, summary_data_json: str) -> str: ...
    def build_iterative_gap_analysis_prompt(
        self, book_genre: str, book_title: str, batch_data: str
    ) -> str: ...
    def build_dry_run_prompt(
        self,
        ep_num: int,
        improved_prompt: str,
        plot_detailed_blueprint: str,
        plot_script_content: str,
    ) -> str: ...
    def build_easy_mode_inference_prompt(
        self, user_prompt: str, schema_json: Optional[Any] = None
    ) -> str: ...


class DatabaseManagerProtocol(Protocol):
    """データベース接続管理のインターフェース"""

    async def fetch_one(self, query: str, params: Tuple[Any, ...] = ()) -> Optional[Any]: ...
    async def fetch_all(self, query: str, params: Tuple[Any, ...] = ()) -> List[Any]: ...
    async def execute(self, query: str, params: Tuple[Any, ...] = ()) -> Any: ...


class IRepository(Protocol):
    """データアクセスのインターフェース (DataRepositoryProtocol からのリネームと型厳格化)"""

    @property
    def db(self) -> DatabaseManagerProtocol: ...
    async def get_book(self, book_id: int) -> Optional[BookDbModel]: ...
    async def get_chapter(self, branch_id: int, ep_num: int) -> Optional[ChapterDbModel]: ...
    async def get_latest_bible(self, book_id: int) -> Optional[BibleDbModel]: ...
    async def get_all_characters(self, book_id: int) -> List[CharacterDbModel]: ...
    async def get_plots_between(
        self, book_id: int, start_ep: int, end_ep: int
    ) -> List[PlotDbModel]: ...
    async def get_all_non_anchor_chapters(
        self, book_id: int, order_by: str = "ep_num"
    ) -> List[ChapterDbModel]: ...
    async def get_all_plots(self, book_id: int) -> List[PlotDbModel]: ...
    async def get_plot(self, branch_id: int, ep_num: int) -> Optional[PlotDbModel]: ...
    async def create_chapter(self, *args: Any, **kwargs: Any) -> Any: ...
    async def create_or_replace_plot(self, *args: Any, **kwargs: Any) -> Any: ...


class UnitOfWorkProtocol(Protocol):
    """トランザクション管理のインターフェース"""

    async def __aenter__(self) -> Any: ...
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Optional[bool]: ...


class IReporter(Protocol):
    """進捗報告用インターフェース"""

    def report(self, msg: str, level: str = "info") -> None: ...
    def update_progress(self, current: int, total: int, status: str = "") -> None: ...


class IWorldBibleGenerator(Protocol):
    """世界観・企画書生成のインターフェース"""

    async def create_hegemony_plan(
        self, config: Any, uow: Any, reporter: Optional[IReporter] = None
    ) -> Tuple[int, Any]: ...


class IPlotExpander(Protocol):
    """プロット展開のインターフェース"""

    async def expand_plots(
        self,
        book_id: int,
        target_ep_list: List[int],
        arcs: List[Any],
        reporter: Optional[IReporter] = None,
        force: bool = False,
        branch_id: Optional[int] = None,
    ) -> List[Any]: ...


class IPlanAuditor(Protocol):
    """企画監査のインターフェース"""

    async def run_audit(
        self,
        genre: str,
        keywords: str,
        trend_memo: str,
        sanctuary: str = "",
        originality_score: int = 50,
        platform: str = "カクヨむ/なろう",
    ) -> Optional[Any]: ...


# --- Agent Protocols ---

class IPlanningAgent(Protocol):
    """企画・アーク生成エージェントのインターフェース"""

    async def generate_arcs(
        self,
        title: str,
        synopsis: str,
        target_eps: int,
        start_ep: int = 1,
        **kwargs: Any,
    ) -> ArcList: ...

    async def run(self, *args: Any, **kwargs: Any) -> Any: ...  # delegate to generate_arcs


class IWritingAgent(Protocol):
    """執筆エージェントのインターフェース"""

    async def generate_episodes(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float,
        target_word_count: int,
        is_easy_mode: bool,
        reporter: Optional[IReporter] = None,
        branch_id: int = 1,
        style_tag: Optional[str] = None,
    ) -> int: ...

    async def generate_episodes_pipeline(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float,
        target_word_count: int,
        is_easy_mode: bool,
        reporter: Optional[IReporter] = None,
        branch_id: int = 1,
        style_tag: Optional[str] = None,
    ) -> Tuple[int, List[int]]: ...

    async def trigger_bible_extraction(
        self, book_id: int, content: str, reporter: Optional[IReporter] = None
    ) -> Any: ...

    async def run(self, *args: Any, **kwargs: Any) -> Any: ...


class IPlotAgent(Protocol):
    """プロット展開エージェントのインターフェース"""

    async def expand_plots(
        self,
        book_id: int,
        ep_nums: List[int],
        arcs: List[Any],
        reporter: Optional[IReporter] = None,
        force: bool = False,
        branch_id: Optional[int] = None,
    ) -> List[PlotDetail]: ...

    async def run(self, *args: Any, **kwargs: Any) -> Any: ...


class ICritiqueAgent(Protocol):
    """批評・改善提案エージェントのインターフェース"""

    async def analyze_work_quality(self, book_id: int) -> str: ...
    async def run_iterative_gap_analysis(
        self, book_id: int, max_iterations: int = 10
    ) -> GenerateResult: ...
    async def run_dry_run(self, book_id: int, ep_num: int, improved_prompt: str) -> str: ...
    async def run_dogfeeding_approval_loop(
        self, content: str, ep_num: int, passion: float, temp: float
    ) -> Dict[str, Any]: ...


class IMarketingAgent(Protocol):
    """マーケティングエージェントのインターフェース"""

    async def generate_pack(
        self, book_title: str, synopsis: str, latest_ep: int, **kwargs: Any
    ) -> Dict[str, Any]: ...

    async def run(self, *args: Any, **kwargs: Any) -> Any: ...

    async def create_export_package(self, book_id: int) -> Tuple[bytes, str]: ...


class ILogicalAuditor(Protocol):
    """論理監査エージェントのインターフェース"""

    async def audit_logical_consistency(
        self, book_id: int, ep_num: int, blueprint: str
    ) -> Tuple[bool, str]: ...

    async def check_integrity(
        self, keywords: List[str], blueprint: str, content: str, threshold: float
    ) -> Tuple[bool, float, List[str]]: ...


class INarrativeController(Protocol):
    """ナラティブコントローラーのインターフェース"""

    async def run(self, *args: Any, **kwargs: Any) -> Any: ...


class IStyleRagManager(Protocol):
    """スタイルRAGマネージャーのインターフェース"""

    # Methods used by WritingAgent etc.
    pass  # Placeholder; actual methods to be defined as needed


class IContextManager(Protocol):
    """コンテキストマネージャーのインターフェース"""

    pass  # Placeholder


class ITextFormatter(Protocol):
    """テキストフォーマッターのインターフェース"""

    def format(self, text: str) -> str: ...


# end of file
