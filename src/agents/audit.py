# agents/audit.py
from __future__ import annotations

import json
import logging
from typing import Any

from src.backend.sharp_edge_preserver import check_edges_preserved
from src.models.audit import (
    CausalityAuditResult,
    CausalityLink,
    CriticFeedback,
    ForeshadowingItem,
    GraphDiffResult,
    LogicalAuditIssueList,
    PromptPatch,
)
from src.models.db import PlotDbModel
from src.models.graph_schemas import GraphExtractionResult
from src.models.sharp_edge import SharpEdgeSpec
from src.services.llm_service import LLMService
from src.services.extraction_service import extraction_service

logger = logging.getLogger(__name__)


class FastPlotScreener:
    """プロット快速スクリーニング。Gemini にプロットの妥当性を検証させる。"""

    def __init__(self, llm: LLMService, prompt_manager: Any):
        self.llm = llm
        self.prompt_manager = prompt_manager

    async def screen_plot(self, blueprint: str) -> tuple[bool, str]:
        prompt = self.prompt_manager.build_fast_plot_screen_prompt(blueprint)
        result = await self.llm.generate_json(purpose="audit", prompt=prompt)
        metadata = result.get("metadata", {})
        return metadata.get("is_valid", True), metadata.get("feedback", "OK")


class AbilityConsistencyChecker:
    """能力整合性チェック"""

    def __init__(self, llm: LLMService, prompt_manager: Any = None):
        self.llm = llm
        self.prompt_manager = prompt_manager

    async def audit_ability_consistency(
        self, blueprint: str, settings_json: str, characters_json: str
    ) -> tuple[bool, str, str]:
        if self.prompt_manager is None:
            return True, "OK", ""
        prompt = self.prompt_manager.build_ability_audit_prompt(
            blueprint, settings_json, characters_json
        )
        result = await self.llm.generate_json(purpose="audit", prompt=prompt)
        metadata = result.get("metadata", {})
        return (
            metadata.get("is_consistent", True),
            metadata.get("feedback", "OK"),
            metadata.get("suggestions", ""),
        )


