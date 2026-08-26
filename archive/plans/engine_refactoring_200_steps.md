# Engine Refactoring: 200-Step Implementation Plan
**Target**: UltimateHegemonyEngine (42 args) → Facade + 5 Domain Services
**Approach**: Strangler Fig pattern, each step ≤5 min for low-perf LLM
**Branch**: `refactor/engine-decomposition`

---

## Phase 0: Preparation (Steps 1-10)

### 1-5: Environment & Baseline
1. Create branch: `git checkout -b refactor/engine-decomposition`
2. Run full test suite: `pytest tests/ -x -q` → confirm green baseline
3. Note test count: `pytest tests/ --collect-only | grep "test session" | tail -1`
4. Create ADR draft: `docs/adr/0003-engine-decomposition.md` (copy from review)
5. Add ADR to git: `git add docs/adr/0003-engine-decomposition.md && git commit -m "docs: add ADR-003 engine decomposition plan"`

### 6-10: Inventory Current Engine Surface
6. `grep -n "engine\." src/backend/workflows/*.py | head -50` → list all engine.* usages
7. `grep -n "engine\." src/backend/routers/*.py | head -30` → list router usages
8. `grep -n "UltimateHegemonyEngine" src/**/*.py` → list all imports
9. `grep -n "engine\." streamlit_app/**/*.py | head -20` → list UI usages
10. Save inventory: `cat > /tmp/engine_usages.txt` (paste all grep results)

---

## Phase 1: EngineConfig & EngineFacade (Steps 11-35)

### 11-15: EngineConfig Dataclass
11. Create file: `src/backend/engine_config.py`
12. Add imports: `from dataclasses import dataclass` + `from src.core.config import AdaptiveCooldown`
13. Define `@dataclass(frozen=True, slots=True) class EngineConfig:` with fields:
    - `api_key: str`
    - `cooldown: AdaptiveCooldown`
14. Add factory: `def create(api_key: str, cooldown: AdaptiveCooldown) -> EngineConfig:`
15. Write unit test: `tests/unit/test_engine_config.py` (instantiate, verify frozen)

### 16-20: EngineFacade Skeleton
16. Create file: `src/backend/engine_facade.py`
17. Add imports: `from src.backend.engine_config import EngineConfig` + all service protocols
17b. Add: `from src.backend.protocols import PlanningPort, WritingPort, CritiquePort, BiblePort, TensionPort`
18. Define class `EngineFacade:` with `__init__` taking `config: EngineConfig` + 5 service ports + `repo, db, pm, ctx_mgr, llm, cooldown`
19. Add read-only properties delegating to services: `planning`, `writing`, `critique`, `bible`, `tension`
20. Write test: `tests/unit/test_engine_facade.py` (mock services, verify delegation)

### 21-25: Migrate sync_bible & resolve_bible_setting
21. In `EngineFacade`, add `async def sync_bible(self, book_id: int, reporter=None):` → `return await self.bible.sync_bible_lifecycle(book_id, reporter)`
22. Add `async def resolve_bible_setting(self, setting_id: int, status: str):` → `await self.repo.resolve_pending_setting(setting_id, status)`
23. Copy `determine_target_tension` to `EngineFacade` (temporarily, will move to TensionService later)
24. Copy `validate_tension_deviation` to `EngineFacade` (temporarily)
25. Run test: `pytest tests/unit/test_engine_facade.py::test_sync_bible -xvs`

### 26-30: Backward Compatibility Layer
26. In `src/backend/engine.py`, add `from src.backend.engine_facade import EngineFacade`
27. In `UltimateHegemonyEngine.__init__`, add: `self._facade = EngineFacade(...)` (pass all current args)
28. Change `sync_bible` to: `return await self._facade.sync_bible(book_id, reporter)`
29. Change `resolve_bible_setting` to: `return await self._facade.resolve_bible_setting(setting_id, status)`
30. Run: `pytest tests/unit/test_engines.py -xvs` (verify existing engine tests pass)

