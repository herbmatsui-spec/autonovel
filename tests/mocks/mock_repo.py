import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.backend.database.uow_context import current_uow


class MockOutboxEvent:
    def __init__(self, id_val, event_type, payload):
        self.id = id_val
        self.event_type = event_type
        self.payload = payload
        self.status = "pending"
        self.processed_at = None

class MockBaseRepository:
    """汎用的なインメモリリポジトリモック"""
    def __init__(self):
        self.data = {}

    async def get_by_id(self, id_val: Any) -> Optional[Dict[str, Any]]:
        return self.data.get(id_val)

    async def save(self, data: dict) -> Any:
        pass


class MockBookRepository(MockBaseRepository):
    async def get_book(self, book_id: int):
        return self.data.get(book_id)

    async def create_book(self, title: str, genre: str, target_eps: int) -> int:
        b_id = len(self.data) + 1
        self.data[b_id] = {
            "id": b_id,
            "title": title,
            "genre": genre,
            "target_eps": target_eps,
            "created_at": datetime.now()
        }
        return b_id

    async def update_book(self, book_id: int, updates: dict):
        if book_id in self.data:
            self.data[book_id].update(updates)


class MockPlotRepository(MockBaseRepository):
    async def get_plot(self, book_id: int, ep_num: int):
        return self.data.get(f"{book_id}_{ep_num}")

    async def save_plot(self, book_id: int, plot_data: dict):
        ep_num = plot_data.get("ep_num")
        self.data[f"{book_id}_{ep_num}"] = plot_data

    async def get_plots(self, book_id: int) -> List[Dict[str, Any]]:
        return [p for k, p in self.data.items() if str(k).startswith(f"{book_id}_")]


class MockChapterRepository(MockBaseRepository):
    async def get_chapter(self, book_id: int, ep_num: int):
        return self.data.get(f"{book_id}_{ep_num}")

    async def save_chapter(self, book_id: int, chapter_data: dict):
        ep_num = chapter_data.get("ep_num")
        self.data[f"{book_id}_{ep_num}"] = chapter_data


class MockBibleRepository(MockBaseRepository):
    async def get_bible(self, book_id: int):
        return self.data.get(book_id)

    async def save_bible(self, book_id: int, bible_data: dict):
        self.data[book_id] = bible_data


class MockBranchRepository(MockBaseRepository):
    async def create_branch(self, book_id: int, name: str, parent_id: Optional[int] = None, fork_ep_num: int = 0) -> int:
        b_id = len(self.data) + 1
        self.data[b_id] = {
            "id": b_id,
            "book_id": book_id,
            "name": name,
            "parent_id": parent_id,
            "fork_ep_num": fork_ep_num,
            "created_at": datetime.now().isoformat()
        }
        return b_id

    async def get_branches(self, book_id: int) -> List[Any]:
        from src.models import BranchDbModel
        res = []
        for b in self.data.values():
            if b.get("book_id") == book_id:
                res.append(BranchDbModel(**b))
        return res

    async def update_book_current_branch(self, book_id: int, branch_id: int) -> None:
        pass


class MockCharacterRepository(MockBaseRepository):
    async def get_all_characters(self, book_id: int) -> List[Any]:
        from src.models import CharacterDbModel
        res = []
        for c in self.data.values():
            if c.get("book_id") == book_id:
                res.append(CharacterDbModel(**c))
        return res

    async def create_character(self, book_id: int, name: str, role: str, registry_data: Any) -> None:
        c_id = len(self.data) + 1
        self.data[c_id] = {
            "id": c_id,
            "book_id": book_id,
            "name": name,
            "role": role,
            "registry_data": registry_data
        }

    async def update_character_registry(self, char_id: int, registry_data: Any) -> None:
        for c in self.data.values():
            if c.get("id") == char_id:
                c["registry_data"] = registry_data


