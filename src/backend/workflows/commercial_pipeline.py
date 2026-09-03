"""
src/backend/workflows/commercial_pipeline.py — 商用化統合パイプライン（本格実装）
追加：包括的なエラー処理とリトライ機構
"""

import asyncio
import logging
import random
from typing import Any

from src.core.exceptions import PipelineError  # 新規カスタム例外
from src.services.episode_writer import EpisodeWriter
from src.services.publishers import (
    get_publisher,
    get_credential_store,
    PublisherCredentials,
    PublishResult,
)

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
                        raise PipelineError(
                            f"Pipeline step failed after {attempt} attempts: {exc}"
                        ) from exc
                    delay = base_delay * (2 ** (attempt - 1))
                    jitter = delay * 0.1 * random.uniform(0.5, 1.5)  # randomized jitter
                    logger.warning(
                        f"Attempt {attempt} failed with {exc}. Retrying in {delay + jitter:.2f}s..."
                    )
                    await asyncio.sleep(delay + jitter)

        return wrapper

    return decorator


class CommercialPipeline:
    """統合パイプラインクラス"""

    def __init__(self, csv_path: str | None = None):
        """
        Initialize pipeline with optional CSV output path.

        Args:
            csv_path: CSV出力先パス。未指定の場合はデフォルト値を使用
        """
        self.csv_path = csv_path or "/tmp/commercial_schedule.csv"

    @async_retry(max_attempts=3, base_delay=1.0)
    async def _step_plan_async(self, series_config: dict) -> dict[str, Any]:
        """Bible生成ステップ（リトライ対応）"""
        return self._step_plan(series_config)

    @staticmethod
    def _step_plan(series_config: dict) -> dict[str, Any]:
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
                    "Multi-platform support",
                ],
                # 連続性確保フラグや后续设置
                "continuity": {"enable": True, "plan": "standard"},
            }

            logger.info("Bible generation completed", extra={"bible": bible_data})
            return bible_data

        except Exception as e:
            logger.exception("Error in Bible generation")
            raise PipelineError(f"Bible generation failed: {e}") from e

    @async_retry(max_attempts=3, base_delay=1.0)
    async def _generate_content_async(
        self, bible: dict[str, Any], samples: list[dict[str, Any]], platforms: list[str]
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """コンテンツ生成ステップ（リトライ対応）"""
        return await self._generate_content(bible, samples, platforms)

    async def _generate_content(
        self, bible: dict[str, Any], samples: list[dict[str, Any]], platforms: list[str]
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        コンテンツ生成ステップ。

        Args:
            bible: Bibleデータ
            samples: 生成サンプル（使用しないがAPI互換性確保）
            platforms: 対象プラットフォーム

        Returns:
            tuple: (selected_items, exports_data)
        """
        selected: list[dict[str, Any]] = []
        exports: dict[str, Any] = {}

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
                    "previous_episode_summary": previous_episode_context["summary"]
                    if previous_episode_context
                    else None,
                    "previous_episode_text": previous_episode_context["text_excerpt"]
                    if previous_episode_context
                    else None,
                    "previous_killer_phrase": previous_episode_context["killer_phrase"]
                    if previous_episode_context
                    else None,
                    # WritingAgent が利用する想定のキー
                    "plot": {
                        "branch_id": 1,  # 将来的に取得可能
                        "ep_num": ep_num,
                    },
                    "script": "",  # 将来的に脚本データを投入
                    "target_word_count": bible.get("target_word_count_per_episode", 3000),
                    "continuation": True,  # 続き執筆フラグ
                    "build_platform": "streamlit_demo",
                }

                try:
                    # 修正1: book_id を動的に取得（book_id=0 ではなく実際の値）
                    # ただし、この例では book_id の取得ロジックが実装されていないため、一時的に 1 を使用
                    book_id = bible.get("book_id", 1)  # 修正1: bible_data から book_id を取得
                    result = await writer.write(
                        book_id=book_id,  # 修正1: ダミーbook_idから実際の値へ
                        ep_num=ep_num,
                        context=context,
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
                        exports[platform].append(
                            {
                                "ep_num": ep_num,
                                "title": context["title"],
                                "format": "web",
                                "target_word_count": context["target_word_count"],
                            }
                        )
                except Exception as e:
                    logger.warning(f"Episode {ep_num} generation failed: {e}")
                    raise PipelineError(f"Episode {ep_num} generation failed: {e}") from e

            logger.info(
                f"Content generation completed: {len(selected)} episodes generated",
                extra={"selected_episode_count": len(selected)},
            )
            return selected, exports
        except Exception as e:
            logger.exception("Error in content generation pipeline")
            raise PipelineError(f"Content generation failed: {e}") from e

    def _create_schedule_csv(self, exports: dict[str, Any]) -> str:
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
            csv_path = (
                self.csv_path
            )  # 修正2: ハードコードされたパスを使用せず、インスタンス変数を使用
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write(csv_content)

            logger.info("Schedule CSV created", extra={"path": csv_path})
            return csv_path

        except Exception as e:
            logger.exception("Failed to create schedule CSV")
            raise PipelineError(f"CSV creation failed: {e}") from e

    async def _publish_to_platforms(
        self,
        novel: dict[str, Any],
        episodes: list[dict[str, Any]],
        platforms: list[str],
        credentials: dict[str, PublisherCredentials] | None = None,
    ) -> dict[str, list[PublishResult]]:
        """
        指定プラットフォームへ投稿を実行する。

        Args:
            novel: 小説メタデータ
            episodes: エピソードリスト
            platforms: 対象プラットフォームリスト
            credentials: プラットフォーム別認証情報（Noneの場合はCredentialStoreから取得）

        Returns:
            プラットフォーム別投稿結果リスト
        """
        if credentials is None:
            credential_store = get_credential_store()
            credentials = {}
            for platform in platforms:
                credentials[platform] = credential_store.get(platform)

        results: dict[str, list[PublishResult]] = {}

        for platform in platforms:
            platform_creds = credentials.get(platform)
            if not platform_creds:
                logger.warning(f"認証情報なし、スキップ: {platform}")
                results[platform] = []
                continue

            try:
                publisher = get_publisher(platform)

                # 認証
                auth_success = await publisher.authenticate(platform_creds)
                if not auth_success:
                    logger.error(f"認証失敗: {platform}")
                    results[platform] = [
                        PublishResult(success=False, platform=platform, error="認証失敗")
                    ]
                    continue

                platform_results = []

                # 第1話が成功した後のpost_idを保持（第2話以降で使用）
                platform_post_id = None

                for episode in episodes:
                    try:
                        # 既存投稿IDがあるかチェック（更新の場合）
                        post_id = episode.get(f"{platform}_post_id") or platform_post_id

                        if post_id:
                            # 既存話の更新
                            result = await publisher.update_chapter(
                                post_id, episode, platform_creds
                            )
                        else:
                            # 新規投稿（第1話の場合はpublish、それ以外はupdate_chapter）
                            if episode.get("ep_num", 1) == 1:
                                result = await publisher.publish(novel, episode, platform_creds)
                            else:
                                # 第2話以降でpost_idがない場合は小説IDが必要
                                result = PublishResult(
                                    success=False,
                                    platform=platform,
                                    error=f"第{episode.get('ep_num')}話の投稿には小説ID(post_id)が必要です",
                                )

                        platform_results.append(result)

                        # 成功時はpost_idをepisodeに記録（次回更新用）
                        if result.success and result.post_id:
                            episode[f"{platform}_post_id"] = result.post_id
                            episode[f"{platform}_post_url"] = result.url
                            platform_post_id = result.post_id  # 共有用

                        # レート制限対策で少し待機
                        await publisher._apply_rate_limit()

                    except Exception as e:
                        logger.exception(
                            f"Episode {episode.get('ep_num')} publish failed on {platform}"
                        )
                        platform_results.append(
                            PublishResult(success=False, platform=platform, error=str(e))
                        )

                results[platform] = platform_results
                logger.info(
                    f"Platform {platform} publish completed: {len([r for r in platform_results if r.success])}/{len(platform_results)} success"
                )

            except Exception as e:
                logger.exception(f"Platform {platform} publish failed entirely")
                results[platform] = [
                    PublishResult(success=False, platform=platform, error=f"Platform error: {e}")
                ]

        return results

    async def run(
        self,
        series_config: dict,
        samples: list,
        platforms: list,
        credentials: dict[str, PublisherCredentials] | None = None,
        do_publish: bool = False,
    ) -> dict[str, Any]:
        """
        パイプラインのエントリーポイント。

        Args:
            series_config: シリーズ設定パラメータ
            samples: 生成サンプルリスト（実質的に使用しないが将来拡張可能）
            platforms: 対象プラットフォームリスト
            credentials: プラットフォーム別認証情報（Noneの場合はCredentialStoreから取得）
            do_publish: 実際に投稿を実行するかどうか

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

            # 4. 投稿実行（オプション）
            publish_results = {}
            if do_publish:
                # novelデータ構築
                novel_data = {
                    "title": bible.get("concept", "無題"),
                    "synopsis": bible.get("trend_analysis", ""),
                    "genre": bible.get("genre", "general"),
                    "tags": bible.get("keywords", []),
                    "is_adult": False,
                }
                publish_results = await self._publish_to_platforms(
                    novel=novel_data,
                    episodes=selected,
                    platforms=platforms,
                    credentials=credentials,
                )

            result = {
                "bible": bible,
                "selected": selected,
                "exports": exports,
                "schedule_csv": schedule_csv,
                "publish_results": publish_results,
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
                "schedule_csv": None,
                "publish_results": {},
            }
        except Exception as e:
            logger.exception("Unexpected error in CommercialPipeline.run")
            return {
                "error": str(e),
                "bible": None,
                "selected": [],
                "exports": {},
                "schedule_csv": None,
                "publish_results": {},
            }
