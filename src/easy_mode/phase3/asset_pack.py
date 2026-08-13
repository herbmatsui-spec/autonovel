"""
資産化パック生成
IFルート・メディアミックス・電子書籍を統合した配信用パッケージ生成
"""

from __future__ import annotations

import json
import logging
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from src.easy_mode.phase3.ebook_export import create_ebook_exporter
from src.easy_mode.phase3.if_routes import IFRouteGenerator, IFRouteGraph
from src.easy_mode.phase3.media_mix import (
    MediaFormat,
    create_media_mix_exporter,
)
from src.easy_mode.pipeline import SeriesResult

logger = logging.getLogger(__name__)


@dataclass
class AssetPackMetadata:
    """資産化パックメタデータ"""
    pack_id: str
    title: str
    genre: str
    version: str = "1.0.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source_series_id: str = ""
    episode_count: int = 0
    total_words: int = 0
    formats: Dict[str, Any] = field(default_factory=dict)  # 含まれるフォーマット
    if_routes: bool = False
    media_mix: List[str] = field(default_factory=list)
    ebook_formats: List[str] = field(default_factory=list)
    checksums: Dict[str, str] = field(default_factory=dict)
    manifest: Dict[str, str] = field(default_factory=dict)  # ファイルパス -> 説明
    licensing: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "title": self.title,
            "genre": self.genre,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source_series_id": self.source_series_id,
            "episode_count": self.episode_count,
            "total_words": self.total_words,
            "formats": self.formats,
            "if_routes": self.if_routes,
            "media_mix": self.media_mix,
            "ebook_formats": self.ebook_formats,
            "checksums": self.checksums,
            "manifest": self.manifest,
            "licensing": self.licensing
        }


