"""
かんたんモード パイプライン
ジャンル選択のみで企画〜完結まで全自動生成
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from config.constants import EP_CLIMAX, EP_FINAL
from src.easy_mode.spice_guard import SpiceElement, create_spice_guard
from src.presets.loader import load_preset

logger = logging.getLogger(__name__)


@dataclass
class EpisodeResult:
    """1話分の生成結果"""

    episode_num: int
    title: str
    content: str
    word_count: int
    audit_score: float
    audit_passed: bool
    rewrite_count: int
    spice_elements: list[SpiceElement]
    metadata: dict[str, Any]
    needs_human_review: bool = False


@dataclass
class SeriesResult:
    """シリーズ全体の生成結果"""

    genre: str
    title: str
    concept: str
    total_episodes: int
    episodes: list[EpisodeResult]
    bible: dict[str, Any]
    plot_outline: list[dict[str, Any]]
    metadata: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "completed"  # "in_progress", "completed", "failed", "paused"


@dataclass
class PipelineConfig:
    """パイプライン設定"""

    genre: str
    target_episodes: int = 8
    max_rewrite_iterations: int = 3
    target_audit_score: float = 95.0
    enable_spice_guard: bool = True
    progress_callback: Callable[[str, int, int], None] | None = None


class EasyModePipeline:
    """かんたんモード 全自動生成パイプライン"""

    # LLM呼び出しリトライ設定
    MAX_LLM_RETRIES = 3
    LLM_RETRY_DELAY = 1.0  # seconds

    def __init__(self, engine, config: PipelineConfig):
        self.engine = engine
        self.config = config
        self.preset = load_preset(config.genre)
        self.series_result: SeriesResult | None = None
        self._cancelled = False

    async def _generate_with_retry(
        self, prompt: str, variables: dict, operation: str = "generate"
    ) -> str:
        """LLM生成をリトライ付きで実行"""
        last_error: Exception = Exception("Unknown error")
        for attempt in range(self.MAX_LLM_RETRIES):
            try:
                if self._cancelled:
                    raise RuntimeError("Cancelled")
                result = await self.engine.llm.generate(prompt, variables)
                if result and result.strip():
                    return result
                last_error = Exception("Empty response from LLM")
            except Exception as e:
                if self._cancelled:
                    raise
                last_error = e
                logger.warning(
                    f"{operation} attempt {attempt + 1}/{self.MAX_LLM_RETRIES} failed: {e}"
                )
                if attempt < self.MAX_LLM_RETRIES - 1:
                    await asyncio.sleep(self.LLM_RETRY_DELAY * (attempt + 1))

        logger.error(f"{operation} failed after {self.MAX_LLM_RETRIES} attempts: {last_error}")
        raise last_error

    async def run(self) -> SeriesResult:
        """パイプライン全体を実行"""
        logger.info(f"Starting easy mode pipeline for genre: {self.config.genre}")

        # グローバルセマフォを通じて並行実行数を制御
        from src.core.async_utils import limit_concurrency

        try:
            # Step 1: Bible生成
            await self._report_progress("bible", 0, self.config.target_episodes)
            bible = await limit_concurrency(self._generate_bible())

            # Step 2: プロット生成
            await self._report_progress("plot", 0, self.config.target_episodes)
            plot_outline = await limit_concurrency(self._generate_plot_outline(bible))

            # Step 3: 各話生成ループ
            episodes: list[EpisodeResult] = []
            for ep_num in range(1, self.config.target_episodes + 1):
                if self._cancelled:
                    logger.info(f"Pipeline cancelled at episode {ep_num}")
                    break

                await self._report_progress("writing", ep_num - 1, self.config.target_episodes)
                episode_result = await limit_concurrency(
                    self._generate_episode(ep_num, plot_outline, bible)
                )
                episodes.append(episode_result)

            await self._report_progress("finalizing", len(episodes), self.config.target_episodes)
            result = self._finalize_result(episodes)

            # 完了処理
            self._cancelled = False
            return result

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            self._cancelled = False
            raise

    async def _generate_bible(self) -> dict[str, Any]:
        """Bible自動生成（プリセット注入）"""
        # プロンプトテンプレートを直接使用（モジュールパス問題回避）
        bible_template = self.preset.get("bible", "")

        # プリセットからデフォルト変数を取得
        preset_vars = self._get_preset_defaults()

        # 変数をマージ
        variables = {
            "world_rules_json": "{}",
            "concept": preset_vars.get("concept", "デフォルトコンセプト"),
            "protagonist_name": preset_vars.get("protagonist_name", "主人公"),
            "betrayal_type": preset_vars.get("betrayal_type", "追放"),
            "catharsis_target": preset_vars.get("catharsis_target", "元パーティ"),
            "cheat_ability": preset_vars.get("cheat_ability", "全スキル習得"),
            "schema_json": "{}",
            "humiliation_ep": "2",
            "trigger_ep": "3",
            "musou_start_ep": "4",
            "final_ep": "8",
            "tension_threshold": "75",
        }
        variables.update(preset_vars)

        # LLMで生成（リトライ付き）
        try:
            bible_text = await self._generate_with_retry(
                bible_template, variables, "bible_generation"
            )
            # パースして辞書化
            bible = self._parse_bible(bible_text)
        except Exception as e:
            if self._cancelled:
                raise
            logger.warning(f"Bible generation failed, using fallback: {e}")
            bible = self._fallback_bible(variables)

        return bible

    async def _generate_plot_outline(self, bible: dict[str, Any]) -> list[dict[str, Any]]:
        """プロット自動生成（テンプレ曲線×テンプレ展開）"""
        tension_curve = self.preset.get("tension", {})
        curve_points = tension_curve.get("curve_points", [])
        catharsis_spikes = tension_curve.get("catharsis_spikes", [0.25, 0.5, 0.75, 1.0])

        # 話数分のプロットを生成
        plots = []
        for ep_num in range(1, self.config.target_episodes + 1):
            progress = ep_num / self.config.target_episodes

            # テンション値を曲線から取得
            target_tension = self._interpolate_tension(progress, curve_points)

            # カタルシス話か判定
            is_catharsis = any(abs(progress - spike) < 0.08 for spike in catharsis_spikes)

            # テンプレート展開パターン選択
            pattern = self._select_plot_pattern(ep_num, is_catharsis)

            plot = {
                "episode": ep_num,
                "title": f"第{ep_num}話 {pattern['title_suffix']}",
                "target_tension": target_tension,
                "is_catharsis": is_catharsis,
                "pattern": pattern["name"],
                "beats": pattern["beats"],
                "hook_point": pattern["hook"],
                "catharsis_type": pattern.get("catharsis_type"),
            }
            plots.append(plot)

        return plots

    async def _generate_episode(
        self,
        ep_num: int,
        bible: dict[str, Any],
        plot_outline: list[dict[str, Any]],
        previous_episodes: list[EpisodeResult],
    ) -> EpisodeResult:
        """1話生成（執筆→監査→リライト）"""
        plot = plot_outline[ep_num - 1]

        # 前話までの要約作成
        prev_context = self._build_prev_context(previous_episodes)

        # 執筆
        content = await self._write_episode(ep_num, bible, plot, prev_context)

        # 監査
        audit_result = await self._audit_episode(content, bible, plot, ep_num)

        # リライト（SpiceGuard付き）
        final_content = content
        rewrite_count = 0
        spice_elements = []

        if self.config.enable_spice_guard:
            spice_elements = self._extract_spice(content)

        for rewrite_iter in range(self.config.max_rewrite_iterations):
            if audit_result["score"] >= self.config.target_audit_score:
                break

            if rewrite_iter >= self.config.max_rewrite_iterations - 1:
                # 最後の試行でもダメなら人間レビューフラグ
                audit_result["needs_human_review"] = True
                break

            # 改善指示でリライト
            improvements = audit_result.get("improvements", [])
            final_content = await self._rewrite_episode(final_content, improvements, spice_elements)

            # 再監査
            audit_result = await self._audit_episode(final_content, bible, plot, ep_num)
            rewrite_count += 1

        return EpisodeResult(
            episode_num=ep_num,
            title=plot["title"],
            content=final_content,
            word_count=len(final_content),
            audit_score=audit_result["score"],
            audit_passed=audit_result["score"] >= self.config.target_audit_score,
            rewrite_count=rewrite_count,
            spice_elements=spice_elements,
            metadata={"plot": plot, "audit_details": audit_result},
            needs_human_review=audit_result.get("needs_human_review", False),
        )

    # === ヘルパーメソッド ===

    def _get_preset_defaults(self) -> dict[str, Any]:
        """プリセットからデフォルト変数を抽出"""
        # characters, titles, marketing からデフォルト値を抽出
        defaults = {}

        chars = self.preset.get("characters", {})
        if "archetypes" in chars:
            proto = chars["archetypes"].get("protagonist") or chars["archetypes"].get("dm")
            if proto:
                defaults["protagonist_name"] = proto.get("name_pattern", "主人公").split("（")[0]

        titles = self.preset.get("titles", {})
        if titles.get("title_templates"):
            defaults["title_template"] = titles["title_templates"][0]

        marketing = self.preset.get("marketing", {})
        if marketing.get("synopsis_structure"):
            defaults["concept"] = marketing["synopsis_structure"].get("hook", "")

        return defaults

    def _parse_bible(self, text: str) -> dict[str, Any]:
        """Bibleテキストをパース"""
        # 簡易パース：JSON部分を抽出、または構造化
        try:
            import json

            return json.loads(text)
        except Exception:
            # フォールバック：テキストをそのまま格納
            return {"raw": text, "parsed": False}

    def _fallback_bible(self, variables: dict[str, Any]) -> dict[str, Any]:
        """Bible生成失敗時のフォールバック"""
        return {
            "world": variables.get("world_rules_json", "{}"),
            "concept": variables.get("concept", ""),
            "protagonist": variables.get("protagonist_name", "主人公"),
            "cheat_ability": variables.get("cheat_ability", ""),
            "catharsis_target": variables.get("catharsis_target", ""),
            "fallback": True,
        }

    def _interpolate_tension(self, progress: float, curve_points: list[list[float]]) -> float:
        """テンション曲線から進行度に対応する値を補間"""
        if not curve_points:
            return 0.5

        for i in range(len(curve_points) - 1):
            p1, t1 = curve_points[i]
            p2, t2 = curve_points[i + 1]
            if p1 <= progress <= p2:
                ratio = (progress - p1) / (p2 - p1) if p2 != p1 else 0
                return t1 + (t2 - t1) * ratio

        return curve_points[-1][1]

    def _select_plot_pattern(self, ep_num: int, is_catharsis: bool) -> dict[str, Any]:
        """話数・カタルシス有無に応じた展開パターン選択"""
        patterns = {
            "opening": {
                "name": "opening",
                "title_suffix": "〜始まりの刻印〜",
                "beats": ["日常の提示", "異変の兆候", "決定的な事件", "新世界への扉"],
                "hook": "冒頭3行で読者の欠落を刺激",
            },
            "catharsis": {
                "name": "catharsis",
                "title_suffix": "〜逆転の咆哮〜",
                "beats": ["絶体絶命", "覚醒のトリガー", "圧倒的無双", "ざまぁの完成"],
                "hook": "カタルシス直後の余韻で次話へ",
                "catharsis_type": "major",
            },
            "development": {
                "name": "development",
                "title_suffix": "〜試練の連鎖〜",
                "beats": ["新たな敵・課題", "仲間との出会い", "スキル・戦力の拡張", "伏線の提示"],
                "hook": "次なる脅威の予兆",
            },
            "climax": {
                "name": "climax",
                "title_suffix": "〜最終決戦の序曲〜",
                "beats": ["最大の危機", "真相の暴露", "全戦力の結集", "決戦への覚悟"],
                "hook": "最終話への最大級クリフハンガー",
            },
            "resolution": {
                "name": "resolution",
                "title_suffix": "〜新たな世界の幕開け〜",
                "beats": ["完全勝利", "因果の清算", "新秩序の構築", "平穏な日常へ"],
                "hook": "エピローグへの静かな誘い",
            },
        }

        if ep_num == 1:
            return patterns["opening"]
        elif ep_num == EP_FINAL:
            return patterns["resolution"]
        elif ep_num == EP_CLIMAX:
            return patterns["climax"]
        elif is_catharsis:
            return patterns["catharsis"]
        else:
            return patterns["development"]

    def _build_prev_context(self, episodes: list[EpisodeResult]) -> str:
        """前話までの要約文脈構築"""
        if not episodes:
            return "（第1話のため前話なし）"

        summaries = []
        for ep in episodes[-3:]:  # 直近3話のみ
            summaries.append(f"第{ep.episode_num}話: {ep.title} - {ep.content[:200]}...")

        return "\n\n".join(summaries)

    async def _write_episode(self, ep_num: int, bible: dict, plot: dict, prev_context: str) -> str:
        """第1話執筆"""
        # 既存のエンジン執筆機能を使用
        # engine.narrative.write_episode 等を呼び出し
        try:
            # プリセットのStyle DNA、フック、官能ルールを注入
            style_dna = self.preset.get("style", {})
            hooks = self.preset.get("hooks", {})
            erotic_rules = self.preset.get("erotic", {})

            # 執筆プロンプト構築・実行
            prompt = self._build_writing_prompt(
                ep_num, bible, plot, prev_context, style_dna, hooks, erotic_rules
            )

            content = await self._generate_with_retry(prompt, {}, f"write_episode_{ep_num}")
            return content
        except Exception as e:
            logger.error(f"Writing failed for ep {ep_num}: {e}")
            return f"[執筆エラー: 第{ep_num}話の生成に失敗しました]"

    def _build_writing_prompt(
        self,
        ep_num: int,
        bible: dict,
        plot: dict,
        prev_context: str,
        style_dna: dict,
        hooks: dict,
        erotic_rules: dict,
    ) -> str:
        """執筆プロンプト構築"""
        # 既存の final_writing_prompt.j2 相当を構築
        return f"""
        【第{ep_num}話 執筆指示】

        Bible: {bible}
        プロット: {plot}
        前話文脈: {prev_context}

        Style DNA: {style_dna}
        フック戦略: {hooks}
        官能ルール: {erotic_rules}

        目標文字数: 3000-5000字
        テンション目標: {plot.get("target_tension", 0.5)}
        カタルシス話: {plot.get("is_catharsis", False)}

        以下の制約を厳守せよ：
        1. POV漏れ禁止
        2. ショー・ドン・テル
        3. 各シーン末尾にフック
        4. 官能Lv.{erotic_rules.get("max_intensity_level", 3)}以下
        5. 独自比喩・キャラ声・伏線回収キーワードを保護
        """

    async def _audit_episode(
        self, content: str, bible: dict, plot: dict, ep_num: int
    ) -> dict[str, Any]:
        """監査エージェント統合呼び出し"""
        # 既存の監査機能を使用
        try:
            audit_result = await self.engine.auditor.audit(
                content,
                {"bible": bible, "plot": plot, "episode": ep_num, "genre": self.config.genre},
            )

            # スコア正規化（0-100）
            score = audit_result.get("overall_score", 0)
            if score > 100:
                score = score / 10  # 1000点満点なら100点満点に

            return {
                "score": score,
                "passed": score >= self.config.target_audit_score,
                "issues": audit_result.get("issues", []),
                "improvements": audit_result.get("improvements", []),
                "details": audit_result,
            }
        except Exception as e:
            if self._cancelled:
                raise
            logger.warning(f"Audit failed for ep {ep_num}: {e}")
            return {
                "score": 85,  # デフォルトスコア
                "passed": False,
                "issues": ["監査エラー"],
                "improvements": ["監査システムを確認してください"],
                "details": {},
            }

    def _extract_spice(self, text: str) -> list[SpiceElement]:
        """尖り要素の自動抽出（SpiceGuard使用）"""
        if not hasattr(self, "_spice_guard"):
            self._spice_guard = create_spice_guard(self.config.genre)
        return self._spice_guard.extract_spice(text)

    def _inject_spice_markers(self, text: str, spice_elements: list[SpiceElement]) -> str:
        """尖り要素を保護マーカーで囲む"""
        # 位置順にソート（後ろから置換）
        sorted_elements = sorted(spice_elements, key=lambda x: x.position, reverse=True)

        result = text
        for elem in sorted_elements:
            pos = elem.position
            length = len(elem.text)
            if pos >= 0 and length > 0:
                marker_id = f"{elem.type}_{pos}"
                before = result[:pos]
                target = result[pos : pos + length]
                after = result[pos + length :]
                result = before + f"<<<SPICE:{marker_id}>>> {target} <<</SPICE>>>" + after

        return result

    async def _rewrite_episode(
        self, content: str, improvements: list[str], spice_elements: list[SpiceElement]
    ) -> str:
        """SpiceGuard付きリライト"""
        if not improvements:
            return content

        protected_content = self._inject_spice_markers(content, spice_elements)

        prompt = f"""
        以下の小説を改善せよ。ただし、<<<SPICE:...>>> で囲まれた部分は
        『絶対に変更するな。一文字も触るな。そこがこの話の『命』だ。』

        【改善指示】
        {chr(10).join(f"- {imp}" for imp in improvements)}

        【原文】
        {protected_content}

        改善後の本文のみを出力せよ。SPICEマーカーはそのまま残せ。
        """

        try:
            rewritten = await self._generate_with_retry(prompt, {}, "rewrite_episode")
            # SPICEマーカーを除去
            import re

            cleaned = re.sub(r"<<<SPICE:[^>]+>>>|<<</SPICE>>>", "", rewritten)
            return cleaned
        except Exception as e:
            logger.error(f"Rewrite failed: {e}")
            return content

    def _build_rewrite_prompt(
        self, content: str, improvements: list[str], spice_elements: list[SpiceElement]
    ) -> str:
        """SpiceGuard付きリライトプロンプト構築（テスト用公開メソッド）"""
        if not hasattr(self, "_spice_guard"):
            self._spice_guard = create_spice_guard(self.config.genre)
        return self._spice_guard.build_rewrite_prompt(content, improvements, spice_elements)

    async def _finalize_series(
        self, bible: dict, plot_outline: list, episodes: list[EpisodeResult]
    ) -> dict:
        """シリーズ完結処理・メタデータ生成"""
        total_words = sum(ep.word_count for ep in episodes)
        avg_score = sum(ep.audit_score for ep in episodes) / len(episodes) if episodes else 0

        # タイトル生成
        titles = self.preset.get("titles", {})
        title = titles.get("title_templates", ["無題"])[0]

        # あらすじ生成
        marketing = self.preset.get("marketing", {})
        synopsis = marketing.get("synopsis_structure", {})

        return {
            "title": title,
            "concept": marketing.get("synopsis_structure", {}).get("hook", ""),
            "total_words": total_words,
            "average_audit_score": round(avg_score, 1),
            "episodes_completed": len(episodes),
            "synopsis": synopsis,
            "tags": marketing.get("tags", [])[:10],
            "catchphrase": marketing.get("catchphrase_templates", [""])[0],
        }

    async def _report_progress(self, stage: str, current: int, total: int):
        """進捗報告"""
        if self.config.progress_callback:
            self.config.progress_callback(stage, current, total)

    def cancel(self):
        """キャンセル"""
        self._cancelled = True


def create_series(
    engine, genre: str, target_episodes: int = 8, progress_callback: Callable | None = None
) -> EasyModePipeline:
    """シリーズ作成エントリーポイント"""
    config = PipelineConfig(
        genre=genre, target_episodes=target_episodes, progress_callback=progress_callback
    )
    return EasyModePipeline(engine, config)