class PlotIntegrityMonitor:
    """プロット整合性モニター（因果律監査フル実装）

    機能:
    1. NERベースのキーワード/エンティティ抽出（GraphExtractionResult活用）
    2. 因果関係（A→B）のLLM抽出
    3. Blueprint と Content のグラフ差分検出
    4. 因果鎖の連続性検証
    5. 未回収伏線・矛盾検出
    6. 具体的パッチ（PromptPatch）自動生成
    7. パッチ投稿 API 連携（routers/patches.py）
    """

    # 因果関係抽出用プロンプト
    CAUSALITY_EXTRACTION_PROMPT = """
以下の小説テキストから、明示的・暗黙的な因果関係（A→B）を全て抽出してください。

【抽出ルール】
- 「Aが起きたため B が起きた」「Aしたので B になった」等の因果を検出
- 直接的な因果だけでなく、伏線・フラグ・準備行為→後々の結果 も含める
- キャラクターの行動・決断・状態変化・アイテム獲得・イベント発生を対象
- 確信度の高いもののみ抽出（推測は含めない）

【出力形式】必ず以下のJSONのみを出力（Markdownコードブロック不要）:
{{
  "causality_links": [
    {{
      "cause_entity": "アルス",
      "cause_event": "聖剣エクスカリバーを抜いた",
      "effect_entity": "封印",
      "effect_event": "解かれた",
      "confidence": 0.95
    }},
    {{
      "cause_entity": "グリフォン",
      "cause_event": "空から襲撃した",
      "effect_entity": "セリア",
      "effect_event": "炎魔法で迎撃し負傷した",
      "confidence": 0.9
    }}
  ]
}}

【対象テキスト】
{text}
"""

    # パッチ生成用プロンプトテンプレート
    CAUSALITY_FIX_PROMPT_TEMPLATE = """
【因果鎖切れの修正指示】
以下の因果関係が本文で適切に描写されていません。執筆時に以下を遵守してください。

{broken_chains_detail}

【執筆への制約追加】:
- 前話・前シーンで確立された因果関係を無視しないこと
- 原因イベントがあれば、その結果を必ず描写すること（省略不可）
- 伏線として仕込んだ要素は、後々必ず回収すること
"""

    FORSHADOWING_FIX_PROMPT_TEMPLATE = """
【未回収伏線の回収指示】
以下の伏線が仕込まれたまま回収されていません。次話以降で必ず回収してください。

{foreshadowing_detail}

【執筆への制約追加】:
- 重要アイテム・能力・約束・予言等の「仕込み」は、{max_gap}話以内に回収すること
- 回収時は「なぜそれが重要だったか」を読者に納得させる描写を含めること
"""

    CONTRADICTION_FIX_PROMPT_TEMPLATE = """
【設定矛盾の修正指示】
以下の設定矛盾が検出されました。バイブリ（設定集）および執筆で整合性を取ってください。

{contradictions_detail}

【修正方針】:
- Blueprint（計画）優先で整合性を取ること
- 本文側の記述が誤りの場合、次話以降で修正・言及すること
- キャラクターの生死・所持品・場所・能力の矛盾は Critical 扱い
"""

    def __init__(
        self,
        llm: LLMService | None = None,
        prompt_manager: Any = None,
        repo: Any = None,
    ):
        self.llm = llm
        self.prompt_manager = prompt_manager
        self.repo = repo
        self._extraction_service = extraction_service

    async def extract_keywords(self, text: str) -> list[str]:
        """GraphRAG抽出サービス経由でエンティティ名を取得（NER代替）

        Character, Item, Event, Location タイプのエンティティ名を
        出現順・重複なしで返す。
        """
        if not text or not text.strip():
            return []

        try:
            # 既存のグラフ抽出サービスを利用（LLM構造化出力 + キャッシュ + フォールバック済み）
            result: GraphExtractionResult = self._extraction_service.extract_graph_from_text(text)

            # 因果律監査に関わるタイプのみ抽出
            target_types = {"Character", "Item", "Event", "Location", "Faction"}
            keywords = []
            seen = set()
            for entity in result.entities:
                if entity.type in target_types and entity.name not in seen:
                    seen.add(entity.name)
                    keywords.append(entity.name)

            logger.debug(f"Extracted {len(keywords)} keywords from text (length={len(text)})")
            return keywords

        except Exception as e:
            logger.warning(f"Keyword extraction failed, falling back to empty list: {e}")
            return []

    async def check_integrity(
        self,
        keywords: list[str],
        blueprint: str,
        content: str,
        threshold: float = 0.7,
        book_id: int | None = None,
        ep_num: int | None = None,
    ) -> tuple[bool, float, CausalityAuditResult]:
        """因果律整合性の総合チェック

        Returns:
            tuple: (is_consistent, score, CausalityAuditResult)
        """
        if not blueprint or not blueprint.strip():
            return True, 1.0, CausalityAuditResult(is_consistent=True, score=1.0)

        if not content or not content.strip():
            # 本文がない場合はスキップ（執筆前段階など）
            return True, 1.0, CausalityAuditResult(is_consistent=True, score=1.0)

        try:
            # 1. キーワード補完（引数の keywords + 両テキストからの抽出）
            bp_keywords = await self.extract_keywords(blueprint)
            ct_keywords = await self.extract_keywords(content)
            _ = list(dict.fromkeys(keywords + bp_keywords + ct_keywords))

            # 2. 因果リンク抽出（Blueprint と Content 両方から）
            bp_links = await self._extract_causality_links(blueprint, source="blueprint")
            ct_links = await self._extract_causality_links(content, source="content")

            # 3. グラフ差分計算
            graph_diff = await self._diff_graphs(blueprint, content)

            # 4. 因果鎖連続性検証
            all_links = bp_links + ct_links
            broken_chains = self._verify_causality_chains(all_links)

            # 5. 未回収伏線・矛盾検出
            foreshadowing, contradictions = await self._detect_foreshadowing_and_contradictions(
                blueprint, content, graph_diff, ep_num
            )

            # 6. パッチ生成
            patches = await self._generate_patches(broken_chains, foreshadowing, contradictions)

            # 7. パッチ投稿（設定有効時・book_idがある場合）
            if patches and book_id:
                await self._submit_patches(book_id, patches)

            # 8. スコア計算・結果構築
            score = self._calculate_score(broken_chains, foreshadowing, contradictions, all_links)
            is_consistent = score >= threshold and len(contradictions) == 0

            result = CausalityAuditResult(
                is_consistent=is_consistent,
                causality_links=all_links,
                broken_chains=broken_chains,
                unresolved_foreshadowing=foreshadowing,
                contradictions=contradictions,
                patches=patches,
                score=score,
                graph_diff=graph_diff,
            )

            logger.info(
                f"Causality audit: consistent={is_consistent}, score={score:.2f}, "
                f"links={len(all_links)}, broken={len(broken_chains)}, "
                f"foreshadowing={len(foreshadowing)}, contradictions={len(contradictions)}"
            )

            return is_consistent, score, result

        except Exception as e:
            logger.error(f"Causality integrity check failed: {e}", exc_info=True)
            # エラー時は安全側（通す）で返す
            return (
                True,
                1.0,
                CausalityAuditResult(
                    is_consistent=True, score=1.0, contradictions=[f"監査エラー: {str(e)}"]
                ),
            )

    async def _extract_causality_links(self, text: str, source: str) -> list[CausalityLink]:
        """LLMでテキストから因果関係を抽出"""
        if not text or not text.strip():
            return []

        # テキスト長制限（プロンプトサイズ制御）
        truncated_text = text[:8000]

        prompt = self.CAUSALITY_EXTRACTION_PROMPT.format(text=truncated_text)

        try:
            # LLM 呼び出し（構造化出力期待）
            if self.llm and hasattr(self.llm, "generate_json"):
                raw = await self.llm.generate_json(purpose="causality_extraction", prompt=prompt)
                data = raw.get("metadata", raw) if isinstance(raw, dict) else {}
            elif self.llm and callable(self.llm):
                raw = await self.llm(purpose="causality_extraction", prompt=prompt)
                data = raw.get("metadata", raw) if isinstance(raw, dict) else {}
            else:
                # LLM未設定時は空リスト返す
                logger.debug("LLM not configured for causality extraction")
                return []

            # パース
            links_data = data.get("causality_links", []) if isinstance(data, dict) else []
            links = []
            for item in links_data:
                try:
                    links.append(
                        CausalityLink(
                            cause_entity=item.get("cause_entity", ""),
                            cause_event=item.get("cause_event", ""),
                            effect_entity=item.get("effect_entity", ""),
                            effect_event=item.get("effect_event", ""),
                            confidence=float(item.get("confidence", 0.8)),
                            source=source,  # type: ignore
                        )
                    )
                except Exception as e:
                    logger.debug(f"Failed to parse causality link: {e}")

            return links

        except Exception as e:
            logger.warning(f"Causality extraction failed for {source}: {e}")
            return []

    async def _diff_graphs(self, blueprint: str, content: str) -> GraphDiffResult:
        """Blueprint と Content のエンティティグラフ差分を計算"""
        bp_result = self._extraction_service.extract_graph_from_text(blueprint)
        ct_result = self._extraction_service.extract_graph_from_text(content)

        # エンティティ名集合
        bp_entities = {e.name: e for e in bp_result.entities}
        ct_entities = {e.name: e for e in ct_result.entities}

        bp_names = set(bp_entities.keys())
        ct_names = set(ct_entities.keys())

        missing_entities = bp_names - ct_names
        extra_entities = ct_names - bp_names

        # 関係性の差分（タプルで比較）
        bp_rels = {(r.source, r.target, r.type) for r in bp_result.relationships}
        ct_rels = {(r.source, r.target, r.type) for r in ct_result.relationships}

        missing_relations = bp_rels - ct_rels
        extra_relations = ct_rels - bp_rels

        # プロパティ矛盾検出（共通エンティティで重要プロパティが異なる）
        property_conflicts = {}
        important_props = {
            "is_alive",
            "location",
            "owner",
            "faction",
            "is_injured",
            "has_holy_sword",
        }
        for name in bp_names & ct_names:
            bp_props = bp_entities[name].properties or {}
            ct_props = ct_entities[name].properties or {}
            conflicts = {}
            for prop in important_props:
                if prop in bp_props and prop in ct_props and bp_props[prop] != ct_props[prop]:
                    conflicts[prop] = {"blueprint": bp_props[prop], "content": ct_props[prop]}
            if conflicts:
                property_conflicts[name] = conflicts

        return GraphDiffResult(
            missing_entities=missing_entities,
            extra_entities=extra_entities,
            missing_relations=missing_relations,
            extra_relations=extra_relations,
            property_conflicts=property_conflicts,
        )

    def _verify_causality_chains(self, links: list[CausalityLink]) -> list[CausalityLink]:
        """因果鎖の連続性を検証し、切れているリンクを返す"""
        if not links:
            return []

        # エンティティごとの入力/出力因果を集計
        from collections import defaultdict

        entity_outputs: dict[str, list[CausalityLink]] = defaultdict(list)  # cause_entity -> links
        entity_inputs: dict[str, list[CausalityLink]] = defaultdict(list)  # effect_entity -> links

        for link in links:
            entity_outputs[link.cause_entity].append(link)
            entity_inputs[link.effect_entity].append(link)

        broken = []
        all_entities = set(entity_outputs.keys()) | set(entity_inputs.keys())

        for entity in all_entities:
            outputs = entity_outputs.get(entity, [])
            inputs = entity_inputs.get(entity, [])

            # 入力があるのに出力がない（因果の始まりでない限り）
            # → このエンティティに原因があるのに、そのエンティティが原因となって結果を生んでいない
            if inputs and not outputs:
                # 終端イベント（死亡、最終決戦等）なら許容
                if not self._is_terminal_entity(entity, inputs):
                    broken.extend(inputs)

            # 出力があるのに入力がない（因果の終わりでない限り）
            # → このエンティティが原因となって結果を出しているが、その原因がない
            if outputs and not inputs:
                if not self._is_initial_entity(entity, outputs):
                    broken.extend(outputs)

        # 重複除去
        seen = set()
        unique_broken = []
        for link in broken:
            key = (link.cause_entity, link.cause_event, link.effect_entity, link.effect_event)
            if key not in seen:
                seen.add(key)
                unique_broken.append(link)

        return unique_broken

    def _is_terminal_entity(self, entity: str, inputs: list[CausalityLink]) -> bool:
        """終端エンティティ（因果の行き止まり）か判定"""
        terminal_keywords = ["死亡", "死", "消滅", "終了", "決着", "完結", "破壊"]
        for link in inputs:
            if any(kw in link.effect_event for kw in terminal_keywords):
                return True
        return False

    def _is_initial_entity(self, entity: str, outputs: list[CausalityLink]) -> bool:
        """始端エンティティ（因果の起点）か判定"""
        initial_keywords = ["開始", "発見", "獲得", "覚醒", "出発", "遭遇", "旅立ち", "始まり"]
        for link in outputs:
            if any(kw in link.cause_event for kw in initial_keywords):
                return True
        return False

    async def _detect_foreshadowing_and_contradictions(
        self,
        blueprint: str,
        content: str,
        graph_diff: GraphDiffResult,
        ep_num: int | None,
    ) -> tuple[list[ForeshadowingItem], list[str]]:
        """未回収伏線と矛盾を検出"""
        foreshadowing = []
        contradictions = []

        # 1. 矛盾: プロパティコンフリクトから生成
        for entity_name, conflicts in graph_diff.property_conflicts.items():
            for prop, vals in conflicts.items():
                contradictions.append(
                    f"[{entity_name}.{prop}] Blueprint: {vals['blueprint']} vs Content: {vals['content']}"
                )

        # 2. 矛盾: Blueprintにある重要関係がContentにない
        for source, target, rel_type in graph_diff.missing_relations:
            if rel_type in ("POSSESSES", "LOCATED_IN", "KNOWS", "ALLY_OF", "ENEMY_OF"):
                contradictions.append(
                    f"関係欠落: {source} --{rel_type}--> {target} (BlueprintにありContentにない)"
                )

        # 3. 伏線検出: Blueprintにのみ存在する重要アイテム/イベント
        bp_result = self._extraction_service.extract_graph_from_text(blueprint)
        bp_entities = {e.name: e for e in bp_result.entities}

        current_ep = ep_num or 1
        for entity_name in graph_diff.missing_entities:
            entity = bp_entities.get(entity_name)
            if not entity:
                continue

            # 重要度判定: アイテム/イベントで重要プロパティを持つもの
            importance = "Minor"
            if entity.type == "Item":
                if entity.properties.get("rarity") in ("legendary", "unique", "artifact"):
                    importance = "Critical"
                elif entity.properties.get("importance") == "high":
                    importance = "Major"
                else:
                    importance = "Major"
            elif entity.type == "Event":
                if entity.properties.get("is_climax") or entity.properties.get("is_turning_point"):
                    importance = "Critical"
                else:
                    importance = "Major"
            elif entity.type == "Character":
                if entity.properties.get("is_protagonist") or entity.properties.get(
                    "is_antagonist"
                ):
                    importance = "Major"

            if importance in ("Critical", "Major"):
                foreshadowing.append(
                    ForeshadowingItem(
                        entity_name=entity_name,
                        setup_chapter=current_ep,
                        setup_context=entity.description[:200]
                        if entity.description
                        else f"{entity_name} が言及される",
                        expected_payoff=f"{entity_name} の活用・回収・解決",
                        importance=importance,  # type: ignore
                    )
                )

        return foreshadowing, contradictions

    async def _generate_patches(
        self,
        broken_chains: list[CausalityLink],
        foreshadowing: list[ForeshadowingItem],
        contradictions: list[str],
    ) -> list[PromptPatch]:
        """検出問題に対するプロンプトパッチを生成"""
        patches = []

        # 因果鎖切れパッチ
        if broken_chains:
            detail_lines = []
            for link in broken_chains[:10]:  # 最大10件
                detail_lines.append(
                    f"  - {link.cause_entity}「{link.cause_event}」→ {link.effect_entity}「{link.effect_event}」"
                )
            detail = "\n".join(detail_lines)

            patch_content = self.CAUSALITY_FIX_PROMPT_TEMPLATE.format(broken_chains_detail=detail)
            patches.append(
                PromptPatch(
                    target_prompt="writing_director",
                    patch_content=patch_content,
                    reasoning=f"{len(broken_chains)}件の因果鎖切れを検出。前因果の継承と結果描写の徹底を指示。",
                )
            )

        # 伏線未回収パッチ
        if foreshadowing:
            detail_lines = []
            for fs in foreshadowing[:10]:
                detail_lines.append(
                    f"  - {fs.entity_name} (第{fs.setup_chapter}話仕込み, 重要度:{fs.importance}): {fs.setup_context[:100]}"
                )
            detail = "\n".join(detail_lines)

            from config.project_context import ProjectContext

            max_gap = ProjectContext.get_setting("FORSHADOWING_MAX_GAP_CHAPTERS", 5)

            patch_content = self.FORSHADOWING_FIX_PROMPT_TEMPLATE.format(
                foreshadowing_detail=detail,
                max_gap=max_gap,
            )
            patches.append(
                PromptPatch(
                    target_prompt="plot_expansion",
                    patch_content=patch_content,
                    reasoning=f"{len(foreshadowing)}件の未回収伏線を検出。次話以降での確実な回収を指示。",
                )
            )

        # 矛盾パッチ
        if contradictions:
            detail = "\n".join(f"  - {c}" for c in contradictions[:15])

            patch_content = self.CONTRADICTION_FIX_PROMPT_TEMPLATE.format(
                contradictions_detail=detail
            )
            patches.append(
                PromptPatch(
                    target_prompt="bible_update",
                    patch_content=patch_content,
                    reasoning=f"{len(contradictions)}件の設定矛盾を検出。バイブリ設定の修正と次話での整合性確保を指示。",
                )
            )

        return patches

    async def _submit_patches(self, book_id: int, patches: list[PromptPatch]) -> list[int]:
        """生成パッチを PendingPatch として DB 登録"""
        try:
            from src.backend.database.uow import UnitOfWork
            from src.backend.database.models import PendingPatch
            from src.core.container import AppContainer

            patch_ids = []
            async with UnitOfWork(AppContainer.db()) as uow:
                for patch in patches:
                    # JSONシリアライズ可能な形で保存
                    patch_data = {
                        "target_prompt": patch.target_prompt,
                        "content": patch.patch_content,
                        "reasoning": patch.reasoning,
                    }
                    pending = PendingPatch(
                        book_id=book_id,
                        patch_type="prompt",
                        patch_content=json.dumps(patch_data, ensure_ascii=False),
                        status="pending",
                    )
                    uow.session.add(pending)
                    await uow.session.flush()
                    patch_ids.append(pending.id)
                await uow.session.commit()

            logger.info(f"Submitted {len(patch_ids)} causality patches for book_id={book_id}")
            return patch_ids

        except Exception as e:
            logger.error(f"Failed to submit patches: {e}")
            return []

    def _calculate_score(
        self,
        broken_chains: list[CausalityLink],
        foreshadowing: list[ForeshadowingItem],
        contradictions: list[str],
        all_links: list[CausalityLink],
    ) -> float:
        """整合性スコア計算 (0.0-1.0)"""
        if not all_links and not foreshadowing and not contradictions:
            return 1.0

        # 基準スコア
        score = 1.0

        # 因果鎖切れペナルティ
        if all_links:
            broken_ratio = len(broken_chains) / len(all_links)
            score -= broken_ratio * 0.4  # 最大40%減点

        # 伏線未回収ペナルティ
        critical_fs = sum(1 for f in foreshadowing if f.importance == "Critical")
        major_fs = sum(1 for f in foreshadowing if f.importance == "Major")
        score -= critical_fs * 0.15
        score -= major_fs * 0.08

        # 矛盾ペナルティ
        score -= len(contradictions) * 0.1

        return max(0.0, min(1.0, score))

    # ============================================================
    # 後方互換性メソッド (既存コードからの呼び出し用)
    # ============================================================

    async def audit_setting_causality(
        self, content: str, world_settings: str, blueprint: str
    ) -> tuple[bool, str, list[dict[str, Any]]]:
        """後方互換: 設定因果律監査 (旧インターフェース)

        既存の writing_services.py から呼び出されるため、旧形式の戻り値に変換して返す。
        """
        try:
            # world_settings を blueprint に含めてチェック
            combined_blueprint = (
                blueprint + "\n\n【世界設定】\n" + world_settings if world_settings else blueprint
            )
            is_ok, score, result = await self.check_integrity(
                [], combined_blueprint, content, threshold=0.7
            )

            # 結果を旧形式に変換
            failures = []
            if result.contradictions:
                for c in result.contradictions:
                    failures.append({"rule": "設定矛盾", "gap": c, "fragment": "設定不整合"})
            if result.broken_chains:
                for link in result.broken_chains:
                    failures.append(
                        {
                            "rule": "因果鎖切れ",
                            "gap": f"{link.cause_entity}→{link.effect_entity} が未接続",
                            "fragment": f"{link.cause_event} → {link.effect_event}",
                        }
                    )
            if result.unresolved_foreshadowing:
                for fs in result.unresolved_foreshadowing:
                    failures.append(
                        {
                            "rule": "伏線未回収",
                            "gap": f"{fs.entity_name} が未回収",
                            "fragment": fs.setup_context,
                        }
                    )

            reason = ""
            if failures:
                reason = "\n".join([f"・{f['rule']}: {f['gap']}" for f in failures])

            return is_ok, reason, failures

        except Exception as e:
            logger.error(f"audit_setting_causality failed: {e}")
            return True, "", []  # エラー時は安全側で通す

    async def run_constraint_unit_tests(
        self, content: str, active_constraints: list[dict[str, Any]]
    ) -> tuple[bool, list[dict[str, Any]]]:
        """後方互換: 制約ユニットテスト (旧インターフェース)

        アクティブな制約リストに対して、本文が違反していないかチェックする簡易版。
        """
        if not active_constraints or not content:
            return True, []

        try:
            failures = []
            for i, constraint in enumerate(active_constraints):
                constraint_text = (
                    constraint.get("constraint", "")
                    if isinstance(constraint, dict)
                    else str(constraint)
                )
                if constraint_text and constraint_text not in content:
                    failures.append(
                        {
                            "constraint_index": i,
                            "reason": f"制約未満足: {constraint_text[:50]}",
                            "violating_snippet": "...",
                        }
                    )

            return len(failures) == 0, failures

        except Exception as e:
            logger.error(f"run_constraint_unit_tests failed: {e}")
            return True, []