class AssetPackGenerator:
    """資産化パック生成器"""

    def __init__(self, genre: str, preset: Dict[str, Any]):
        self.genre = genre
        self.preset = preset
        self.if_generator = None  # 遅延初期化
        self.media_exporter = None
        self.ebook_exporter = None

    def _init_components(self, series: SeriesResult):
        """コンポーネント初期化"""
        if self.if_generator is None:
            self.if_generator = IFRouteGenerator(self.genre, self.preset)
        if self.media_exporter is None:
            self.media_exporter = create_media_mix_exporter(self.genre, self.preset)
        if self.ebook_exporter is None:
            self.ebook_exporter = create_ebook_exporter(self.genre, self.preset)

    def generate_pack(
        self,
        series: SeriesResult,
        output_dir: Path,
        pack_id: str = None,
        include_if_routes: bool = True,
        include_media_mix: bool = True,
        include_ebook: bool = True,
        media_formats: List[str] = None,
        ebook_formats: List[str] = None,
        **kwargs
    ) -> Path:
        """資産化パック生成"""
        self._init_components(series)

        pack_id = pack_id or f"pack_{series.title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        pack_id = pack_id.replace(" ", "_").replace("/", "_")

        # 作業ディレクトリ
        work_dir = output_dir / f"asset_pack_{pack_id}"
        work_dir.mkdir(parents=True, exist_ok=True)

        # サブディレクトリ構造
        subdirs = {
            'original': work_dir / '01_original_novel',
            'if_routes': work_dir / '02_if_routes',
            'media_mix': work_dir / '03_media_mix',
            'ebook': work_dir / '04_ebook',
            'metadata': work_dir / '05_metadata',
            'promo': work_dir / '06_promotional'
        }

        for d in subdirs.values():
            d.mkdir(parents=True, exist_ok=True)

        metadata = AssetPackMetadata(
            pack_id=pack_id,
            title=series.title,
            genre=self.genre,
            source_series_id=getattr(series, 'id', ''),
            episode_count=len(series.episodes),
            total_words=sum(ep.word_count for ep in series.episodes),
            licensing=kwargs.get('licensing', {
                'type': 'CC BY-NC-SA 4.0',
                'commercial_use': False,
                'derivatives': True,
                'attribution': 'AI Novel Engine'
            })
        )

        # 1. オリジナル小説保存
        original_files = self._save_original_novel(series, subdirs['original'])
        metadata.manifest.update(original_files)
        metadata.formats['original'] = 'text/json'

        # 2. IFルート生成
        if include_if_routes:
            if_route_files = self._generate_if_routes(series, subdirs['if_routes'])
            metadata.manifest.update(if_route_files)
            metadata.if_routes = True
            metadata.formats['if_routes'] = 'application/json'

        # 3. メディアミックス生成
        if include_media_mix:
            media_files = self._generate_media_mix(
                series, subdirs['media_mix'], media_formats
            )
            metadata.manifest.update(media_files)
            metadata.media_mix = media_formats or ['manga', 'audio_drama', 'video']
            metadata.formats['media_mix'] = 'application/json'

        # 4. 電子書籍生成
        if include_ebook:
            ebook_files = self._generate_ebooks(
                series, subdirs['ebook'], ebook_formats, **kwargs
            )
            metadata.manifest.update(ebook_files)
            metadata.ebook_formats = ebook_formats or ['epub', 'pdf']
            metadata.formats['ebook'] = 'application/epub+zip'

        # 5. プロモーション素材生成
        promo_files = self._generate_promo_materials(series, subdirs['promo'])
        metadata.manifest.update(promo_files)

        # 6. メタデータ保存
        metadata.updated_at = datetime.now().isoformat()
        metadata_path = subdirs['metadata'] / 'pack_metadata.json'
        metadata_path.write_text(
            json.dumps(metadata.to_dict(), ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        metadata.manifest['pack_metadata.json'] = 'パックメタデータ'

        # 7. チェックサム計算
        metadata.checksums = self._calculate_checksums(work_dir)

        # メタデータ更新保存
        metadata_path.write_text(
            json.dumps(metadata.to_dict(), ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

        # 8. ZIP圧縮
        zip_path = output_dir / f"{pack_id}.zip"
        self._create_zip(work_dir, zip_path)

        # 作業ディレクトリ削除（オプション）
        if kwargs.get('clean_work_dir', True):
            shutil.rmtree(work_dir)

        logger.info(f"Asset pack generated: {zip_path}")
        return zip_path

    def _save_original_novel(self, series: SeriesResult, output_dir: Path) -> Dict[str, str]:
        """オリジナル小説保存"""
        files = {}

        # シリーズ全体JSON
        series_data = {
            'title': series.title,
            'genre': series.genre,
            'concept': series.concept,
            'total_episodes': series.total_episodes,
            'total_words': sum(ep.word_count for ep in series.episodes),
            'bible': series.bible,
            'plot_outline': series.plot_outline,
            'episodes': [
                {
                    'episode_num': ep.episode_num,
                    'title': ep.title,
                    'content': ep.content,
                    'word_count': ep.word_count,
                    'audit_score': ep.audit_score,
                    'audit_passed': ep.audit_passed,
                    'rewrite_count': ep.rewrite_count,
                    'spice_elements': [
                        {
                            'type': se.type,
                            'text': se.text,
                            'position': se.position,
                            'priority': se.priority,
                            'metadata': se.metadata
                        }
                        for se in ep.spice_elements
                    ],
                    'metadata': ep.metadata
                }
                for ep in series.episodes
            ],
            'metadata': series.metadata,
            'created_at': series.created_at.isoformat() if series.created_at else '',
            'status': series.status
        }

        series_path = output_dir / 'series_complete.json'
        series_path.write_text(
            json.dumps(series_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        files['series_complete.json'] = 'シリーズ完全データ'

        # 各話別テキスト
        for ep in series.episodes:
            ep_path = output_dir / f"ep{ep.episode_num:03d}_{ep.title}.txt"
            ep_content = f"{ep.title}\n\n{ep.content}\n\n--- \n文字数: {ep.word_count}\n監査スコア: {ep.audit_score}\n"
            ep_path.write_text(ep_content, encoding='utf-8')
            files[f'ep{ep.episode_num:03d}_{ep.title}.txt'] = f'第{ep.episode_num}話テキスト'

        # プロットアウトライン
        plot_path = output_dir / 'plot_outline.json'
        plot_path.write_text(
            json.dumps(series.plot_outline, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        files['plot_outline.json'] = 'プロットアウトライン'

        # Bible
        bible_path = output_dir / 'bible.json'
        bible_path.write_text(
            json.dumps(series.bible, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        files['bible.json'] = 'Bible（世界観設定）'

        return files

    def _generate_if_routes(self, series: SeriesResult, output_dir: Path) -> Dict[str, str]:
        """IFルート生成"""
        files = {}

        # IFルートグラフ生成
        graph = self.if_generator.generate_from_series(series)

        # グラフ全体JSON
        graph_data = {
            'entry_node_id': graph.entry_node_id,
            'metadata': graph.metadata,
            'nodes': {
                node_id: node.to_dict()
                for node_id, node in graph.nodes.items()
            }
        }

        graph_path = output_dir / 'if_route_graph.json'
        graph_path.write_text(
            json.dumps(graph_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        files['if_route_graph.json'] = 'IFルートグラフ（全ノード）'

        # 可視化用DOT
        dot_path = output_dir / 'if_route_graph.dot'
        dot_content = self._generate_dot_graph(graph)
        dot_path.write_text(dot_content, encoding='utf-8')
        files['if_route_graph.dot'] = 'Graphviz DOT形式グラフ'

        # ルート別シナリオ
        routes_path = output_dir / 'route_scenarios'
        routes_path.mkdir(exist_ok=True)

        # 主要ルート抽出
        main_routes = self._extract_main_routes(graph)
        for route_name, route_nodes in main_routes.items():
            route_file = routes_path / f'{route_name}.json'
            route_file.write_text(
                json.dumps({
                    'route_name': route_name,
                    'nodes': [n.to_dict() for n in route_nodes]
                }, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            files[f'route_scenarios/{route_name}.json'] = f'ルートシナリオ: {route_name}'

        # プレイヤー用セーブデータテンプレート
        save_template = {
            'version': '1.0',
            'graph_id': list(graph.nodes.keys())[0] if graph.nodes else '',
            'save_slots': [],
            'settings': {
                'auto_save': True,
                'show_unavailable': False
            }
        }
        save_path = output_dir / 'save_template.json'
        save_path.write_text(
            json.dumps(save_template, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        files['save_template.json'] = 'セーブデータテンプレート'

        return files

    def _generate_dot_graph(self, graph: IFRouteGraph) -> str:
        """Graphviz DOT形式生成"""
        lines = [
            'digraph IFRouteGraph {',
            '    rankdir=LR;',
            '    node [shape=box, style=filled, fontname="Noto Sans JP"];',
            '    edge [fontname="Noto Sans JP"];',
            ''
        ]

        # ノード定義
        for node_id, node in graph.nodes.items():
            # ノードタイプによる色分け
            colors = {
                'prologue': '#FFF3E0',
                'main': '#E3F2FD',
                'hidden': '#F3E5F5',
                'bad_end': '#FFEBEE',
                'merge': '#E8F5E9',
                'normal': '#F5F5F5'
            }

            route_type = node.metadata.get('route', 'normal')
            fillcolor = colors.get(route_type, colors['normal'])

            # ラベル作成
            label = f"{node_id}\\nEP{node.episode_num}\\n{node.branch_type.value}"
            if node.metadata.get('route'):
                label += f"\\n[{node.metadata['route']}]"

            lines.append(f'    "{node_id}" [label="{label}", fillcolor="{fillcolor}"];')

        lines.append('')

        # エッジ定義
        for node_id, node in graph.nodes.items():
            for choice in node.choices:
                if choice.target_node_id:
                    label = choice.text[:20] + ('...' if len(choice.text) > 20 else '')
                    lines.append(
                        f'    "{node_id}" -> "{choice.target_node_id}" [label="{label}"];'
                    )

        lines.append('}')
        return '\n'.join(lines)

    def _extract_main_routes(self, graph: IFRouteGraph) -> Dict[str, List]:
        """主要ルート抽出"""
        routes = {}

        # メインルート
        main_nodes = [n for n in graph.nodes.values() if n.metadata.get('route') == 'main']
        if main_nodes:
            routes['main_route'] = sorted(main_nodes, key=lambda n: n.episode_num)

        # 隠しルート
        hidden_nodes = [n for n in graph.nodes.values() if n.metadata.get('route') == 'hidden']
        if hidden_nodes:
            routes['hidden_route'] = sorted(hidden_nodes, key=lambda n: n.episode_num)

        # バッドエンドルート
        bad_nodes = [n for n in graph.nodes.values() if n.metadata.get('route') == 'bad_end']
        if bad_nodes:
            routes['bad_end_routes'] = sorted(bad_nodes, key=lambda n: n.episode_num)

        # 真エンド収束ルート
        merge_nodes = [n for n in graph.nodes.values() if n.branch_type.value == 'merge']
        if merge_nodes:
            routes['true_end_convergence'] = merge_nodes

        return routes

    def _generate_media_mix(
        self,
        series: SeriesResult,
        output_dir: Path,
        media_formats: List[str] = None
    ) -> Dict[str, str]:
        """メディアミックス生成"""
        files = {}

        if media_formats is None:
            media_formats = ['manga', 'audio_drama', 'video']

        format_enums = [MediaFormat(f) for f in media_formats if f in MediaFormat.__members__]

        for episode in series.episodes:
            ep_dir = output_dir / f'ep{episode.episode_num:03d}'
            ep_dir.mkdir(exist_ok=True)

            scripts = self.media_exporter.export_all(
                episode, series, format_enums
            )

            saved = self.media_exporter.save_all(scripts, ep_dir)

            for fmt, path in saved.items():
                rel_path = path.relative_to(output_dir)
                files[str(rel_path)] = f'第{episode.episode_num}話 {fmt.value}台本'

        # 統合インデックス
        index = {
            'series_title': series.title,
            'genre': self.genre,
            'total_episodes': len(series.episodes),
            'media_formats': media_formats,
            'episodes': {
                f'ep{ep.episode_num:03d}': {
                    'title': ep.title,
                    'scripts': list(media_formats)
                }
                for ep in series.episodes
            }
        }

        index_path = output_dir / 'media_mix_index.json'
        index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        files['media_mix_index.json'] = 'メディアミックス統合インデックス'

        return files

    def _generate_ebooks(
        self,
        series: SeriesResult,
        output_dir: Path,
        ebook_formats: List[str] = None,
        **kwargs
    ) -> Dict[str, str]:
        """電子書籍生成"""
        files = {}

        if ebook_formats is None:
            ebook_formats = ['epub', 'pdf']

        # カバー画像パス取得
        cover_path = kwargs.get('cover_image_path')
        if cover_path and not Path(cover_path).exists():
            cover_path = None
            logger.warning("Cover image not found, generating without cover")

        for fmt in ebook_formats:
            output_path = output_dir / f"{series.title}.{fmt}"
            try:
                if fmt == 'epub':
                    result = self.ebook_exporter.export_epub(
                        series, output_path,
                        cover_image_path=cover_path,
                        **kwargs
                    )
                elif fmt == 'pdf':
                    result = self.ebook_exporter.export_pdf(
                        series, output_path,
                        cover_image_path=cover_path,
                        **kwargs
                    )
                elif fmt == 'mobi':
                    result = self.ebook_exporter.export_mobi(
                        series, output_path,
                        cover_image_path=cover_path,
                        **kwargs
                    )
                else:
                    logger.warning(f"Unknown ebook format: {fmt}")
                    continue

                files[f'{series.title}.{fmt}'] = f'{fmt.upper()}形式電子書籍'

            except Exception as e:
                logger.error(f"Failed to generate {fmt}: {e}")

        return files

    def _generate_promo_materials(self, series: SeriesResult, output_dir: Path) -> Dict[str, str]:
        """プロモーション素材生成"""
        files = {}

        # あらすじ（長・短）
        synopsis_long = self._generate_synopsis(series, long=True)
        synopsis_short = self._generate_synopsis(series, long=False)

        (output_dir / 'synopsis_long.txt').write_text(synopsis_long, encoding='utf-8')
        files['synopsis_long.txt'] = '詳細あらすじ'

        (output_dir / 'synopsis_short.txt').write_text(synopsis_short, encoding='utf-8')
        files['synopsis_short.txt'] = '短縮あらすじ'

        # キャッチコピー
        catchphrases = self._generate_catchphrases(series)
        (output_dir / 'catchphrases.txt').write_text(
            '\n'.join(catchphrases), encoding='utf-8'
        )
        files['catchphrases.txt'] = 'キャッチコピー集'

        # キャラクター紹介
        char_intro = self._generate_character_intros(series)
        (output_dir / 'character_introductions.txt').write_text(
            char_intro, encoding='utf-8'
        )
        files['character_introductions.txt'] = 'キャラクター紹介'

        # キーワード・タグ
        keywords = self._generate_keywords(series)
        (output_dir / 'keywords.txt').write_text(
            ', '.join(keywords), encoding='utf-8'
        )
        files['keywords.txt'] = '検索キーワード・タグ'

        # SNS用投稿文
        sns_posts = self._generate_sns_posts(series)
        (output_dir / 'sns_posts.json').write_text(
            json.dumps(sns_posts, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        files['sns_posts.json'] = 'SNS投稿文テンプレート'

        # プレスリリース風
        press = self._generate_press_release(series)
        (output_dir / 'press_release.txt').write_text(press, encoding='utf-8')
        files['press_release.txt'] = 'プレスリリース風紹介文'

        return files

    def _generate_synopsis(self, series: SeriesResult, long: bool = True) -> str:
        """あらすじ生成"""
        lines = []
        lines.append(f"【{series.title}】")
        lines.append("")
        lines.append(f"ジャンル: {series.genre}")
        lines.append(f"全{series.total_episodes}話・約{sum(ep.word_count for ep in series.episodes):,}字")
        lines.append("")

        if long:
            # 詳細版
            lines.append("【あらすじ】")
            if series.concept:
                lines.append(series.concept)
            lines.append("")

            if series.bible.get('protagonist'):
                lines.append(f"主人公: {series.bible['protagonist']}")
            if series.bible.get('cheat_ability'):
                lines.append(f"チート能力: {series.bible['cheat_ability']}")
            if series.bible.get('catharsis_target'):
                lines.append(f"カタルシス対象: {series.bible['catharsis_target']}")
            lines.append("")

            lines.append("【見所】")
            for ep in series.episodes[:3]:
                lines.append(f"第{ep.episode_num}話「{ep.title}」: {ep.content[:100]}...")
            lines.append("...")
        else:
            # 短縮版
            hook = series.metadata.get('synopsis', {}).get('hook', '')
            if hook:
                lines.append(hook)
            else:
                lines.append(series.concept[:200] if series.concept else '')

        return '\n'.join(lines)

    def _generate_catchphrases(self, series: SeriesResult) -> List[str]:
        """キャッチコピー生成"""
        base = self.preset.get('marketing', {}).get('catchphrase_templates', [])

        phrases = []
        for template in base[:5]:
            phrase = template.replace('{title}', series.title)
            phrase = phrase.replace('{genre}', self.genre)
            phrase = phrase.replace('{protagonist}', series.bible.get('protagonist', '主人公'))
            phrase = phrase.replace('{cheat}', series.bible.get('cheat_ability', 'チート'))
            phrases.append(phrase)

        # ジャンル別追加
        genre_phrases = {
            'zarma': [
                f"「{series.title}」——追放された最強が、裏切り者を完全制圧する！",
                "無双×ざまぁの究極カタルシス、ここに極まる。"
            ],
            'aku_reijo': [
                f"「{series.title}」——断罪フラグをへし折れ！隠しルートで溺愛エンドへ。",
                "悪役令嬢の知略と百合の輝き、新たな歴史が始まる。"
            ],
            'cheat_tensei': [
                f"「{series.title}」——転生即チート、秒殺無双の爽快感！",
                "効率厨ゲーマーの夢、ここに実現。"
            ],
            'slow_life': [
                f"「{series.title}」——前世は社畜、今は異世界スローライフ。",
                "戦わない最強、癒やしの極致。"
            ],
            'loop': [
                f"「{series.title}」——{100}回死んで、やっと真エンド。",
                "確率0を1にする、完全攻略の物語。"
            ]
        }

        if self.genre in genre_phrases:
            phrases.extend(genre_phrases[self.genre])

        return phrases

    def _generate_character_intros(self, series: SeriesResult) -> str:
        """キャラクター紹介生成"""
        lines = [f"【{series.title} キャラクター紹介】", ""]

        archetypes = series.bible.get('characters', {}).get('archetypes', {})

        for name, data in archetypes.items():
            pattern = data.get('name_pattern', name)
            role = data.get('role', '')
            desc = data.get('description', '')
            speech = data.get('speech_patterns', {})

            lines.append(f"◆ {pattern}")
            if role:
                lines.append(f"  役割: {role}")
            if desc:
                lines.append(f"  概要: {desc}")
            if speech.get('first_person'):
                lines.append(f"  一人称: {speech['first_person']}")
            if speech.get('tone'):
                lines.append(f"  口調: {speech['tone']}")
            lines.append("")

        return '\n'.join(lines)

    def _generate_keywords(self, series: SeriesResult) -> List[str]:
        """キーワード生成"""
        keywords = [
            series.title,
            self.genre,
            'Web小説',
            'AI生成',
            '完結済み',
            f'{series.total_episodes}話完結',
            f'{sum(ep.word_count for ep in series.episodes)//10000}万字',
        ]

        # ジャンル別キーワード
        genre_kw = {
            'zarma': ['ざまぁ', '追放', '無双', 'カタルシス', '裏切り', '復讐'],
            'aku_reijo': ['悪役令嬢', '断罪回避', '隠しルート', '百合', '乙女ゲーム'],
            'cheat_tensei': ['チート転生', '最強', 'スキル無限', '秒殺', '効率厨'],
            'slow_life': ['スローライフ', 'ほのぼの', '異世界料理', '農業', '癒やし'],
            'dungeon_admin': ['ダンジョン運営', '経営', 'モンスター', 'ギミック', 'タワーディフェンス'],
            'modern_cheat': ['現代チート', '都市伝説', '管理者権限', 'バグ', '実体化'],
            'ts_tensei': ['TS転生', '性別反転', '百合', '美少女', 'ハーレム'],
            'vrmmo': ['VRMMO', 'フルダイブ', '実体化', '配信者', 'ソロ攻略'],
            'loop': ['ループ', '時間逆行', '真エンド', '完全攻略', '周回プレイ']
        }

        if self.genre in genre_kw:
            keywords.extend(genre_kw[self.genre])

        # 主人公・チート関連
        if series.bible.get('protagonist'):
            keywords.append(f"主人公:{series.bible['protagonist']}")
        if series.bible.get('cheat_ability'):
            keywords.append(f"能力:{series.bible['cheat_ability']}")

        return keywords[:50]  # 最大50個

    def _generate_sns_posts(self, series: SeriesResult) -> Dict[str, Any]:
        """SNS投稿文生成"""
        return {
            'twitter': [
                f"【新刊】「{series.title}」全{series.total_episodes}話完結！{self.genre}ジャンルの決定版。{series.concept[:100]}... #Web小説 #AI生成 #完結済み",
                f"「{series.title}」の見所：{series.bible.get('protagonist', '主人公')}が{series.bible.get('cheat_ability', 'チート能力')}で無双！カタルシス度MAX！ #新刊"
            ],
            'pixiv': [
                f"「{series.title}」全話公開中！\nジャンル: {self.genre}\n全{series.total_episodes}話・約{sum(ep.word_count for ep in series.episodes):,}字\n\n{series.concept[:200]}..."
            ],
            'note': [
                f"「{series.title}」制作裏話\n\nAI Novel Engineを使って{self.genre}ジャンルの小説を自動生成しました。\nBible設定からプロット、本文、監査まで全自動。\nSpiceGuardで「尖り」を守りながらリライト..."
            ]
        }

    def _generate_press_release(self, series: SeriesResult) -> str:
        """プレスリリース風生成"""
        return f"""
========================================
【プレスリリース】
========================================

AI Novel Engine、新作Web小説「{series.title}」を自動生成完了
〜{self.genre}ジャンル・全{series.total_episodes}話・約{sum(ep.word_count for ep in series.episodes):,}字〜

令和{datetime.now().year}年{datetime.now().month}月{datetime.now().day}日
AI Novel Engine 開発チーム

AIを活用した小説自動生成システム「AI Novel Engine v3.0」において、
新作Web小説「{series.title}」の全自動生成が完了しました。

【作品概要】
タイトル: {series.title}
ジャンル: {self.genre}
話数: 全{series.total_episodes}話
総文字数: 約{sum(ep.word_count for ep in series.episodes):,}字
生成方式: 全自動（企画・プロット・本文・監査・リライト）

【コンセプト】
{series.concept}

【特徴】
1. ジャンル選択のみで企画から完結まで全自動生成
2. SpiceGuard技術により、自動リライト時も「尖り（独自比喩・キャラ声・伏線等）」を保護
3. 監査スコア95点以上を目標とした品質保証（最大3回リライト）
4. IFルート分岐・メディアミックス・電子書籍まで一括出力可能

【ジャンル別特徴】
{self._get_genre_feature_text()}

【今後の展開】
- 漫画・音声ドラマ・動画用台本の自動生成（メディアミックス）
- EPUB/PDF/MOBI形式での電子書籍出力
- IFルート分岐によるインタラクティブノベル展開
- 多言語翻訳対応

【お問い合わせ】
AI Novel Engine 開発チーム
Email: ai-novel-engine@example.com

以上
"""

    def _get_genre_feature_text(self) -> str:
        features = {
            'zarma': '- 追放・無双・ざまぁの王道カタルシスを自動構築\n- 段階的ストレス蓄積と爆発的カタルシスの波を数理モデル化',
            'aku_reijo': '- 断罪フラグ回避と隠しルート攻略をゲーム的ロジックで実装\n- 百合テンション管理による溺愛ルート自動生成',
            'cheat_tensei': '- スキル習得∞・秒殺・最適解の爽快感を数値化\n- 効率厨ゲーマー視点の「最適解」探索アルゴリズム',
            'slow_life': '- 五感描写特化の感覚豊かな文章生成\n- バトルなしでもカタルシスを生む日常の積み重ね設計',
            'dungeon_admin': '- ギミック・モンスター個性の組み合わせ爆発を管理\n- 忠誠・進化・命名など経営シミュレーション的要素',
            'modern_cheat': '- 管理者権限メタファーによる現代チート表現\n- 現金化・実体化・同期など現実干渉のバリエーション',
            'ts_tensei': '- 性別ユーフォリアと百合親密度の二軸管理\n- 可愛い・美少女・永遠のキーワード自動挿入',
            'vrmmo': '- フルダイブ・同期・実体化の三段階リアリティ\n- 配信者視点とゲーム=現実統合の演出',
            'loop': '- ループカウント・データ蓄積・最適解探索の三要素\n- 確率0を1にする収束アルゴリズム'
        }
        return features.get(self.genre, '- ジャンル特化の自動生成パイプライン')

    def _calculate_checksums(self, directory: Path) -> Dict[str, str]:
        """チェックサム計算"""
        import hashlib

        checksums = {}
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                rel_path = file_path.relative_to(directory)
                with open(file_path, 'rb') as f:
                    checksums[str(rel_path)] = hashlib.sha256(f.read()).hexdigest()[:16]
        return checksums

    def _create_zip(self, source_dir: Path, zip_path: Path) -> None:
        """ZIP圧縮"""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zf.write(file_path, arcname)

        logger.info(f"Created zip: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB)")


def create_asset_pack_generator(genre: str, preset: Dict[str, Any]) -> AssetPackGenerator:
    """資産化パック生成器作成"""
    return AssetPackGenerator(genre, preset)