### 31-35: Container Integration
31. Open `src/core/container.py` (AppContainer)
32. Add provider: `engine_facade = providers.Factory(EngineFacade, config=..., planning_service=..., ...)`
33. Keep `engine = providers.Factory(UltimateHegemonyEngine, ...)` for now (alias)
34. In `config/container.py` (legacy Container), add same facade provider
35. Verify: `python -c "from config.container import Container; c=Container(); print(c.engine_facade())"`

---

## Phase 2: Protocol Definitions (Steps 36-55)

### 36-40: Create Protocols File
36. Create `src/backend/protocols.py`
37. Define `PlanningPort(Protocol):` with methods:
    - `async def create_hegemony_plan(self, genre, keywords, style_key, concept, title, cheat_scale, growth_curve, system_assist, cost_severity, target_eps, initial_plot_limit, reporter) -> tuple[int, Bible]`
    - `async def audit_bible_completeness(self, bible, reporter) -> bool`
38. Define `WritingPort(Protocol):` with:
    - `async def generate_episodes_pipeline(self, book_id, start_ep, end_ep, passion, target_word_count, reporter, mode, is_easy_mode) -> tuple[int, list]`
    - `async def generate_episodes(self, book_id, write_from, write_to, passion, word_count, do_refine, reporter, env_state, mode) -> int`
39. Define `CritiquePort(Protocol):` with:
    - `async def run_critique_optimization(self, book_id: int, reporter) -> dict`
40. Define `BiblePort(Protocol):` with:
    - `async def sync_bible_lifecycle(self, book_id: int, reporter) -> Bible`
    - `async def resolve_pending_setting(self, setting_id: int, status: str)`

### 41-45: Tension & Repository Protocols
41. Define `TensionPort(Protocol):` with:
    - `async def determine_target_tension(self, book_id: int, ep_num: int, genre: str, story_type: str | None) -> float`
    - `async def validate_tension_deviation(self, ep_num: int, generated_tension: float, book_id: int, tolerance: float) -> tuple[bool, float]`
42. Define `DataRepository(Protocol):` with methods used by workflows:
    - `get_book`, `get_plot`, `get_all_plots`, `update_plot_target_tension`, `save_chapter`, etc. (copy from `src/backend/database/repository.py` interface)
43. Add `__all__ = ["PlanningPort", "WritingPort", "CritiquePort", "BiblePort", "TensionPort", "DataRepository"]`
44. Write test: `tests/unit/test_protocols.py` (verify protocols import, structural subtyping works)
45. Run: `pytest tests/unit/test_protocols.py -xvs`

### 46-50: Make Services Implement Protocols (Planning)
46. Open `src/agents/planner.py` (or wherever `create_hegemony_plan` lives)
47. Add `implements PlanningPort` comment (or just ensure method signatures match)
48. Verify: `python -c "from src.agents.planner import Planner; from src.backend.protocols import PlanningPort; assert issubclass(Planner, PlanningPort)"` (structural, so just check methods exist)
49. Repeat for `BibleGenerator` → `BiblePort`
50. Run: `pytest tests/unit/test_planner.py -xvs` (ensure no regression)

### 51-55: Make Services Implement Protocols (Writing, Critique, Tension)
51. Check `src/agents/writer.py` → matches `WritingPort`
52. Check `src/agents/critique.py` → matches `CritiquePort`
53. Create `TensionService` stub in `src/backend/tension_service.py` with `TensionPort` methods (copy from EngineFacade temporarily)
54. Verify all 5 services have matching methods
55. Run: `pytest tests/unit/ -k "planner or writer or critique" -x --tb=short`

---

## Phase 3: PlanningService Extraction (Steps 56-80)

