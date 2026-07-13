import logging
from typing import Any, Dict, Generic, List, Optional, TypeVar

from src.core.container import AppContainer
from streamlit_app import api_client
from streamlit_app.progress import ProgressStateProxy, run_in_background
from streamlit_app.workflow_types import WorkflowType

logger = logging.getLogger(__name__)

# コンテナのキャッシュを管理する内部辞書
_container_cache: dict[str, AppContainer] = {}

def get_di_container(api_key: str = "DUMMY") -> AppContainer:
    """
    DIコンテナをLazyに取得する。
    @st.cache_resource の代わりに明示的なキャッシュ管理を行うことで、
    APIキー変更時の切り替えや初期化タイミングを制御しやすくする。
    """
    global _container_cache

    if api_key not in _container_cache:
        # ここで初めてインスタンス化とワイヤリングを行う (Lazy Loading)
        logger.debug(f"Initializing new AppContainer for api_key: {api_key[:4]}***")
        container = AppContainer(api_key=api_key)
        container.wire(modules=[__name__])
        _container_cache[api_key] = container

    return _container_cache[api_key]

from src.models.api_schemas import (
    BibleSchema,
    BookSchema,
    ChapterSchema,
    OptimizationReportSchema,
    PlotSchema,
)

T = TypeVar('T')

class SchemaProxy(Generic[T]):
    """Pydanticスキーマを軽量にラップし、型安全なアクセスを提供する汎用プロキシ"""
    _schema_cls: type[T]

    def __init__(self, d: dict | T):
        self._data = d if isinstance(d, self._schema_cls) else self._schema_cls(**d)

    def __getattr__(self, name):
        return getattr(self._data, name)

    def model_dump(self) -> dict:
        return self._data.model_dump()

class BookProxy(SchemaProxy[BookSchema]):
    _schema_cls = BookSchema

class PlotProxy(SchemaProxy[PlotSchema]):
    _schema_cls = PlotSchema

class ChapterProxy(SchemaProxy[ChapterSchema]):
    _schema_cls = ChapterSchema

class BibleProxy(SchemaProxy[BibleSchema]):
    _schema_cls = BibleSchema

class OptimizationHistoryProxy(SchemaProxy[OptimizationReportSchema]):
    _schema_cls = OptimizationReportSchema

class DataRepositoryProxy:
    def get_all_books(self) -> List[BookProxy]:
        books = api_client.list_books()
        return [BookProxy(b) for b in books]

    def get_book(self, book_id: int) -> Optional[BookProxy]:
        b = api_client.get_book(book_id)
        return BookProxy(b) if b else None

    def delete_book(self, book_id: int) -> None:
        api_client.delete_book(book_id)

    def get_all_plots(self, book_id: int) -> List[PlotProxy]:
        plots = api_client.get_plots(book_id)
        return [PlotProxy(p) for p in plots]

    def get_all_non_anchor_chapters(self, book_id: int, order_by: str = None) -> List[ChapterProxy]:
        chapters = api_client.get_chapters(book_id)
        return [ChapterProxy(c) for c in chapters]

    def get_latest_bible(self, book_id: int) -> Optional[BibleProxy]:
        b = api_client.get_bible(book_id)
        return BibleProxy(b) if b else None

    def get_optimization_history(self, book_id: int) -> List[OptimizationHistoryProxy]:
        history = api_client.get_opt_history(book_id)
        return [OptimizationHistoryProxy(h) for h in history]

    def create_chapter(self, book_id: int, ep_num: int, title: str, content: str, summary: str, killer_phrase: str = "", ai_insight: str = "", world_state: dict = None, trinity_review_log: dict = None, created_at: str = None) -> None:
        api_client.create_chapter(book_id, ep_num, title, content, summary, killer_phrase, ai_insight, world_state, trinity_review_log, created_at)

    def delete_chapter(self, book_id: int, ep_num: int) -> None:
        api_client.delete_chapter(book_id, ep_num)

class CritiqueProxy:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def run_dry_run(self, book_id: int, test_ep: int, prompt_patch: str) -> Dict[str, Any]:
        return {"success": True, "log": "Proxy run_dry_run"}

class MarketingProxy:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def analyze_style_dna(self, sample: str) -> Dict[str, Any]:
        return api_client.analyze_style_dna(self.api_key, sample)

    def create_export_package(self, book_id: int) -> tuple:
        try:
            r = api_client.export_package(self.api_key, book_id)
            if not r:
                return b"", "export.zip"
            cd = r.headers.get("Content-Disposition", "")
            filename = "export.zip"
            if "filename=" in cd:
                filename = cd.split("filename=")[1].strip('"')
            return r.content, filename
        except Exception as e:
            print(f"Error fetching export package: {e}")
            return b"", "export.zip"

class PlannerProxy:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def create_hegemony_plan(self, **kwargs) -> tuple:
        pass

class NarrativeProxy:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_stress_history_data(self, chapters: List[ChapterProxy], plots: List[PlotProxy]) -> List[Dict[str, Any]]:
        res = []
        cumulative = 0
        for p in plots:
            ep_num = p.ep_num
            if getattr(p, 'is_catharsis', False):
                cumulative = 0  # カタルシス発動でストレス値をリセット
            else:
                stress_val = getattr(p, 'stress', 0) or 0
                if not stress_val:
                    stress_val = (p.tension - 50) if (getattr(p, 'tension', 50) or 50) > 50 else 0
                cumulative += max(0, stress_val)
            res.append({
                "話数": ep_num,
                "ストレス蓄積値": cumulative
            })
        return res

