import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class MockApiClient:
    """Mock API Client simulating streamlit_app/api_client.py."""
    def __init__(self):
        self.books = {}
        self.plots = {}
        self.chapters = {}
        self.bibles = {}
        self.tasks = {}
        self.issues = {}
        self.patches = {}
        self.prompt_versions = {}
        self.opt_history = {}

        # Prepopulate with dummy data
        self.add_mock_book(1, "テスト用の本", "ファンタジー", 5)

    def add_mock_book(self, book_id: int, title: str, genre: str, target_eps: int):
        self.books[book_id] = {
            "id": book_id,
            "title": title,
            "genre": genre,
            "target_eps": target_eps,
            "created_at": datetime.now().isoformat()
        }
        self.plots[book_id] = []
        self.chapters[book_id] = []
        self.bibles[book_id] = {
            "book_id": book_id,
            "characters": [],
            "world_settings": "剣と魔法のファンタジー"
        }
        self.issues[book_id] = []
        self.patches[book_id] = []
        self.prompt_versions[book_id] = []
        self.opt_history[book_id] = []

    def list_books(self) -> List[Dict[str, Any]]:
        return list(self.books.values())

    def get_book(self, book_id: int) -> Optional[Dict[str, Any]]:
        return self.books.get(book_id)

    def delete_book(self, book_id: int) -> bool:
        if book_id in self.books:
            del self.books[book_id]
            return True
        return False

    def get_plots(self, book_id: int) -> List[Dict[str, Any]]:
        return self.plots.get(book_id, [])

    def get_chapters(self, book_id: int) -> List[Dict[str, Any]]:
        return self.chapters.get(book_id, [])

    def get_bible(self, book_id: int) -> Dict[str, Any]:
        return self.bibles.get(book_id, {})

    def get_opt_history(self, book_id: int) -> List[Dict[str, Any]]:
        return self.opt_history.get(book_id, [])

    def get_task_status(self, task_id: str, timeout: float = 30.0) -> Dict[str, Any]:
        return self.tasks.get(task_id, {
            "is_running": False,
            "message": "完了",
            "logs": ["Mock task finished successfully."],
            "error": None
        })

    def stop_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            self.tasks[task_id]["is_running"] = False
            self.tasks[task_id]["message"] = "停止済み"
            return True
        return False

    def generate_easy(self, api_key: str, config: dict, genre: str, keywords: str, archetype_key: str, target_eps: int, initial_limit: int, word_count: int, concept: str, tone_vibe: float) -> Optional[str]:
        task_id = "task_easy_mock"
        self.tasks[task_id] = {
            "is_running": True,
            "message": "イージーモード実行中...",
            "logs": ["Easy generation mock started"],
            "error": None
        }
        book_id = len(self.books) + 1
        self.add_mock_book(book_id, f"Easy Book {book_id}", genre, target_eps)
        self.tasks[task_id]["is_running"] = False
        self.tasks[task_id]["message"] = "完了"
        self.tasks[task_id]["result_data"] = {"book_id": book_id}
        return task_id

    def generate_episodes(self, api_key: str, config: dict, book_id: int, write_from: int, write_to: int, passion: float, word_count: int, do_refine: bool, env_state: Dict[str, str], pipeline_mode: bool) -> Optional[str]:
        task_id = "task_episodes_mock"
        self.tasks[task_id] = {
            "is_running": False,
            "message": "完了",
            "logs": ["Episode generation finished"],
            "error": None
        }
        self.chapters.setdefault(book_id, []).append({
            "ep_num": write_from,
            "title": f"第{write_from}話 モック",
            "content": "モックの本文です。" * 20,
            "summary": "モックのあらすじ",
            "killer_phrase": "キラーフレーズ",
            "ai_insight": "AI考察",
            "world_state": {},
            "trinity_review_log": {},
            "created_at": datetime.now().isoformat()
        })
        return task_id

    def plan_generation(self, api_key: str, config: dict, params: Dict[str, Any]) -> Optional[str]:
        task_id = "task_plan_mock"
        self.tasks[task_id] = {
            "is_running": False,
            "message": "完了",
            "logs": ["Planning finished"],
            "error": None
        }
        return task_id

    def retry_failed_episodes(self, api_key: str, config: dict, book_id: int, passion: float, word_count: int) -> Optional[str]:
        task_id = "task_retry_mock"
        self.tasks[task_id] = {
            "is_running": False,
            "message": "完了",
            "logs": ["Retry finished"],
            "error": None
        }
        return task_id

    def expand_plots(self, api_key: str, config: dict, book_id: int, gen_from: int, gen_to: int) -> Optional[str]:
        task_id = "task_expand_mock"
        self.tasks[task_id] = {
            "is_running": False,
            "message": "完了",
            "logs": ["Expand plots finished"],
            "error": None
        }
        for ep in range(gen_from, gen_to + 1):
            self.plots.setdefault(book_id, []).append({
                "ep_num": ep,
                "title": f"第{ep}話プロット モック",
                "one_line_summary": "一言サマリー",
                "detailed_blueprint": "詳細プロット...",
                "tension": 50,
                "tension_delta": 0,
                "catharsis": 10,
                "is_catharsis": False,
                "love_meter": 0
            })
        return task_id

    def rebuild_plots(self, api_key: str, config: dict, params: Dict[str, Any]) -> Optional[str]:
        task_id = "task_rebuild_mock"
        self.tasks[task_id] = {
            "is_running": False,
            "message": "完了",
            "logs": ["Rebuild finished"],
            "error": None
        }
        return task_id

    def critique_optimize(self, api_key: str, config: dict, book_id: int) -> Optional[str]:
        task_id = "task_critique_mock"
        self.tasks[task_id] = {
            "is_running": False,
            "message": "完了",
            "logs": ["Critique finished"],
            "error": None
        }
        return task_id

    def import_chapter(self, api_key: str, book_id: int, ep_num: int, import_text: str, do_refine: bool) -> Optional[str]:
        task_id = "task_import_mock"
        self.tasks[task_id] = {
            "is_running": False,
            "message": "完了",
            "logs": ["Import finished"],
            "error": None
        }
        self.chapters.setdefault(book_id, []).append({
            "ep_num": ep_num,
            "title": f"第{ep_num}話 インポートモック",
            "content": import_text,
            "summary": "インポート要約",
            "killer_phrase": "",
            "ai_insight": "",
            "world_state": {},
            "trinity_review_log": {},
            "created_at": datetime.now().isoformat()
        })
        return task_id

    def generate_marketing(self, api_key: str, book_id: int, latest_ep: int) -> Optional[str]:
        task_id = "task_marketing_mock"
        self.tasks[task_id] = {
            "is_running": False,
            "message": "完了",
            "logs": ["Marketing generated"],
            "error": None
        }
        return task_id

    def analyze_style_dna(self, api_key: str, sample: str) -> Dict[str, Any]:
        return {
            "style_dna": {
                "sentence_length": "medium",
                "pacing": "fast",
                "vocabulary": "standard"
            }
        }

    def audit_producer_plan(self, api_key: str, genre: str, keywords: str, trend_memo: str, sanctuary: str = "", originality_score: int = 50, platform: str = "カクヨム/なろう") -> Dict[str, Any]:
        return {
            "refined_keywords": keywords,
            "refined_concept": trend_memo,
            "refined_mc_suggestion": "主人公の提案",
            "recommended_tropes": ["追放", "チート"],
            "candidates": [
                {
                    "plan_name": "提案プラン1",
                    "plan_type": "王道",
                    "refined_keywords": keywords,
                    "refined_concept": trend_memo,
                    "refined_mc_suggestion": "主人公",
                    "refined_villain_suggestion": "悪役",
                    "recommended_tropes": ["追放"],
                    "anti_tropes": ["バッドエンド"],
                    "hybrid_idea": "ハイブリッドアイデア"
                }
            ]
        }

    def export_package(self, api_key: str, book_id: int) -> Any:
        class MockResponse:
            def __init__(self):
                self.content = b"mock export package zip contents"
                self.headers = {"Content-Disposition": 'attachment; filename="mock_export.zip"'}
        return MockResponse()

    def create_chapter(self, book_id: int, ep_num: int, title: str, content: str, summary: str, killer_phrase: str, ai_insight: str, world_state: dict, trinity_review_log: dict, created_at: str) -> bool:
        self.chapters.setdefault(book_id, []).append({
            "ep_num": ep_num,
            "title": title,
            "content": content,
            "summary": summary,
            "killer_phrase": killer_phrase,
            "ai_insight": ai_insight,
            "world_state": world_state,
            "trinity_review_log": trinity_review_log,
            "created_at": created_at
        })
        return True

    def delete_chapter(self, book_id: int, ep_num: int) -> bool:
        if book_id in self.chapters:
            self.chapters[book_id] = [c for c in self.chapters[book_id] if c.get("ep_num") != ep_num]
            return True
        return False

    def get_issues(self, book_id: int) -> List[Dict[str, Any]]:
        return self.issues.get(book_id, [])

    def resolve_issue(self, issue_id: int, action: str, api_key: str) -> Dict[str, Any]:
        for book_id, issues_list in self.issues.items():
            for issue in issues_list:
                if issue.get("id") == issue_id:
                    issue["status"] = "resolved"
                    issue["resolved_note"] = action
                    return {"status": "success", "issue": issue}
        return {"status": "error", "message": "Issue not found"}

    def save_pending_patch(self, book_id: int, patch_type: str, patch_content: str, ab_test_result: Dict[str, Any]) -> Dict[str, Any]:
        patch_id = len(self.patches.get(book_id, [])) + 1
        patch = {
            "id": patch_id,
            "book_id": book_id,
            "patch_type": patch_type,
            "patch_content": patch_content,
            "ab_test_result": ab_test_result,
            "status": "pending"
        }
        self.patches.setdefault(book_id, []).append(patch)
        return {"success": True, "patch": patch}

    def get_pending_patches(self, book_id: int) -> List[Dict[str, Any]]:
        return [p for p in self.patches.get(book_id, []) if p.get("status") == "pending"]

    def approve_patch(self, patch_id: int) -> Dict[str, Any]:
        for book_id, patches_list in self.patches.items():
            for p in patches_list:
                if p.get("id") == patch_id:
                    p["status"] = "approved"
                    return {"success": True}
        return {"success": False, "error": "Patch not found"}

    def reject_patch(self, patch_id: int) -> Dict[str, Any]:
        for book_id, patches_list in self.patches.items():
            for p in patches_list:
                if p.get("id") == patch_id:
                    p["status"] = "rejected"
                    return {"success": True}
        return {"success": False, "error": "Patch not found"}

    def get_prompt_versions(self, book_id: int) -> List[Dict[str, Any]]:
        return self.prompt_versions.get(book_id, [])

    def rollback_prompt_version(self, book_id: int, version_id: int) -> Dict[str, Any]:
        return {"success": True, "message": f"Rolled back to version {version_id}"}