### 56-60: Create PlanningService Class
56. Create `src/backend/planning_service.py`
57. Class `PlanningService:` implementing `PlanningPort`
58. `__init__(self, planner, bible_generator, repo, pm, ctx_mgr, reporter_factory)` (inject deps, not engine)
59. Move `create_hegemony_plan` from planner/bible_generator → delegate to injected planner
60. Move `audit_bible_completeness` → delegate to injected planner's auditor

### 61-65: Wire PlanningService in Container
61. In `src/core/container.py`, add: `planning_service = providers.Factory(PlanningService, planner=..., bible_generator=..., repo=..., pm=..., ctx_mgr=...)`
62. In `config/container.py`, add same provider
63. In `EngineFacade.__init__`, replace `planner` arg with `planning_service: PlanningPort`
64. Update `EngineFacade.sync_bible` to use `self.planning.sync_bible_lifecycle` (via BiblePort)
65. Test: `pytest tests/unit/test_engine_facade.py::test_sync_bible -xvs`

### 66-70: Migrate FullAutoWorkflow
66. Open `src/backend/workflows/full_auto_workflow.py`
67. Change `__init__(self, engine)` → `__init__(self, planning_service: PlanningPort, writing_service: WritingPort, reporter: StatusReporter)`
68. Replace `self.engine.planner.create_hegemony_plan` → `self.planning.create_hegemony_plan`
69. Replace `self.engine.planner.plan_auditor.audit_bible_completeness` → `self.planning.audit_bible_completeness`
70. Run: `pytest tests/unit/test_workflows.py::test_full_auto_workflow -xvs`

### 71-75: Migrate PlanGenerationWorkflow
71. Open `src/backend/workflows/plan_generation_workflow.py`
72. Same init change: inject `PlanningPort`
73. Replace `engine.planner` calls → `self.planning`
74. Update container wiring for this workflow
75. Test: `pytest tests/unit/test_workflows.py::test_plan_generation_workflow -xvs`

### 76-80: Verify All Planning Workflows
76. `grep -r "engine\.planner" src/backend/workflows/` → should be empty
77. `grep -r "engine\.bible_agent" src/backend/workflows/` → should be empty
78. Run all workflow tests: `pytest tests/unit/test_workflows.py -x --tb=short`
79. Run integration: `pytest tests/integration/test_plot_workflow.py -x --tb=short`
80. Commit: `git commit -am "refactor: extract PlanningService, migrate planning workflows"`

---

## Phase 4: WritingService Extraction (Steps 81-110)

### 81-85: Create WritingService
81. Create `src/backend/writing_service.py`
82. Class `WritingService:` implementing `WritingPort`
83. `__init__(self, writer, style_rag, formatter, plot_expander, repo, pm, ctx_mgr, reporter_factory)`
83b. (Note: `plot_expander` may be separate agent; inject it)
84. Move `generate_episodes_pipeline` logic from `engine.writer` → delegate to injected `writer`
85. Move `generate_episodes` logic similarly

### 86-90: Wire WritingService
86. In `src/core/container.py`: `writing_service = providers.Factory(WritingService, writer=..., style_rag=..., formatter=..., plot_expander=..., repo=..., pm=..., ctx_mgr=...)`
87. In `config/container.py`: same
88. In `EngineFacade`: replace `writer` arg with `writing_service: WritingPort`
89. Update `EngineFacade` properties to delegate to `writing_service`
90. Test: `pytest tests/unit/test_engine_facade.py -xvs`

### 91-95: Migrate EpisodeWritingWorkflow
91. Open `src/backend/workflows/episode_writing_workflow.py`
92. Change init: inject `WritingPort`, `TensionPort` (for prefetch), `DataRepository`
93. Replace `self.engine.writer.generate_episodes_pipeline` → `self.writing.generate_episodes_pipeline`
94. Replace `self.engine.style_rag` → inject `style_rag` separately or via writing service
95. Update `_trigger_prefetch` to use injected deps