class CandidateProxy:
    """プロデューサー企画監査における候補プランのプロキシ"""
    def __init__(self, c: dict):
        self.plan_name = c.get("plan_name", "")
        self.plan_type = c.get("plan_type", "")
        self.refined_keywords = c.get("refined_keywords", "")
        self.refined_concept = c.get("refined_concept", "")
        self.refined_mc_suggestion = c.get("refined_mc_suggestion", "")
        self.refined_villain_suggestion = c.get("refined_villain_suggestion", "")
        self.recommended_tropes = c.get("recommended_tropes", [])
        self.anti_tropes = c.get("anti_tropes", [])
        self.hybrid_idea = c.get("hybrid_idea", "")

class AuditResultProxy:
    """プロデューサー企画監査結果のプロキシ"""
    def __init__(self, d: dict):
        self.refined_keywords = d.get("refined_keywords", "")
        self.refined_concept = d.get("refined_concept", "")
        self.refined_mc_suggestion = d.get("refined_mc_suggestion", "")
        self.recommended_tropes = d.get("recommended_tropes", [])
        self.candidates = [CandidateProxy(c) for c in d.get("candidates", [])]

class UltimateHegemonyEngineProxy:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.repo = DataRepositoryProxy()
        self.critique = CritiqueProxy(api_key)
        self.marketing = MarketingProxy(api_key)
        self.narrative = NarrativeProxy(api_key)

    def get_all_books(self) -> List[BookProxy]:
        return self.repo.get_all_books()

    def get_book(self, book_id: int) -> Optional[BookProxy]:
        return self.repo.get_book(book_id)

    def delete_book(self, book_id: int) -> None:
        self.repo.delete_book(book_id)

    def get_all_plots(self, book_id: int) -> List[PlotProxy]:
        return self.repo.get_all_plots(book_id)

    def get_all_non_anchor_chapters(self, book_id: int) -> List[ChapterProxy]:
        return self.repo.get_all_non_anchor_chapters(book_id)

    def get_latest_bible(self, book_id: int) -> Optional[BibleProxy]:
        return self.repo.get_latest_bible(book_id)

    def get_optimization_history(self, book_id: int) -> List[OptimizationHistoryProxy]:
        return self.repo.get_optimization_history(book_id)

    def create_chapter(self, **kwargs) -> None:
        self.repo.create_chapter(**kwargs)

    def delete_chapter(self, book_id: int, ep_num: int) -> None:
        self.repo.delete_chapter(book_id, ep_num)

    def generate_marketing_pack(self, book_id: int, latest_ep: int) -> Optional[Dict[str, Any]]:
        return api_client.generate_marketing(self.api_key, book_id, latest_ep)

    def audit_producer_plan(
        self,
        genre: str,
        keywords: str,
        trend_memo: str,
        sanctuary: str = "",
        originality_score: int = 50,
        platform: str = "カクヨム/なろう",
    ) -> Any:
        try:
            data = api_client.audit_producer_plan(
                api_key=self.api_key,
                genre=genre,
                keywords=keywords,
                trend_memo=trend_memo,
                sanctuary=sanctuary,
                originality_score=originality_score,
                platform=platform
            )
            return AuditResultProxy(data)
        except Exception as e:
            print(f"Error auditing plan: {e}")
            return None

    def get_issues(self, book_id: int) -> List[Dict[str, Any]]:
        return api_client.get_issues(book_id)

    def resolve_issue(self, issue_id: int, action: str) -> Dict[str, Any]:
        return api_client.resolve_issue(issue_id, action, self.api_key)

    def generate_erotic_scene(self, book_id: int, ep_num: int, intensity: int = 2, platform_preset: str = "kakuyomu_romance") -> Optional[str]:
        """官能シーンの生成・研磨を開始する。"""
        try:
            from streamlit_app.state import get_session
            session = get_session()
            config_dict = session.config if hasattr(session, "config") else {}
            return api_client.start_erotic_refinement(self.api_key, config_dict, book_id, ep_num, intensity, platform_preset)
        except Exception as e:
            logger.error(f"generate_erotic_scene failed: {e}")
            return None


class HegemonyServiceProxy:
    def __init__(self, engine: UltimateHegemonyEngineProxy):
        self.engine = engine

    def chapter_import_workflow(self, book_id: int, ep_num: int, text: str, do_refine: bool) -> Dict[str, Any]:
        # chapter_import は即時レスポンスを返すAPIであるため、run_in_backgroundではなく直接呼び出す
        result = api_client.import_chapter(self.engine.api_key, book_id, ep_num, text, do_refine)

        from streamlit_app.state import get_session
        session = get_session()
        if session.config.get("enable_nsfw", False) and session.config.get("erotic_intensity", 0) > 0:
            from src.agents.erotic_integrity import EroticIntegrityChecker
            from src.engine.prompts.erotic_specialist import EroticSpecialist

            specialist = EroticSpecialist()
            intensity = session.config.get("erotic_intensity", 2)
            filtered_text = specialist.metaphor_filter(text, intensity)

            checker = EroticIntegrityChecker()
            is_ok, issues = checker.check_all(filtered_text)
            if not is_ok:
                result["erotic_integrity_issues"] = issues

        return result

    def dispatch_workflow(self, workflow_type: WorkflowType, **kwargs) -> 'ProgressStateProxy':
        return run_in_background(workflow_type, **kwargs)