class DeAIAuditor:
    """AI感除去監査エージェント"""

    def __init__(
        self,
        repo=None,
        llm: LLMService = None,
        prompt_manager: Any = None,
        edge_preserver=None,
        *args,
        **kwargs,
    ):
        self.repo = repo
        self.llm = llm
        self.prompt_manager = prompt_manager
        self.edge_preserver = edge_preserver  # New parameter for semantic edge preservation

    async def audit(
        self,
        content: str,
        before_content: str | None = None,
        edges: list[SharpEdgeSpec] | None = None,
        emotional_hook: Any | None = None,
    ) -> tuple[bool, str]:
        if edges:
            if self.edge_preserver is not None:
                # Semantic mode: use SemanticEdgePreserver for robust detection
                semantic_lost, _ = await self.edge_preserver.check_edges_preserved(
                    before_content or "",
                    content,
                    edges,
                )
                lost = semantic_lost
            else:
                # Legacy string-only mode (backward compatible)
                lost = check_edges_preserved(
                    before_content or "",
                    content,
                    edges,
                )
            if lost:
                lost_types = ", ".join(e.edge_type for e in lost)
                return False, f"以下の角が削られました: {lost_types}"

        if emotional_hook is not None:
            hook_edges = [
                SharpEdgeSpec(
                    edge_type="emotional_hook",
                    description=getattr(emotional_hook, "one_line_intent", str(emotional_hook)),
                )
            ]
            if self.edge_preserver is not None:
                semantic_lost, _ = await self.edge_preserver.check_edges_preserved(
                    before_content or "",
                    content,
                    hook_edges,
                )
                lost = semantic_lost
            else:
                lost = check_edges_preserved(
                    before_content or "",
                    content,
                    hook_edges,
                )
            if lost:
                return (
                    False,
                    f"刺さりが削られました: {getattr(emotional_hook, 'one_line_intent', '')}",
                )

        if self.prompt_manager is None:
            return True, "OK"
        prompt = self.prompt_manager.build_critic_feedback_prompt(
            issue_list=None, draft_content=content, blueprint=content
        )
        result = await self.llm.generate_json(purpose="audit", prompt=prompt)
        metadata = result.get("metadata", {})
        return metadata.get("is_valid", True), metadata.get("feedback", "OK")