### 96-100: Migrate RetryFailedEpisodesWorkflow
96. Open `src/backend/workflows/retry_failed_episodes_workflow.py`
96b. Same injection pattern
97. Replace `engine.writer` calls
98. Update container wiring for this workflow
99. Test: `pytest tests/unit/test_workflows.py::test_retry_failed -xvs`
100. Run all writing workflow tests

### 101-105: Migrate ChapterImportWorkflow
101. Open `src/backend/workflows/chapter_import_workflow.py`
102. Inject `WritingPort` (for refine), `DataRepository`
103. Replace `engine.writer` calls
104. Update container
105. Test

### 106-110: Migrate RefineEroticWorkflow
106. Open `src/backend/workflows/refine_erotic_workflow.py`
107. Inject `WritingPort` (has refine method), `DataRepository`
108. Replace `engine.writer.refine_erotic` call
109. Update container
110. Run: `pytest tests/integration/test_erotic_refine_workflow.py -xvs` + all workflow tests

---

## Phase 5: CritiqueService Extraction (Steps 111-125)

### 111-115: Create CritiqueService
111. Create `src/backend/critique_service.py`
112. Class `CritiqueService:` implementing `CritiquePort`
113. `__init__(self, critique, auditor, validator, narrative, repo, pm, ctx_mgr)`
114. Implement `run_critique_optimization(book_id, reporter)` → delegate to `critique` agent
115. Add helper methods for audit issues, narrative metrics

### 116-120: Wire & Migrate CritiqueOptimizationWorkflow
116. Container: `critique_service = providers.Factory(CritiqueService, ...)`
117. EngineFacade: add `critique_service: CritiquePort`
118. Open `src/backend/workflows/critique_optimization_workflow.py`
119. Inject `CritiquePort`, `DataRepository`
120. Replace `engine.critique.run_critique_optimization_workflow` → `self.critique.run_critique_optimization`

### 121-125: Migrate LogicalAuditWorkflow
121. Open `src/backend/workflows/logical_audit_workflow.py`
122. Inject `CritiquePort` (has auditor), `DataRepository`
123. Replace `engine.auditor` calls
124. Update container
125. Test: `pytest tests/unit/test_workflows.py::test_critique -xvs && pytest tests/unit/test_narrative_metrics_audit.py -xvs`

---

## Phase 6: BibleService Extraction (Steps 126-140)

### 126-130: Create BibleService
126. Create `src/backend/bible_service.py`
127. Class `BibleService:` implementing `BiblePort`
128. `__init__(self, bible_generator, repo, pm, marketing, ctx_mgr)`
129. Implement `sync_bible_lifecycle` (delegate to bible_generator)
130. Implement `resolve_pending_setting` (delegate to repo)

### 131-135: Wire & Migrate Remaining Bible Usages
131. Container: `bible_service = providers.Factory(BibleService, ...)`
132. EngineFacade: add `bible_service: BiblePort`
133. Check `grep -r "engine\.bible_agent" src/` → migrate any remaining
134. Check `grep -r "engine\.planner" src/` (should be empty now)
135. Run all tests: `pytest tests/ -x --tb=short -q`

### 136-140: MarketingGenerationWorkflow
136. Open `src/backend/workflows/marketing_generation_workflow.py`
137. Inject `BiblePort` (for marketing), `DataRepository`
138. Replace `engine.marketing` calls
139. Update container
140. Test: `pytest tests/unit/test_workflows.py::test_marketing -xvs`

---

## Phase 7: TensionService Extraction (Steps 141-155)

### 141-145: Create TensionService (Complete)
141. Open `src/backend/tension_service.py` (stub from step 53)
142. Implement `determine_target_tension` (copy from EngineFacade, use injected `repo`, `ctx_mgr`)
143. Implement `validate_tension_deviation` (copy from EngineFacade)
144. Add `select_tension_curve`, `calculate_progress`, `get_target_tension` imports from `tension_utils`
145. Write unit test: `tests/unit/test_tension_service.py`

