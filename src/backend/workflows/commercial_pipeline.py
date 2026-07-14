"""
src/backend/workflows/commercial_pipeline.py — 商用化統合パイプライン（本格実装）
追加：包括的なエラー処理とリトライ機構
"""

import json
import csv
import uuid
import asyncio
import logging
import random
import os
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

from src.services.episode_writer import EpisodeWriter
from src.core.exceptions import PipelineError  # 新規カスタム例外

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# リトライ デコレータ（非同期関数に対して指数バックオフでリトライ）
# ----------------------------------------------------------------------
def async_retry(max_attempts: int = 3, base_delay: float = 1.0):
    """非同期関数の呼び出しを指数バックオフでリトライするデコレータ。"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"Attempt {attempt} failed permanently: {exc}")
                        raise PipelineError(f"Pipeline step failed after {attempt} attempts: {exc}") from exc
                    delay = base_delay * (2 ** (attempt - 1))
                    jitter = delay * 0.1 * random.uniform(0.5, 1.5)  # randomized jitter
                    logger.warning(f"Attempt {attempt} failed with {exc}. Retrying in {delay+jitter:.2f}s...")
                    await asyncio.sleep(delay + jitter)
        return wrapper
    return decorator

class CommercialPipeline:
    """統合パイプラインクラス"""
    
    def __init__(self, csv_path: Optional[str] = None):
        """
        Initialize pipeline with optional CSV output path.
        
        Args:
            csv_path: CSV出力先パス。未指定の場合はデフォルト値を使用
        """
        self.csv_path = csv_path or "/tmp/commercial_schedule.csv"
        
    @async_retry(max_attempts=3, base_delay=1.0)
    async def _step_plan_async(self, series_config: dict) -> Dict[str, Any]:
        """Bible生成ステップ（リトライ対応）"""
        return self._step_plan(series_config)
    
    @staticmethod
    def _step_plan(series_config: dict) -> Dict[str, Any]:
        """
        Bible生成ステップ。
        
        Args:
            series_config: シリーズ設定
            
        Returns:
            dict: Bibleデータ（詳細情報を含む）
        """
        try:
            # キーワードリスト取得・正規化
            keywords = [kw.strip() for kw in series_config.get("keywords", "") if kw.strip()]
            if not keywords:
                raise ValueError("Missing required keywords")
            
            # トレンド情報取得（将来的に外部トレンドAPI等を想定）
            trend_memo = series_config.get("trend_memo", "")
            
            # 基本設定取得
            target_eps = series_config.get("target_eps", 10)
            target_word_per_ep = series_config.get("target_word_count_per_episode", 3000)
            genre = series_config.get("genre", "general")
            concept = series_config.get("concept", "現代日本")
            platforms = series_config.get("platforms", ["kakuyomu", "naru"])
            
            # Bible構造を作成（拡張版）
            bible_data = {
                "concept": concept,
                "genre": genre,
                "keywords": keywords,
                "trend_analysis": trend_memo,
                "target_eps": target_eps,
                "target_word_count_per_episode": target_word_per_ep,
                "target_platforms": list(set(platforms)),
                "book_id": series_config.get("book_id", 1),
                "unique_selling_points": [
                    f"Keywords: {', '.join(keywords)}",
                    f"Trend: {trend_memo}",
                    f"Eps: {target_eps}",
                    f"Word/episode: {target_word_per_ep}",
                    "Multi-platform support"
                ],
                # 連続性確保フラグや后续设置
                "continuity": {
                    "enable": True,
                    "plan": "standard"
                }
            }
            
            logger.info("Bible generation completed", extra={"bible": bible_data})
            return bible_data
            
        except Exception as e:
            logger.exception("Error in Bible generation")
            raise PipelineError(f"Bible generation failed: {e}") from e
    
    @async_retry(max_attempts=3, base_delay=1.0)
    async def _generate_content_async(
        self,
        bible: Dict[str, Any], 
        samples: List[Dict[str, Any]], 
        platforms: List[str]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """コンテンツ生成ステップ（リトライ対応）"""
        return await self._generate_content(bible, samples, platforms)
    
    async def _generate_content(
        self,
        bible: Dict[str, Any], 
        samples: List[Dict[str, Any]], 
        platforms: List[str]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        コンテンツ生成ステップ。
        
        Args:
            bible: Bibleデータ
            samples: 生成サンプル（使用しないがAPI互換性確保）
            platforms: 対象プラットフォーム
            
        Returns:
            tuple: (selected_items, exports_data)
        """
        selected: List[Dict[str, Any]] = []
        exports: Dict[str, Any] = {}
        
        try:
            # 目標エピソード数取得
            target_episodes = bible.get("target_eps", 10)
            
            # EpisodeWriterインスタンス化
            writer = EpisodeWriter()
            
            for ep_num in range(1, target_episodes + 1):
                # 前話情報取得（連続性確保のために前エピソードの要約やテキストをコンテキストに含める）
                previous_episode_context = None
                if selected:
                    prev_episode = selected[-1]
                    previous_episode_context = {
                        "summary": prev_episode.get("summary", ""),
                        "text_excerpt": prev_episode.get("content", "")[:500],
                        "killer_phrase": prev_episode.get("killer_phrase", ""),
                    }
                
                # コンテキスト作成（WritingAgent が利用する想定の形式に準拠）
                context = {
                    "ep_num": ep_num,
                    "title": f"第{ep_num}話",
                    "is_first": ep_num == 1,
                    "is_last": ep_num == target_episodes,
                    "target_word_count": bible.get("target_word_count_per_episode", 3000),
                    "genre": bible.get("genre", "general"),
                    "concept": bible.get("concept", ""),
                    "keywords": bible.get("keywords", []),
                    "previous_episode_summary": previous_episode_context["summary"] if previous_episode_context else None,
                    "previous_episode_text": previous_episode_context["text_excerpt"] if previous_episode_context else None,
                    "previous_killer_phrase": previous_episode_context["killer_phrase"] if previous_episode_context else None,
                    # WritingAgent が利用する想定のキー
                    "plot": {
                        "branch_id": 1,  # 将来的に取得可能
                        "ep_num": ep_num,
                    },
                    "script": "",  # 将来的に脚本データを投入
                    "target_word_count": bible.get("target_word_count_per_episode", 3000),
                    "continuation": True,  # 続き執筆フラグ
                    "build_platform": "streamlit_demo"
                }
                
                try:
                    # 修正1: book_id を動的に取得（book_id=0 ではなく実際の値）
                    # ただし、この例では book_id の取得ロジックが実装されていないため、一時的に 1 を使用
                    book_id = bible.get("book_id", 1)  # 修正1: bible_data から book_id を取得
                    result = await writer.write(
                        book_id=book_id,  # 修正1: ダミーbook_idから実際の値へ
                        ep_num=ep_num,
                        context=context
                    )
                    
                    # 生成結果の加工
                    episode_entry = {
                        "ep_num": ep_num,
                        "title": context["title"],
                        "content": result.get("text", ""),
                        "summary": result.get("summary", ""),
                        "quality_score": result.get("quality_score", 0.0),
                        "killer_phrase": result.get("killer_phrase", ""),
                    }
                    selected.append(episode_entry)
                    
                    # exportsデータ構築（platformごとに情報を格納）
                    for platform in platforms:
                        if platform not in exports:
                            exports[platform] = []
                        exports[platform].append({
                            "ep_num": ep_num,
                            "title": context["title"],
                            "format": "web",
                            "target_word_count": context["target_word_count"]
                        })
                except Exception as e:
                    logger.warning(f"Episode {ep_num} generation failed: {e}")
                    raise PipelineError(f"Episode {ep_num} generation failed: {e}") from e
              
            logger.info(f"Content generation completed: {len(selected)} episodes generated", extra={"selected_episode_count": len(selected)})
            return selected, exports
        except Exception as e:
            logger.exception("Error in content generation pipeline")
            raise PipelineError(f"Content generation failed: {e}") from e
    
    def _create_schedule_csv(self, exports: Dict[str, Any]) -> str:
        """
        CSV出力スケジュール作成ステップ。
        
        Args:
            exports: 出力データ
            
        Returns:
            str: CSVファイルパス
        """
        try:
            csv_content = "platform,ep_num,title,format,target_word_count,output_path\n"
            for platform, episodes in exports.items():
                for episode in episodes:
                    csv_content += f"{platform},{episode['ep_num']},{episode['title']},{episode['format']},{episode['target_word_count']},/output/{platform}_ep{episode['ep_num']}.txt\n"
            
            # CSVファイルへ書き込み（実際の出力は /tmp 以下に実装）
            csv_path = self.csv_path  # 修正2: ハードコードされたパスを使用せず、インスタンス変数を使用
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write(csv_content)
            
            logger.info("Schedule CSV created", extra={"path": csv_path})
            return csv_path
            
        except Exception as e:
            logger.exception("Failed to create schedule CSV")
            raise PipelineError(f"CSV creation failed: {e}") from e
    
    async def run(self, series_config: dict, samples: list, platforms: list) -> Dict[str, Any]:
        """
        パイプラインのエントリーポイント。
        
        Args:
            series_config: シリーズ設定パラメータ
            samples: 生成サンプルリスト（実itel的に使用しないが将来拡張可能）
            platforms: 対象プラットフォームリスト
            
        Returns:
            dict: パイプライン実行結果
        """
        logger.info("CommercialPipeline.run started")
        try:
            # 1. Bible生成（リトライ対応）
            bible = await self._step_plan_async(series_config)
            
            # 2. コンテンツ生成（リトライ対応）
            selected, exports = await self._generate_content_async(bible, samples, platforms)
            
            # 3. CSV出力スケジュール作成
            schedule_csv = self._create_schedule_csv(exports)
            
            result = {
                "bible": bible,
                "selected": selected,
                "exports": exports,
                "schedule_csv": schedule_csv
            }
            logger.info("CommercialPipeline.run completed successfully")
            return result
            
        except PipelineError as perr:
            logger.error(f"PipelineError caught: {perr}")
            return {
                "error": str(perr),
                "bible": None,
                "selected": [],
                "exports": {},
                "schedule_csv": None
            }
        except Exception as e:
            logger.exception("Unexpected error in CommercialPipeline.run")
            return {
                "error": str(e),
                "bible": None,
                "selected": [],
                "exports": {},
                "schedule_csv": None
            }