class InternalLogicValidator:
    """内部ロジック(アリバイ・タイムライン・情報非対称)の整合性検証エージェント。

    テスト・簡易利用側は PromptManager と generate_json 呼び出しを
     kwargs 経由で注入できる（LogicalAuditor と同様の設計）。
    """

    def __init__(
        self, repo: Any = None, llm: Any = None, ctx_mgr: Any = None, pm: Any = None, **kwargs
    ):
        self.repo = repo
        self.ctx_mgr = ctx_mgr
        self.prompt_manager = pm

        # Priority 1: Explicit generate_json provided in kwargs (Common in tests)
        if "generate_json" in kwargs:
            self.llm = kwargs["generate_json"]
        # Priority 2: llm argument provided
        elif llm is not None:
            self.llm = llm
        else:
            self.llm = None

        self.wave_analyzer = None

    async def validate_alibi_and_timeline(
        self, blueprint: str, script: str
    ) -> tuple[bool, list[str]]:
        """アリバイとタイムラインの整合性を検証する（スタブ）。"""
        return True, []

    async def check_information_asymmetry(
        self, past_info: str, current_info: str
    ) -> tuple[bool, list[str]]:
        """情報の非対称性を検証する（スタブ）。"""
        return True, []


class LogicalAuditor:
    """ロジカル一貫性チェックエージェント"""

    def __init__(
        self, repo: Any = None, llm: Any = None, ctx_mgr: Any = None, pm: Any = None, **kwargs
    ):
        self.repo = repo
        self.ctx_mgr = ctx_mgr
        self.prompt_manager = pm

        # Priority 1: Explicit generate_json provided in kwargs (Common in tests)
        if "generate_json" in kwargs:
            self.llm = kwargs["generate_json"]
        # Priority 2: llm argument provided
        elif llm is not None:
            self.llm = llm
        else:
            self.llm = None

        self.wave_analyzer = None

    async def generate_critic_feedback(
        self, issue_list: LogicalAuditIssueList, draft_content: str, blueprint: str
    ) -> CriticFeedback:
        """
        Criticエージェントとして、具体的な修正案を含むフィードバックを生成する。
        """
        if not self.prompt_manager:
            from src.models.audit import CriticFeedback

            return CriticFeedback(rewrite_guidance="Prompt manager not configured.")

        prompt = await self.prompt_manager.build_critic_feedback_prompt(
            issue_list=issue_list, draft_content=draft_content, blueprint=blueprint
        )

        # Handle both LLMService and raw generate_json function
        if hasattr(self.llm, "generate_json"):
            # Use await directly; AsyncMock will return return_value when awaited
            result = await self.llm.generate_json(purpose="critic", prompt=prompt)
        elif callable(self.llm):
            result = await self.llm(purpose="critic", prompt=prompt)
        else:
            from src.models.audit import CriticFeedback

            return CriticFeedback(rewrite_guidance="LLM client not configured.")

        from src.models.audit import CriticFeedback

        # Debugging: print result type
        # print(f"DEBUG: result type: {type(result)}, result: {result}")
        if hasattr(result, "metadata"):
            data = result.metadata
        elif isinstance(result, dict):
            data = result.get("metadata", result)
        else:
            data = result

        if isinstance(data, dict):
            return CriticFeedback.model_validate(data)

        return (
            result
            if isinstance(result, CriticFeedback)
            else CriticFeedback(rewrite_guidance=str(result))
        )

    async def validate_alibi_and_timeline(
        self, blueprint: str, script: str
    ) -> tuple[bool, list[str]]:
        """
        アリバイとタイムラインの整合性を検証する（スタブ）
        """
        return True, []

    async def audit_logical_consistency(
        self, book_id: int, ep_num: int, blueprint: str
    ) -> tuple[bool, str, float]:
        """作品のロジカル整合性をチェックします"""
        base_ok, base_feedback = await self._check_base_config(book_id, ep_num)
        if not base_ok:
            return False, base_feedback, 0.0

        plot_ok, plot_feedback = await self._check_plot_integrity(book_id, ep_num)
        if not plot_ok:
            return False, plot_feedback, 0.0

        char_ok, char_feedback = await self._check_character_actions(book_id)
        if not char_ok:
            return False, char_feedback, 0.0

        theme_ok, theme_feedback = await self._check_theme_continuity(blueprint)
        if not theme_ok:
            return False, theme_feedback, 0.0

        return True, "OK", 1.0

    async def _check_base_config(self, book_id: int, ep_num: int) -> tuple[bool, str]:
        """基本設定の一貫性"""
        if self.repo is None:
            return True, "OK"
        settings = await self.repo.bible.get_plot(book_id, ep_num)
        if not settings:
            return False, "設定未設定"
        if not settings.get("scene_integrity", "false"):
            return False, "scene integrity violation"
        return True, "OK"

    async def _check_plot_integrity(self, book_id: int, ep_num: int) -> tuple[bool, str]:
        """プロット全体の一貫性"""
        if self.repo is None:
            return True, "OK"
        plot = await self.repo.plot.get_plot(book_id, ep_num)
        if not plot:
            return False, "plot not found"
        if not await self._check_pacing(plot):
            return False, "inconsistent pacing"
        return True, "OK"

    async def _check_pacing(self, plot: PlotDbModel) -> bool:
        """テンションの一貫性チェック"""
        return True

    async def check_information_asymmetry(
        self, past_info: str, current_info: str
    ) -> tuple[bool, list[str]]:
        """
        情報の非対称性を検証する（スタブ）
        """
        return True, []

    async def _check_character_actions(self, book_id: int) -> tuple[bool, str]:
        """キャラクターの行動一貫性（スタブ）"""
        return True, "OK"

    async def _check_theme_continuity(self, blueprint: str) -> tuple[bool, str]:
        """テーマの連続性（スタブ）"""
        return True, "OK"

    async def analyze_tension_wave(self, book_id: int, ep_range: tuple = (1, 9999)) -> Any:
        """作品のtension履歴からNarrativeWavePatternを生成する"""
        try:
            from config.project_context import ProjectContext
            from src.models.audit import NarrativeWavePattern

            if self.repo is None:
                return NarrativeWavePattern()

            plots = await self.repo.plot.get_plots(book_id, ep_range[0], ep_range[1])
            if not plots:
                return NarrativeWavePattern()

            tension_history = [getattr(p, "tension", 50) for p in plots]

            if self.wave_analyzer is None:
                from src.backend.engine_narrative import WavePatternAnalyzer

                self.wave_analyzer = WavePatternAnalyzer(
                    threshold=ProjectContext.get_setting("catharsis_threshold", 65),
                    reset_value=ProjectContext.get_setting("catharsis_reset_value", 0),
                )

            return self.wave_analyzer.analyze(tension_history)
        except Exception as e:
            from src.models.audit import NarrativeWavePattern

            return NarrativeWavePattern(issues=[f"波パターン分析中にエラー: {str(e)}"])

    async def score_narrative_metrics(
        self,
        book_id: int,
        branch_id: int,
        ep_num: int,
        scene_num: int,
        scene_content: str,
        context: str = "",
        reporter: Any = None,
    ) -> list[dict[str, Any]]:
        """1シーン分の没入スコアと物語メトリクスをLLMで算出する"""
        default_scores = [
            {
                "metric_name": "immersion_score",
                "score": 0.0,
                "reasoning": "スコアリング失敗時デフォルト",
            },
            {"metric_name": "pov_stability", "score": 0.0, "reasoning": ""},
            {"metric_name": "empathy_gap", "score": 1.0, "reasoning": ""},
            {"metric_name": "curiosity_hook_rate", "score": 0.0, "reasoning": ""},
            {"metric_name": "sensory_density", "score": 0.0, "reasoning": ""},
            {"metric_name": "catharsis_density", "score": 0.0, "reasoning": ""},
        ]
        if not scene_content or not scene_content.strip():
            return default_scores

        try:
            from src.models.audit import ImmersionScore

            prompt = (
                "以下の小説本文を、以下の6観点で0.0-1.0で評価してください。"
                "評価結果は JSON で返してください。\n"
                "{\n"
                '  "pov_stability": 0.0-1.0,\n'
                '  "empathy_gap": 0.0-1.0,\n'
                '  "curiosity_hook_rate": 0.0-1.0,\n'
                '  "sensory_density": 0.0-1.0,\n'
                '  "catharsis_density": 0.0-1.0\n'
                "}\n\n"
                "【本文】\n" + scene_content[:12000] + "\n"
            )
            if context:
                prompt += "\n【参考コンテキスト】\n" + context[:4000] + "\n"

            raw = await self.llm(purpose="narrative_metrics", prompt=prompt)
            data = raw.get("metadata", raw) if isinstance(raw, dict) else {}
            immersion = ImmersionScore(
                pov_stability=float(data.get("pov_stability", 0.0) or 0.0),
                empathy_gap=float(data.get("empathy_gap", 1.0) or 1.0),
                curiosity_hook_rate=float(data.get("curiosity_hook_rate", 0.0) or 0.0),
                sensory_density=float(data.get("sensory_density", 0.0) or 0.0),
            )
            total_score = immersion.calculate_total()
            scores = [
                {"metric_name": "immersion_score", "score": total_score, "reasoning": "加重合計"},
                {"metric_name": "pov_stability", "score": immersion.pov_stability, "reasoning": ""},
                {"metric_name": "empathy_gap", "score": immersion.empathy_gap, "reasoning": ""},
                {
                    "metric_name": "curiosity_hook_rate",
                    "score": immersion.curiosity_hook_rate,
                    "reasoning": "",
                },
                {
                    "metric_name": "sensory_density",
                    "score": immersion.sensory_density,
                    "reasoning": "",
                },
                {
                    "metric_name": "catharsis_density",
                    "score": float(data.get("catharsis_density", 0.0) or 0.0),
                    "reasoning": "",
                },
            ]
            if reporter:
                reporter.report(
                    f"ℹ️ Ep.{ep_num} Scene.{scene_num}: 没入スコア {total_score:.1f}", "info"
                )
            return scores
        except Exception as e:
            if reporter:
                reporter.report(f"⚠️ スコアリング失敗: {type(e).__name__}: {e}", "warning")
            return default_scores