### 146-150: Wire TensionService
146. Container: `tension_service = providers.Factory(TensionService, repo=..., ctx_mgr=...)`
147. EngineFacade: add `tension_service: TensionPort`
148. In EngineFacade, delegate `determine_target_tension` → `self.tension.determine_target_tension`
149. Delegate `validate_tension_deviation` → `self.tension.validate_tension_deviation`
150. Test: `pytest tests/unit/test_tension_service.py -xvs && pytest tests/unit/test_engine_facade.py -xvs`

### 151-155: Migrate PlotExpansionWorkflow & PlotRebuildWorkflow
151. Open `src/backend/workflows/plot_expansion_workflow.py`
152. Inject `TensionPort`, `PlanningPort` (for plot_agent), `DataRepository`
153. Replace `engine.plot_agent` and `engine.determine_target_tension`
154. Open `src/backend/workflows/plot_rebuild_workflow.py` → same
155. Test: `pytest tests/integration/test_plot_workflow.py -xvs`

---

## Phase 8: CoreEngine & Final Facade Cleanup (Steps 156-175)

### 156-160: Create CoreEngine (Minimal)
156. Create `src/backend/core_engine.py`
157. Class `CoreEngine:` with `__init__(self, repo, db, uow_factory)`
158. Add `@asynccontextmanager async def transaction(self):` yielding UoW
159. Add `async def get_book(self, book_id): return await self.repo.get_book(book_id)` (convenience)
160. Test: `tests/unit/test_core_engine.py`

### 161-165: Update EngineFacade to Use CoreEngine
161. In `EngineFacade.__init__`, add `core_engine: CoreEngine`
162. Remove `repo`, `db` from EngineFacade args (access via `self.core_engine.repo`)
163. Update EngineFacade methods that used `self.repo` → `self.core_engine.repo`
164. Update container: `core_engine = providers.Factory(CoreEngine, repo=..., db=..., uow_factory=...)`
165. Update `engine_facade` provider to inject `core_engine`

### 166-170: Deprecate UltimateHegemonyEngine Methods
166. In `src/backend/engine.py`, add deprecation warnings to all methods
167. Mark class with `# DEPRECATED: Use EngineFacade + CoreEngine`
168. Verify no workflow imports `UltimateHegemonyEngine` directly
169. `grep -r "UltimateHegemonyEngine" src/backend/workflows/` → should be empty
170. `grep -r "UltimateHegemonyEngine" src/backend/routers/` → should be empty

### 171-175: Router Migration
171. Check `src/backend/server.py` imports
172. Change `from src.backend.engine_helpers import get_engine as resolve_engine` → `from src.backend.engine_facade import EngineFacade`
173. Update `resolve_engine` to return `EngineFacade` (or create `get_engine_facade`)
174. Update any direct `engine.` calls in routers to use facade properties
175. Test: `pytest tests/integration/test_app_integration.py -xvs`

---

## Phase 9: Remove UltimateHegemonyEngine (Steps 176-185)

### 176-180: Final Verification
176. `grep -r "UltimateHegemonyEngine" src/ --include="*.py" | grep -v "__pycache__" | grep -v test` → must be empty
177. `grep -r "engine\." src/backend/workflows/ src/backend/routers/ streamlit_app/ --include="*.py" | grep -v "engine_facade" | grep -v "core_engine"` → must be empty
178. Run full test suite: `pytest tests/ -x --tb=short -q` → all green
179. Run lint: `ruff check src/` → clean
180. Run typecheck: `mypy src/` → clean (or only pre-existing errors)

### 181-185: Delete & Commit
181. `git rm src/backend/engine.py`
182. `git rm src/backend/engine_helpers.py` (if only exported old engine)
183. Remove `UltimateHegemonyEngine` from any `__init__.py` exports
184. `git commit -am "refactor: remove UltimateHegemonyEngine, complete EngineFacade + 5 services migration"`
185. Tag: `git tag -a refactor/engine-decomposition-v1 -m "Engine decomposition complete"`

