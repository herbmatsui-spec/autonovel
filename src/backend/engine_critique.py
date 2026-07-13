import json
from typing import Any, Dict

from config import MODEL_PLANNING
from src.backend.sharp_edge_preserver import check_edges_preserved, SemanticEdgePreserver
from src.models import GenerateResult


class CritiqueAgent:
    """生成された作品を分析し、エンジンの改善案を提案する専用エージェント"""
    def __init__(self, repo, pm, generate_json, edge_preserver=None):
        self.repo = repo
        self.pm = pm
        self.generate_json = generate_json
        # Semantic edge preserver (None → legacy string-only check_edges_preserved)
        self.edge_preserver = edge_preserver or SemanticEdgePreserver(
            semantic_cache=None, use_semantic=False
        )

    async def analyze_work_quality(self, book_id: int) -> str:
        book = await self.repo.get_book(book_id)
        chapters = await self.repo.get_all_non_anchor_chapters(book_id)
        plots = await self.repo.get_all_plots(book_id)

        # 分析用コンテキストの構築
        summary_data = []
        for c in chapters:
            p = next((p for p in plots if p.ep_num == c.ep_num), None)
            summary_data.append({
                "ep": c.ep_num,
                "plot_goal": p.detailed_blueprint if p else "",
                "actual_summary": c.summary,
                "word_count": len(c.content or "")
            })

        prompt = await self.pm.build_critique_quality_prompt(book.title, json.dumps(summary_data, ensure_ascii=False, indent=2), book_id=book_id)
        res = await self.generate_json(
            MODEL_PLANNING,
            prompt,
            temp=0.3
        )
        return res.story_content

    async def run_iterative_gap_analysis(self, book_id: int, max_iterations: int = 10) -> GenerateResult:
        """全エピソードの『設計図 vs 本文』を一括で分析し、エンジンの最適化レポートを生成する（APIコールを1回に集約）"""
        book = await self.repo.get_book(book_id)
        chapters = await self.repo.get_all_non_anchor_chapters(book_id)
        plots = await self.repo.get_all_plots(book_id)

        if not chapters:
            return GenerateResult(success=False, error_message="分析対象のチャプターが存在しません。")

        # 分析対象を最大10エピソードに制限
        target_chapters = chapters[:max_iterations]

        # 一括分析用のバッチコンテキストを構築
        batch_data = []
        edge_loss_reports = []
        for ch in target_chapters:
            plot = next((p for p in plots if p.ep_num == ch.ep_num), None)
            if not plot:
                continue

            edges = getattr(plot, 'sharp_edges', [])
            if edges:
                if self.edge_preserver is not None:
                    semantic_lost, _string_lost = await self.edge_preserver.check_edges_preserved(
                        plot.detailed_blueprint or "", ch.content or "", edges
                    )
                    lost = semantic_lost
                else:
                    lost = check_edges_preserved(plot.detailed_blueprint or "", ch.content or "", edges)
                if lost:
                    lost_types = ", ".join(e.edge_type for e in lost)
                    edge_loss_reports.append(f"第{ch.ep_num}話: 尖りが削られました ({lost_types})")

            batch_data.append(
                f"--- 第{ch.ep_num}話 分析データ ---\n"
                f"【プロット設計図】: {plot.detailed_blueprint}\n"
                f"【実際の執筆本文(抜粋)】: {ch.content[:1500]}...\n"
            )

        batch_analysis_prompt = await self.pm.build_iterative_gap_analysis_prompt(book.genre, book.title, "\n\n".join(batch_data), book_id=book_id)

        if edge_loss_reports:
            edge_loss_section = "\n\n【⚠️ 尖り保全警告】\n" + "\n".join(edge_loss_reports) + "\n品質磨き上げで角が削られたため、没戻しを推奨します。"
            batch_analysis_prompt = f"{edge_loss_section}\n\n{batch_analysis_prompt}"

        # Self-repair / validation loop (up to 2 retries, meaning max 3 attempts total)
        import logging

        from src.backend.patch_validator import PatchValidator
        logger = logging.getLogger(__name__)

        attempt = 0
        max_attempts = 3
        current_prompt = batch_analysis_prompt
        error_feedback = ""

        while attempt < max_attempts:
            if error_feedback:
                current_prompt = f"【🚨パッチ検証エラー報告🚨】\n前回の出力に以下の不備がありました。修正したJSONを出力してください:\n{error_feedback}\n\n{batch_analysis_prompt}"

            res = await self.generate_json(
                MODEL_PLANNING,
                current_prompt,
                temp=0.3
            )

            if not res.success:
                return res

            meta = res.metadata
            config_patch = meta.get("config_patch") or ""
            prompt_patch = meta.get("prompt_patch") or ""

            # 検証実行
            config_val = PatchValidator.validate_config_patch(str(config_patch))
            prompt_val = PatchValidator.validate_prompt_patch(str(prompt_patch))

            errors = []
            if not config_val.is_safe:
                errors.extend([f"[Config Error] {e}" for e in config_val.errors])
            if not prompt_val.is_safe:
                errors.extend([f"[Prompt Error] {e}" for e in prompt_val.errors])

            if not errors:
                # バリデーション成功
                logger.info("✅ Critique gap analysis output successfully validated.")
                # PendingPatch に保存
                # config_patchとprompt_patchの両方をpending_patchesテーブルに保存する
                # patch_type は 'config' または 'prompt'
                # ab_test_result にスコア等を格納
                scores = meta.get("scores") or {}
                if isinstance(config_patch, dict):
                    config_patch_str = json.dumps(config_patch, ensure_ascii=False)
                else:
                    config_patch_str = str(config_patch)

                # Configパッチを保存
                if config_patch_str.strip():
                    await self.repo.save_pending_patch(
                        book_id=book_id,
                        patch_type="config",
                        patch_content=config_patch_str,
                        ab_test_result={"scores": scores, "habits": meta.get("habits"), "style_gap": meta.get("style_gap")}
                    )

                # Promptパッチを保存
                if prompt_patch and str(prompt_patch).strip():
                    # PendingPatchとして登録
                    patch_id = await self.repo.save_pending_patch(
                        book_id=book_id,
                        patch_type="prompt",
                        patch_content=str(prompt_patch),
                        ab_test_result={"scores": scores, "habits": meta.get("habits"), "style_gap": meta.get("style_gap")}
                    )

                    # さらに、プロンプトバージョン履歴にも自動保存する
                    try:
                        from src.backend.prompt_version_manager import PromptVersionManager
                        # ファサード経由ではなく直接Managerを呼び出し
                        pvm = PromptVersionManager(self.repo.db)
                        # 平均スコアの算出
                        avg_score = None
                        if scores:
                            vals = [float(v) for v in scores.values() if isinstance(v, (int, float))]
                            if vals:
                                avg_score = sum(vals) / len(vals)

                        await pvm.save_new_version(
                            book_id=book_id,
                            prompt_key="optimized_prompt_patch",
                            content=str(prompt_patch),
                            score_before=avg_score,
                            ab_test_metrics={"scores": scores, "pending_patch_id": patch_id}
                        )
                        logger.info("Saved new prompt patch version to history.")
                    except Exception as e:
                        logger.error(f"Failed to auto-save prompt version: {e}")

                await self.repo.save_optimization_report(book_id, res.metadata)
                return res
            else:
                error_feedback = "\n".join(errors)
                logger.warning(f"❌ Patch validation failed on attempt {attempt + 1}: {error_feedback}")
                attempt += 1

        # 全て失敗した場合
        logger.error("❌ Max critique self-repair attempts reached. Saving optimization report anyway without pending patches.")
        await self.repo.save_optimization_report(book_id, res.metadata)
        return GenerateResult(success=False, error_message=f"パッチの自己修復バリデーションに失敗しました: {error_feedback}")


    async def run_dry_run(self, book_id: int, ep_num: int, improved_prompt: str) -> str:
        """提案されたプロンプトを使用して、特定のシーンを再生成して比較する"""
        plot = await self.repo.get_plot(book_id, ep_num)
        if not plot: return "対象話数が見つかりません。"

        # 既存のプロンプト構築に、強制力のある一文を注入
        prompt = await self.pm.build_dry_run_prompt(ep_num, improved_prompt, plot.detailed_blueprint, plot.script_content)
        res = await self.generate_json(
            ProjectContext.get_setting("model_writing"), # ドライランは執筆モデルで実行
            prompt,
            temp=0.7
        )
        return res.story_content

    async def run_dogfeeding_approval_loop(self, content: str, ep_num: int, passion: float, temp: float) -> Dict[str, Any]:
        """
        [Dogfeeding] 執筆された小説本文を自己評価し、合格スコア（80点）を満たしているか判定する。
        """
        prompt = (
            f"以下の第{ep_num}話の執筆原稿を評価してください。\n\n"
            f"【原稿】\n{content}\n\n"
            "読者の期待（カタルシス、面白さ）、キャラ崩れの有無、文章の品質を総合的に評価し、"
            "100点満点で採点してください。また、80点未満の場合は具体的な修正指示（recommended_patch）を出力してください。\n"
            "出力は以下のJSON形式にしてください：\n"
            "{\n"
            "  \"score\": 85,\n"
            "  \"reason\": \"評価理由\",\n"
            "  \"recommended_patch\": \"\"\n"
            "}"
        )
        try:
            res = await self.generate_json(
                ProjectContext.get_setting("model_writing"),
                prompt,
                temp=temp
            )
            if res.success and res.metadata:
                return res.metadata
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error in run_dogfeeding_approval_loop: {e}")
        return {"score": 100, "reason": "Fallback success", "recommended_patch": ""}