class MockRulesRepository(MockBaseRepository):
    def __init__(self):
        super().__init__()
        self.masterpieces = {}

    async def create_rule(
        self, target_word: str, instruction: str, level: str = "global",
        domain: str = "all", character_name: Optional[str] = None,
        status: str = "active"
    ) -> int:
        r_id = len(self.data) + 1
        self.data[r_id] = {
            "id": r_id,
            "target_word": target_word,
            "instruction": instruction,
            "level": level,
            "domain": domain,
            "character_name": character_name,
            "status": status,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        return r_id

    async def get_rule(self, rule_id: int) -> Optional[Dict[str, Any]]:
        return self.data.get(rule_id)

    async def get_all_rules(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        res = []
        for r in self.data.values():
            if not status or r.get("status") == status:
                res.append(r)
        return res

    async def get_active_rules(self, domain: str = "all") -> List[Dict[str, Any]]:
        res = []
        for r in self.data.values():
            if r.get("status") == "active":
                if domain == "all" or r.get("domain") == "all" or r.get("domain") == domain:
                    res.append(r)
        return res

    async def update_rule(
        self, rule_id: int, target_word: str, instruction: str, level: str,
        domain: str, character_name: Optional[str], status: str
    ) -> None:
        if rule_id in self.data:
            self.data[rule_id].update({
                "target_word": target_word,
                "instruction": instruction,
                "level": level,
                "domain": domain,
                "character_name": character_name,
                "status": status,
                "updated_at": datetime.now().isoformat()
            })

    async def update_rule_status(self, rule_id: int, status: str) -> None:
        if rule_id in self.data:
            self.data[rule_id]["status"] = status
            self.data[rule_id]["updated_at"] = datetime.now().isoformat()

    async def delete_rule(self, rule_id: int) -> None:
        if rule_id in self.data:
            del self.data[rule_id]

    async def create_masterpiece(self, emotion_or_scene: str, content: str, vector: Optional[List[float]] = None) -> int:
        m_id = len(self.masterpieces) + 1
        self.masterpieces[m_id] = {
            "id": m_id,
            "emotion_or_scene": emotion_or_scene,
            "content": content,
            "vector_json": json.dumps(vector) if vector is not None else None,
            "created_at": datetime.now().isoformat()
        }
        return m_id

    async def get_all_masterpieces(self) -> List[Dict[str, Any]]:
        return list(self.masterpieces.values())

    async def delete_masterpiece(self, mp_id: int) -> None:
        if mp_id in self.masterpieces:
            del self.masterpieces[mp_id]


class MockAuditRepository(MockBaseRepository):
    async def create_audit_issue(
        self, book_id: int, ep_num: int, category: str, severity: str,
        description: str, evidence_past: str = "", evidence_current: str = "",
        constraint_for_next_ep: str = ""
    ) -> int:
        i_id = len(self.data) + 1
        self.data[i_id] = {
            "id": i_id,
            "book_id": book_id,
            "ep_num": ep_num,
            "category": category,
            "severity": severity,
            "description": description,
            "evidence_past": evidence_past,
            "evidence_current": evidence_current,
            "constraint_for_next_ep": constraint_for_next_ep,
            "status": "open"
        }
        return i_id

    async def get_issue(self, issue_id: int) -> Optional[Dict[str, Any]]:
        return self.data.get(issue_id)

    async def get_issues_by_book(self, book_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
        res = []
        for i in self.data.values():
            if i.get("book_id") == book_id:
                if not status or i.get("status") == status:
                    res.append(i)
        return res

    async def update_issue_status(self, issue_id: int, status: str, resolved_note: str = "") -> None:
        if issue_id in self.data:
            self.data[issue_id]["status"] = status
            self.data[issue_id]["resolved_note"] = resolved_note


class MockPromptVersionRepository(MockBaseRepository):
    async def create_prompt_version(
        self, book_id: int, prompt_key: str, version_tag: str, content: str,
        score_before: Optional[float] = None, score_after: Optional[float] = None,
        ab_test_metrics: Optional[Dict[str, Any]] = None, is_active: bool = False
    ) -> Any:
        v_id = len(self.data) + 1
        version = {
            "id": v_id,
            "book_id": book_id,
            "prompt_key": prompt_key,
            "version_tag": version_tag,
            "content": content,
            "score_before": score_before,
            "score_after": score_after,
            "ab_test_metrics": ab_test_metrics or {},
            "is_active": is_active,
            "created_at": datetime.now().isoformat()
        }
        self.data[v_id] = version
        return version

    async def get_prompt_version(self, version_id: int) -> Optional[Dict[str, Any]]:
        return self.data.get(version_id)

    async def get_prompt_versions(self, book_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        res = []
        for v in self.data.values():
            if v.get("book_id") == book_id:
                res.append(v)
        res = sorted(res, key=lambda x: x.get("created_at"), reverse=True)
        return res[:limit]

    async def get_active_prompt_version(self, book_id: int, prompt_key: str) -> Optional[Dict[str, Any]]:
        for v in self.data.values():
            if v.get("book_id") == book_id and v.get("prompt_key") == prompt_key and v.get("is_active"):
                return v
        return None

    async def set_active_prompt_version(self, book_id: int, prompt_key: str, version_id: int) -> None:
        for v in self.data.values():
            if v.get("book_id") == book_id and v.get("prompt_key") == prompt_key:
                v["is_active"] = (v.get("id") == version_id)

    async def update_score_after(self, version_id: int, score: float) -> None:
        if version_id in self.data:
            self.data[version_id]["score_after"] = score

    async def record_rollback(self, version_id: int, reason: str) -> None:
        if version_id in self.data:
            self.data[version_id]["is_active"] = False
            self.data[version_id]["rollback_reason"] = reason


class MockMiscRepository(MockBaseRepository):
    pass


class MockRepository:
    """テスト用に簡易的に利用する統合Repository"""
    def __init__(self, db=None):
        self.db = db or MockDatabaseManager()
        self.books = {}
        self.plots = {}
        self.chapters = {}

    async def get_book(self, book_id: int):
        return self.books.get(book_id)

    async def save_book(self, book_data: dict) -> int:
        b_id = book_data.get("id", len(self.books) + 1)
        book_data["id"] = b_id
        self.books[b_id] = book_data
        return b_id


class MockSession:
    def __init__(self):
        self.added_objects = []

    def add(self, obj):
        self.added_objects.append(obj)

    async def execute(self, *args, **kwargs):
        pass

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass

    async def begin(self):
        pass


class MockDatabaseManager:
    def get_session(self):
        return MockSession()


class MockUnitOfWork:
    def __init__(self, db=None, db_manager=None):
        self.db = db or db_manager or MockDatabaseManager()
        self.session = None
        self._token = None

        # モックリポジトリ群
        self.bible = MockBibleRepository()
        self.books = MockBookRepository()
        self.plots = MockPlotRepository()
        self.chapters = MockChapterRepository()
        self.branches = MockBranchRepository()
        self.characters = MockCharacterRepository()
        self.rules = MockRulesRepository()
        self.audit = MockAuditRepository()
        self.prompt_versions = MockPromptVersionRepository()
        self.misc = MockMiscRepository()

        # ChromaDB への同期のステージングを模倣
        self._chroma_additions = []
        self._chroma_deletions = []
        self.outbox = []

    def stage_chroma_add(self, collection: str, doc_id: str, doc_content: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None):
        self._chroma_additions.append({
            "collection": collection,
            "id": doc_id,
            "content": doc_content,
            "embedding": embedding,
            "metadata": metadata
        })

    def stage_chroma_delete(self, collection: str, ids: List[str]):
        self._chroma_deletions.append({
            "collection": collection,
            "ids": ids
        })

    async def get_pending_outbox_events(self) -> List[Any]:
        return [e for e in self.outbox if e.status == "pending"]

    async def mark_outbox_event_processed(self, event_id: int) -> None:
        for e in self.outbox:
            if e.id == event_id:
                e.status = "done"
                e.processed_at = datetime.now()


    async def __aenter__(self):
        self.session = self.db.get_session()
        await self.session.begin()
        self._token = current_uow.set(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.session.rollback()
        else:
            await self.session.commit()
        if self._token:
            current_uow.reset(self._token)
            self._token = None
        await self.session.close()