---

## Phase 10: Streamlit UI Migration (Steps 186-195)

### 186-190: Update Streamlit Engine Service
186. Open `streamlit_app/engine_service.py`
187. Change `EngineService.get_instance` to return `EngineFacade`
188. Update any `engine.` attribute accesses to use facade properties
189. Test: `streamlit run streamlit_app/app.py` (manual smoke test)
190. Run UI tests: `pytest tests/integration/test_ui_backend_communication.py -xvs`

### 191-195: Clean Up & Document
191. Update `docs/architecture/engine.md` with new diagram
192. Update `README.md` if it references old engine
193. Write migration guide: `docs/migration/engine_decomposition.md`
194. Final full test run: `pytest tests/ --tb=line -q`
195. Create PR: `gh pr create --title "refactor: Engine decomposition (Facade + 5 Services)" --body-file docs/migration/engine_decomposition.md`

---

## Phase 11: Polish & Edge Cases (Steps 196-200)

### 196-200: Final Polish
196. Add missing docstrings to all 5 services + facade + core engine
197. Ensure all protocols have `__all__` exports
198. Add integration test for full auto workflow E2E: `tests/integration/test_full_auto_e2e.py`
199. Benchmark: `python -m tests.benchmark_engine` (ensure no perf regression)
200. Celebrate 🎉

---

## Quick Reference: File Creation Checklist

### New Files (15)
- [ ] `src/backend/engine_config.py`
- [ ] `src/backend/engine_facade.py`
- [ ] `src/backend/protocols.py`
- [ ] `src/backend/planning_service.py`
- [ ] `src/backend/writing_service.py`
- [ ] `src/backend/critique_service.py`
- [ ] `src/backend/bible_service.py`
- [ ] `src/backend/tension_service.py`
- [ ] `src/backend/core_engine.py`
- [ ] `tests/unit/test_engine_config.py`
- [ ] `tests/unit/test_engine_facade.py`
- [ ] `tests/unit/test_protocols.py`
- [ ] `tests/unit/test_tension_service.py`
- [ ] `tests/unit/test_core_engine.py`
- [ ] `tests/integration/test_full_auto_e2e.py`

### Modified Files (20+)
- [ ] `src/core/container.py` (AppContainer)
- [ ] `config/container.py` (legacy Container)
- [ ] `src/backend/server.py`
- [ ] `src/backend/engine.py` (→ delete)
- [ ] `src/backend/workflows/*.py` (11 files)
- [ ] `streamlit_app/engine_service.py`
- [ ] `src/backend/engine_helpers.py` (→ delete or update)

---

## Rollback Plan (if needed)
```bash
# At any phase, rollback to last commit:
git stash
git checkout main
# Or reset branch:
git reset --hard HEAD~1
```

---

## Time Estimates
| Phase | Steps | Est. Time (low-perf LLM) |
|-------|-------|-------------------------|
| 0-1   | 1-35  | 2-3 hours |
| 2     | 36-55 | 1-2 hours |
| 3     | 56-80 | 2-3 hours |
| 4     | 81-110| 3-4 hours |
| 5     | 111-125| 1-2 hours |
| 6     | 126-140| 1-2 hours |
| 7     | 141-155| 1-2 hours |
| 8     | 156-175| 2-3 hours |
| 9     | 176-185| 1 hour |
| 10    | 186-195| 1-2 hours |
| 11    | 196-200| 1 hour |
| **Total** | **200** | **16-27 hours** |

---

## Success Criteria
- [ ] All 200 steps completed
- [ ] `pytest tests/ -x --tb=short` → 0 failures
- [ ] `ruff check src/` → 0 errors
- [ ] `mypy src/` → 0 new errors
- [ ] No `UltimateHegemonyEngine` references in production code
- [ ] Streamlit app loads and runs basic workflow
- [ ] ADR-003 marked "Accepted" with implementation notes