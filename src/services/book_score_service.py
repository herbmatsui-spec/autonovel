# src/services/book_score_service.py
"""BookScore 計算サービス"""
import logging
from typing import Any, Dict, Optional, Protocol
from dataclasses import dataclass
from datetime import datetime

from src.agents.orchestrator import AgentContext, AgentResult
from src.infrastructure.database.models.book_score import BookScore as BookScoreModel

logger = logging.getLogger(__name__)


@dataclass
class BookScore:
    overall_score: float
    structure_score: float
    coherency_score: float
    factual_grounding_score: float
    visual_textual_synergy_score: float
    reader_experience_score: float


class BookScoreRepository(Protocol):
    """BookScore リポジトリのプロトコル"""

    async def save(self, score: BookScoreModel) -> None:
        ...

    async def get_latest(self, book_id: int, chapter_number: int) -> Optional[BookScoreModel]:
        ...


class BookScoreCalculator:
    """統一100点尺度の成熟度評価メトリクスを計算する"""

    def __init__(
        self,
        config_path: str = "config/book_score_weights.yaml",
        repository: Optional[BookScoreRepository] = None,
    ):
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        self.default_weights = config.get("default", {})
        self.genre_overrides = config.get("genre_overrides", {})
        self.phase_overrides = config.get("phase_overrides", {})
        self._repository = repository

    def _get_weights(self, genre: str = "", phase: str = "") -> Dict[str, float]:
        """ジャンルとフェーズに基づく重みを取得"""
        weights = self.default_weights.copy()
        if genre and genre in self.genre_overrides:
            weights.update(self.genre_overrides[genre])
        if phase and phase in self.phase_overrides:
            weights.update(self.phase_overrides[phase])
        return weights

    async def calculate(
        self,
        book_id: int,
        chapter_number: int,
        ctx: Optional[AgentContext] = None,
        genre: str = "",
        phase: str = "",
    ) -> BookScore:
        """BookScore を計算する"""
        weights = self._get_weights(genre, phase)

        # 各次元スコアを計算（0-100 の範囲で正規化）
        structure = await self._score_structure(book_id, chapter_number, ctx)
        coherency = await self._score_coherency(book_id, chapter_number, ctx)
        factual = await self._score_factual(book_id, chapter_number, ctx)
        visual_textual = await self._score_visual_textual(book_id, chapter_number, ctx)
        reader_exp = await self._score_reader_experience(book_id, chapter_number, ctx)

        # 重み付け合計（各スコアは0-100、重みはパーセント）
        overall = (
            structure * weights.get("structure", 25) / 100
            + coherency * weights.get("coherency", 25) / 100
            + factual * weights.get("factual_grounding", 20) / 100
            + visual_textual * weights.get("visual_textual_synergy", 15) / 100
            + reader_exp * weights.get("reader_experience", 15) / 100
        )

        book_score = BookScore(
            overall_score=round(overall, 2),
            structure_score=round(structure, 2),
            coherency_score=round(coherency, 2),
            factual_grounding_score=round(factual, 2),
            visual_textual_synergy_score=round(visual_textual, 2),
            reader_experience_score=round(reader_exp, 2),
        )

        # 自動保存
        if self._repository:
            await self.save_score(book_id, chapter_number, book_score, evaluator_version="1.0")

        return book_score

    async def save_score(
        self,
        book_id: int,
        chapter_number: int,
        score: BookScore,
        evaluator_version: str = "1.0",
    ) -> None:
        """スコアをデータベースに保存する"""
        if not self._repository:
            logger.warning("Repository not configured, skipping save")
            return
        model = BookScoreModel(
            book_id=book_id,
            chapter_number=chapter_number,
            overall_score=score.overall_score,
            structure_score=score.structure_score,
            coherency_score=score.coherency_score,
            factual_grounding_score=score.factual_grounding_score,
            visual_textual_synergy_score=score.visual_textual_synergy_score,
            reader_experience_score=score.reader_experience_score,
            evaluated_at=datetime.utcnow(),
            evaluator_version=evaluator_version,
        )
        await self._repository.save(model)

    async def get_latest_score(
        self, book_id: int, chapter_number: int
    ) -> Optional[BookScoreModel]:
        """最新のスコアを取得する"""
        if not self._repository:
            return None
        return await self._repository.get_latest(book_id, chapter_number)

    # ---- データ取得ヘルパー ----
    async def _fetch_plot(
        self, book_id: int, chapter_number: int
    ) -> Optional[Any]:
        """プロット情報を取得"""
        if not self._repository or not hasattr(self._repository, 'session'):
            return None
        try:
            from src.infrastructure.database.models.plot import Plot as PlotModel
            from sqlalchemy import select
            result = await self._repository.session.execute(
                select(PlotModel).where(
                    PlotModel.book_id == book_id,
                    PlotModel.ep_num == chapter_number
                ).order_by(PlotModel.id.desc())
            )
            return result.scalars().first()
        except Exception as e:
            logger.debug(f"Failed to fetch plot: {e}")
            return None

    async def _fetch_chapter(
        self, book_id: int, chapter_number: int
    ) -> Optional[Any]:
        """章データを取得"""
        if not self._repository or not hasattr(self._repository, 'session'):
            return None
        try:
            from src.infrastructure.database.models.chapter import Chapter as ChapterModel
            from sqlalchemy import select
            result = await self._repository.session.execute(
                select(ChapterModel).where(
                    ChapterModel.book_id == book_id,
                    ChapterModel.ep_num == chapter_number
                )
            )
            return result.scalars().first()
        except Exception as e:
            logger.debug(f"Failed to fetch chapter: {e}")
            return None

    async def _fetch_illustration(
        self, book_id: int, chapter_number: int
    ) -> Optional[Any]:
        """挿絵データを取得"""
        if not self._repository or not hasattr(self._repository, 'session'):
            return None
        try:
            from src.infrastructure.database.models.illustration import Illustration as IllustrationModel
            from sqlalchemy import select
            result = await self._repository.session.execute(
                select(IllustrationModel).where(
                    IllustrationModel.book_id == book_id,
                    IllustrationModel.episode_number == chapter_number
                ).order_by(IllustrationModel.id.desc())
            )
            return result.scalars().first()
        except Exception as e:
            logger.debug(f"Failed to fetch illustration: {e}")
            return None

    async def _fetch_bible(
        self, book_id: int
    ) -> Optional[Any]:
        """Bible（世界観設定）を取得"""
        if not self._repository or not hasattr(self._repository, 'session'):
            return None
        try:
            from src.infrastructure.database.models.bible import Bible as BibleModel
            from sqlalchemy import select
            result = await self._repository.session.execute(
                select(BibleModel).where(
                    BibleModel.book_id == book_id
                ).order_by(BibleModel.id.desc())
            )
            return result.scalars().first()
        except Exception as e:
            logger.debug(f"Failed to fetch bible: {e}")
            return None

    async def _fetch_audit_report(
        self, book_id: int, chapter_number: int
    ) -> Optional[Any]:
        """監査レポートを取得"""
        if not self._repository or not hasattr(self._repository, 'session'):
            return None
        try:
            from src.infrastructure.database.models.audit import AuditIssue as AuditIssueModel
            from sqlalchemy import select
            result = await self._repository.session.execute(
                select(AuditIssueModel).where(
                    AuditIssueModel.book_id == book_id,
                    AuditIssueModel.ep_num == chapter_number
                ).order_by(AuditIssueModel.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.debug(f"Failed to fetch audit report: {e}")
            return None

    async def _build_text_stats(self, text: str) -> dict:
        """テキスト統計を計算"""
        if not text:
            return {"char_count": 0, "word_count": 0, "sentence_count": 0, "avg_sentence_length": 0.0}
        import re
        sentences = re.split(r'[。！？.!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        char_count = len(text)
        word_count = len(text.split())
        sentence_count = len(sentences)
        avg_sentence_length = char_count / max(1, sentence_count)
        return {
            "char_count": char_count,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": avg_sentence_length,
        }

    async def _score_structure(
        self, book_id: int, chapter_number: int, ctx: Optional[AgentContext]
    ) -> float:
        """構造スコア (0-25点スケールを0-100に正規化)
        
        評価項目:
        1. プロット因果整合性 (0-35点): 論理監査結果から
        2. 章構成バランス (0-35点): アーク境界と実話数の整合
        3. テンポ・ペーシング (0-30点): ストレス曲線の適切性
        """
        if not self._repository or not hasattr(self._repository, 'session'):
            return 50.0  # デフォルト値
        
        try:
            # 1. プロット因果整合性 (監査レポートから)
            audit_report = await self._fetch_audit_report(book_id, chapter_number)
            causal_score = 70.0  # デフォルト
            if audit_report:
                # 論理整合性・因果律監査の結果を確認
                logical_passed = any(
                    getattr(a, 'category', '') == 'logical_consistency' and 
                    getattr(a, 'severity', '') != 'high' 
                    for a in audit_report
                )
                causal_passed = any(
                    getattr(a, 'category', '') == 'causal_integrity' and 
                    getattr(a, 'severity', '') != 'high'
                    for a in audit_report
                )
                if logical_passed and causal_passed:
                    causal_score = 95.0
                elif logical_passed or causal_passed:
                    causal_score = 75.0
                else:
                    causal_score = 40.0
            
            # 2. 章構成バランス (アーク境界チェック)
            plot = await self._fetch_plot(book_id, chapter_number)
            arc_score = 70.0
            if plot:
                # アーク終了話数と実話数の比較
                arc_end = getattr(plot, 'end_ep', None)
                if arc_end:
                    # アーク終了話数付近なら高スコア
                    if abs(chapter_number - arc_end) <= 1:
                        arc_score = 95.0
                    elif abs(chapter_number - arc_end) <= 3:
                        arc_score = 80.0
                    else:
                        arc_score = 60.0
            
            # 3. テンポ・ペーシング (ストレス曲線)
            chapter = await self._fetch_chapter(book_id, chapter_number)
            pacing_score = 70.0
            if chapter and hasattr(chapter, 'tension'):
                tension = getattr(chapter, 'tension', 50)
                # 適切なテンション範囲 (40-80) で高スコア
                if 40 <= tension <= 80:
                    pacing_score = 90.0
                elif 20 <= tension <= 90:
                    pacing_score = 75.0
                else:
                    pacing_score = 50.0
            
            # 重み付け合計 (0-100スケール)
            total = (
                causal_score * 0.35 +
                arc_score * 0.35 +
                pacing_score * 0.30
            )
            return round(min(100.0, max(0.0, total)), 2)
            
        except Exception as e:
            logger.debug(f"Structure scoring failed: {e}")
            return 50.0

    async def _score_coherency(
        self, book_id: int, chapter_number: int, ctx: Optional[AgentContext]
    ) -> float:
        """一貫性スコア (0-25点スケールを0-100に正規化)
        
        評価項目:
        1. キャラクター口調一貫性 (0-30点): 監査レポートの口調チェック
        2. 世界観ルール遵守 (0-30点): 能力整合性監査結果
        3. タイムライン一貫性 (0-20点): 因果律監査結果
        4. 固有名詞表記統一 (0-20点): テキスト統計・表記揺れ検出
        """
        if not self._repository or not hasattr(self._repository, 'session'):
            return 50.0
        
        try:
            # 1. キャラクター口調一貫性 (監査レポートから)
            audit_report = await self._fetch_audit_report(book_id, chapter_number)
            speech_score = 70.0
            if audit_report:
                # 口調関連の監査問題をチェック
                speech_issues = [
                    a for a in audit_report 
                    if 'speech' in getattr(a, 'category', '').lower() or
                       'dialogue' in getattr(a, 'category', '').lower() or
                       '口調' in getattr(a, 'description', '')
                ]
                if not speech_issues:
                    speech_score = 95.0
                elif len(speech_issues) == 1:
                    speech_score = 75.0
                else:
                    speech_score = 50.0
            
            # 2. 世界観ルール遵守 (能力整合性監査)
            world_rule_score = 70.0
            if audit_report:
                ability_issues = [
                    a for a in audit_report 
                    if 'ability' in getattr(a, 'category', '').lower() or
                       '能力' in getattr(a, 'description', '')
                ]
                if not ability_issues:
                    world_rule_score = 95.0
                elif len(ability_issues) == 1:
                    world_rule_score = 75.0
                else:
                    world_rule_score = 50.0
            
            # 3. タイムライン一貫性 (因果律監査)
            timeline_score = 70.0
            if audit_report:
                causal_issues = [
                    a for a in audit_report 
                    if 'causal' in getattr(a, 'category', '').lower() or
                       '因果' in getattr(a, 'description', '')
                ]
                if not causal_issues:
                    timeline_score = 95.0
                elif len(causal_issues) == 1:
                    timeline_score = 75.0
                else:
                    timeline_score = 50.0
            
            # 4. 固有名詞表記統一 (テキスト統計から簡易チェック)
            chapter = await self._fetch_chapter(book_id, chapter_number)
            naming_score = 70.0
            if chapter and hasattr(chapter, 'content') and chapter.content:
                text = chapter.content
                # 簡易的な表記揺れ検出: 同一単語の異なる表記パターン
                import re
                # カタカナ・ひらがな・漢字の混在チェック
                words = re.findall(r'[一-龯ぁ-んァ-ヴー]+', text)
                if words:
                    from collections import Counter
                    word_counts = Counter(words)
                    # 同一読みで異なる表記があるかチェック（簡易版）
                    unique_forms = len(word_counts)
                    total_occurrences = sum(word_counts.values())
                    if total_occurrences > 0:
                        consistency_ratio = unique_forms / total_occurrences
                        if consistency_ratio > 0.9:
                            naming_score = 95.0
                        elif consistency_ratio > 0.7:
                            naming_score = 80.0
                        elif consistency_ratio > 0.5:
                            naming_score = 65.0
                        else:
                            naming_score = 50.0
            
            # 重み付け合計 (0-100スケール)
            total = (
                speech_score * 0.30 +
                world_rule_score * 0.30 +
                timeline_score * 0.20 +
                naming_score * 0.20
            )
            return round(min(100.0, max(0.0, total)), 2)
            
        except Exception as e:
            logger.debug(f"Coherency scoring failed: {e}")
            return 50.0

    async def _score_factual(
        self, book_id: int, chapter_number: int, ctx: Optional[AgentContext]
    ) -> float:
        """事実正確性スコア (0-20点スケールを0-100に正規化)
        
        評価項目:
        1. GraphRAG参照情報との整合性 (0-40点): RAG取得エンティティと本文の一致
        2. 歴史・文化的正確性 (0-35点): 時代考証チェック
        3. 用語の適切性 (0-25点): 用語集・Wiki照合
        """
        if not self._repository or not hasattr(self._repository, 'session'):
            return 50.0
        
        try:
            # 1. GraphRAG参照情報との整合性
            rag_score = 70.0
            # RAG から関連エンティティを取得して本文と比較（簡易版）
            chapter = await self._fetch_chapter(book_id, chapter_number)
            if chapter and hasattr(chapter, 'content') and chapter.content:
                text = chapter.content
                # Bible から世界設定を取得してキーワード抽出
                bible = await self._fetch_bible(book_id)
                if bible and hasattr(bible, 'settings') and bible.settings:
                    import json
                    try:
                        settings = json.loads(bible.settings) if isinstance(bible.settings, str) else bible.settings
                        # 設定からキーワード抽出
                        keywords = set()
                        if isinstance(settings, dict):
                            for v in settings.values():
                                if isinstance(v, str):
                                    import re
                                    keywords.update(re.findall(r'[一-龯ァ-ヴー]{2,}', v))
                        
                        if keywords:
                            # 本文にキーワードが含まれているかチェック
                            found = sum(1 for k in keywords if k in text)
                            coverage = found / max(1, len(keywords))
                            if coverage > 0.7:
                                rag_score = 95.0
                            elif coverage > 0.4:
                                rag_score = 80.0
                            elif coverage > 0.2:
                                rag_score = 65.0
                            else:
                                rag_score = 50.0
                    except Exception:
                        pass
            
            # 2. 歴史・文化的正確性 (HistoricalAccuracyChecker 連携簡易版)
            history_score = 70.0
            if bible and hasattr(bible, 'settings') and bible.settings:
                try:
                    import json
                    settings = json.loads(bible.settings) if isinstance(bible.settings, str) else bible.settings
                    if isinstance(settings, dict):
                        period = settings.get('period', settings.get('時代', 'medieval'))
                        # 時代考証: アナクロニズム検出
                        anachronisms = self._get_anachronisms(period)
                        found_anachronisms = [a for a in anachronisms if a in text]
                        if not found_anachronisms:
                            history_score = 95.0
                        elif len(found_anachronisms) == 1:
                            history_score = 75.0
                        else:
                            history_score = 50.0
                except Exception:
                    pass
            
            # 3. 用語の適切性
            term_score = 70.0
            if chapter and hasattr(chapter, 'content') and chapter.content:
                text = chapter.content
                # 用語集から未定義語をチェック（簡易版）
                bible = await self._fetch_bible(book_id)
                if bible and hasattr(bible, 'settings') and bible.settings:
                    try:
                        import json
                        settings = json.loads(bible.settings) if isinstance(bible.settings, str) else bible.settings
                        if isinstance(settings, dict):
                            glossary = settings.get('glossary', settings.get('用語集', {}))
                            if glossary and isinstance(glossary, dict):
                                # 用語集にある用語が本文で正しく使われているか
                                used_terms = sum(1 for term in glossary if term in text)
                                total_terms = len(glossary)
                                if total_terms > 0:
                                    usage_ratio = used_terms / total_terms
                                    if usage_ratio > 0.5:
                                        term_score = 95.0
                                    elif usage_ratio > 0.2:
                                        term_score = 80.0
                                    else:
                                        term_score = 60.0
                    except Exception:
                        pass
            
            # 重み付け合計 (0-100スケール)
            total = (
                rag_score * 0.40 +
                history_score * 0.35 +
                term_score * 0.25
            )
            return round(min(100.0, max(0.0, total)), 2)
            
        except Exception as e:
            logger.debug(f"Factual scoring failed: {e}")
            return 50.0

    def _get_anachronisms(self, period: str) -> list[str]:
        """時代に合わない用語リストを返す（簡易版）"""
        anachronism_db = {
            "ancient": ["電話", "自動車", "飛行機", "コンピュータ", "プラスチック", "抗生物質"],
            "medieval": ["電話", "自動車", "飛行機", "コンピュータ", "プラスチック", "抗生物質", "拳銃", "ライフル"],
            "edo": ["電話", "自動車", "飛行機", "コンピュータ", "プラスチック", "抗生物質", "ライフル", "機関銃"],
            "modern": ["蒸気機関", "馬車", "提灯", "着物（日常着として）"],
            "futuristic": [],
        }
        return anachronism_db.get(period.lower(), [])

    async def _score_visual_textual(
        self, book_id: int, chapter_number: int, ctx: Optional[AgentContext]
    ) -> float:
        """ビジュアルテキスト相乗効果スコア (0-15点スケールを0-100に正規化)
        
        評価項目:
        1. 情報量マッチ度 (0-40点): 挿絵プロンプトと本文のエンティティ一致
        2. 焦点一致 (0-35点): 本文強調要素とプロンプト強調要素の一致
        3. 感情トーン整合性 (0-25点): 本文感情値とプロンプト色調指定の一致
        """
        if not self._repository or not hasattr(self._repository, 'session'):
            return 50.0
        
        try:
            # 挿絵データ取得
            illustration = await self._fetch_illustration(book_id, chapter_number)
            chapter = await self._fetch_chapter(book_id, chapter_number)
            
            if not illustration or not chapter or not hasattr(chapter, 'content') or not chapter.content:
                return 50.0  # データ不足時はデフォルト
            
            text = chapter.content
            prompt = getattr(illustration, 'prompt', '') or ''
            
            if not prompt:
                return 50.0
            
            # 1. 情報量マッチ度: エンティティ抽出・比較
            import re
            text_entities = set(re.findall(r'[一-龯ァ-ヴー]{2,}', text))
            prompt_entities = set(re.findall(r'[一-龯ァ-ヴー]{2,}', prompt))
            
            entity_score = 50.0
            if text_entities and prompt_entities:
                intersection = text_entities & prompt_entities
                union = text_entities | prompt_entities
                jaccard = len(intersection) / max(1, len(union))
                if jaccard > 0.5:
                    entity_score = 95.0
                elif jaccard > 0.3:
                    entity_score = 80.0
                elif jaccard > 0.1:
                    entity_score = 65.0
                else:
                    entity_score = 40.0
            
            # 2. 焦点一致: 本文の強調表現 vs プロンプトの強調キーワード
            focus_score = 50.0
            # 本文で強調されている要素（感嘆符、大文字、繰り返し等）
            emphasis_patterns = [
                r'！{2,}', r'\!\!{2,}', r'…', r'――',
                r'「[^」]{1,10}」', r'『[^』]{1,10}』'
            ]
            text_focus = set()
            for pattern in emphasis_patterns:
                text_focus.update(re.findall(pattern, text))
            
            # プロンプトの強調キーワード
            prompt_focus_keywords = [
                'focus', 'emphasis', 'highlight', 'dramatic', 'intense',
                '主役', '中心', 'クローズアップ', 'フォーカス', '強調'
            ]
            prompt_focus = set(kw for kw in prompt_focus_keywords if kw.lower() in prompt.lower())
            
            if text_focus and prompt_focus:
                # 簡易的な一致判定
                focus_score = 85.0
            elif text_focus or prompt_focus:
                focus_score = 65.0
            else:
                focus_score = 50.0
            
            # 3. 感情トーン整合性
            tone_score = 50.0
            # 本文の感情トーン推定（簡易版）
            positive_words = ['喜', '笑', '幸', '楽', '愛', '希望', '輝', '明']
            negative_words = ['悲', '泣', '苦', '痛', '憎', '絶望', '暗', '闇', '恐']
            
            text_pos = sum(text.count(w) for w in positive_words)
            text_neg = sum(text.count(w) for w in negative_words)
            
            prompt_pos = sum(prompt.lower().count(w.lower()) for w in ['bright', 'happy', 'joy', 'hope', 'warm', 'light'])
            prompt_neg = sum(prompt.lower().count(w.lower()) for w in ['dark', 'sad', 'gloom', 'fear', 'cold', 'shadow'])
            
            text_tone = 'positive' if text_pos > text_neg else ('negative' if text_neg > text_pos else 'neutral')
            prompt_tone = 'positive' if prompt_pos > prompt_neg else ('negative' if prompt_neg > prompt_pos else 'neutral')
            
            if text_tone == prompt_tone:
                tone_score = 95.0
            elif text_tone == 'neutral' or prompt_tone == 'neutral':
                tone_score = 70.0
            else:
                tone_score = 40.0
            
            # 重み付け合計 (0-100スケール)
            total = (
                entity_score * 0.40 +
                focus_score * 0.35 +
                tone_score * 0.25
            )
            return round(min(100.0, max(0.0, total)), 2)
            
        except Exception as e:
            logger.debug(f"Visual-textual scoring failed: {e}")
            return 50.0

    async def _score_reader_experience(
        self, book_id: int, chapter_number: int, ctx: Optional[AgentContext]
    ) -> float:
        """読者体験スコア (0-15点スケールを0-100に正規化)
        
        評価項目:
        1. 冒頭フック強度 (0-40点): 最初の200文字の「謎/違和感/危機」キーワード密度
        2. 末尾の引き・クリフハンガー (0-35点): 最後の200文字の未解決・示唆キーワード
        3. 感情曲線適切性 (0-25点): WavePatternAnalyzer スコア活用
        """
        if not self._repository or not hasattr(self._repository, 'session'):
            return 50.0
        
        try:
            chapter = await self._fetch_chapter(book_id, chapter_number)
            if not chapter or not hasattr(chapter, 'content') or not chapter.content:
                return 50.0
            
            text = chapter.content
            text_len = len(text)
            
            # 1. 冒頭フック強度 (最初の200文字)
            hook_score = 50.0
            if text_len >= 50:
                prefix = text[:min(200, text_len)]
                hook_keywords = [
                    'なぜ', 'どうして', '謎', '不思議', '奇妙', '違和感', '危機', 'ピンチ',
                    '突然', 'まさか', '誰', '何', 'どこ', 'いつ', '秘密', '隠',
                    '？', '?', '！', '!', '…', '……'
                ]
                hook_count = sum(prefix.count(kw) for kw in hook_keywords)
                hook_density = hook_count / max(1, len(prefix) / 100)
                if hook_density > 5:
                    hook_score = 95.0
                elif hook_density > 3:
                    hook_score = 80.0
                elif hook_density > 1:
                    hook_score = 65.0
                else:
                    hook_score = 40.0
            
            # 2. 末尾の引き・クリフハンガー (最後の200文字)
            cliffhanger_score = 50.0
            if text_len >= 50:
                suffix = text[-min(200, text_len):]
                cliff_keywords = [
                    '続', '次', '未', '謎', '秘密', '真実', '衝撃', '驚',
                    'どうなる', 'どうすれば', '運命', '分岐', '選択', '決断',
                    '？', '?', '！', '!', '…', '……', '――', '——'
                ]
                cliff_count = sum(suffix.count(kw) for kw in cliff_keywords)
                cliff_density = cliff_count / max(1, len(suffix) / 100)
                if cliff_density > 5:
                    cliffhanger_score = 95.0
                elif cliff_density > 3:
                    cliffhanger_score = 80.0
                elif cliff_density > 1:
                    cliffhanger_score = 65.0
                else:
                    cliffhanger_score = 40.0
            
            # 3. 感情曲線適切性 (WavePatternAnalyzer 簡易版)
            emotion_score = 50.0
            if hasattr(chapter, 'tension') and chapter.tension is not None:
                tension = chapter.tension
                # 適切なテンション変化を評価
                # ストレス曲線の波形が健全か
                # 簡易版: テンションが極端でない、かつ変化がある
                if 30 <= tension <= 85:
                    emotion_score = 85.0
                elif 15 <= tension <= 95:
                    emotion_score = 70.0
                else:
                    emotion_score = 50.0
            else:
                # テンションデータがない場合、テキストから簡易推定
                import re
                sentences = re.split(r'[。！？.!?]', text)
                sentences = [s.strip() for s in sentences if s.strip()]
                if len(sentences) > 3:
                    # 文長の変化で感情の起伏を推定
                    lengths = [len(s) for s in sentences]
                    avg_len = sum(lengths) / len(lengths)
                    var_len = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
                    cv = (var_len ** 0.5) / max(1, avg_len)  # 変動係数
                    if 0.3 <= cv <= 0.8:
                        emotion_score = 80.0
                    elif cv > 0.15:
                        emotion_score = 65.0
                    else:
                        emotion_score = 50.0
            
            # 重み付け合計 (0-100スケール)
            total = (
                hook_score * 0.40 +
                cliffhanger_score * 0.35 +
                emotion_score * 0.25
            )
            return round(min(100.0, max(0.0, total)), 2)
            
        except Exception as e:
            logger.debug(f"Reader experience scoring failed: {e}")
            return 50.0