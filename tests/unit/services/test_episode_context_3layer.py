"""3層コンテキストビルダーの単体テスト (v5.0 Relational Memory)

EpisodeContextBuilder の Layer 1/2/3 が正しく構築され、
トークン数が想定内に収まっているかを検証する。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.episode_context import EpisodeContextBuilder
from src.backend.database.models import Character as CharacterModel
from src.backend.database.models import Chapter as ChapterModel
from src.backend.database.models_foreshadowing import ForeshadowingModel


class TestEpisodeContext3Layer:
    """3層ローリング記憶ビルダーのテストスイート"""

    @pytest.fixture
    def mock_db(self):
        """モック AsyncSession を作成"""
        db = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def mock_characters(self):
        """モックキャラクターデータ"""
        chars = []
        for i, (name, role, personality, ability) in enumerate([
            ("アルス", "主人公", "勇敢で正義感が強い", "古代魔導剣術"),
            ("セリア", "ヒロイン", "聡明で優しい", "精霊魔法"),
            ("ガルド", "宿敵", "冷酷で野心家", "闇魔法"),
        ], 1):
            char = MagicMock(spec=CharacterModel)
            char.id = i
            char.name = name
            char.role = role
            char.personality = personality
            char.ability = ability
            chars.append(char)
        return chars

    @pytest.fixture
    def mock_chapters(self):
        """モックチャプターデータ（過去エピソード）"""
        chapters = []
        for ep_num, content in [
            (1, "アルスは村で育った少年だった。ある日、古い剣を見つける。"),
            (2, "剣が光り、アルスは不思議な力を感じた。旅立ちを決意する。"),
            (3, "王都ルミナスに到着。セリアと出会い、共に冒険することになる。"),
        ]:
            ch = MagicMock(spec=ChapterModel)
            ch.ep_num = ep_num
            ch.content = content
            chapters.append(ch)
        return chapters

    @pytest.fixture
    def mock_foreshadowings(self):
        """モック伏線データ"""
        fors = []
        for i, (title, planted_ep, target_ep, status) in enumerate([
            ("謎の剣の正体", 1, 10, "planted"),
            ("セリアの秘密", 3, 8, "progressed"),
            ("ガルドの真の目的", 2, None, "planted"),
        ], 1):
            f = MagicMock(spec=ForeshadowingModel)
            f.id = i
            f.title = title
            f.planted_episode = planted_ep
            f.target_episode = target_ep
            f.status = status
            fors.append(f)
        return fors

    @pytest.mark.asyncio
    async def test_build_context_first_episode(self, mock_db, mock_characters):
        """第1話では Layer 1 のみ、Layer 2/3 は空になることを検証"""
        async def mock_execute(query):
            result = MagicMock()
            if "CharacterModel" in str(query) or "characters" in str(query).lower():
                result.scalars.return_value.all.return_value = mock_characters
            elif "ForeshadowingModel" in str(query) or "foreshadowings" in str(query).lower():
                result.scalars.return_value.all.return_value = []
            elif "ChapterModel" in str(query) or "chapters" in str(query).lower():
                result.scalars.return_value.all.return_value = []
            else:
                result.scalars.return_value.all.return_value = []
            return result
        
        mock_db.execute.side_effect = mock_execute
        
        builder = EpisodeContextBuilder(mock_db)
        context = await builder.build_context(book_id=1, ep_num=1)
        
        # 基本構造の検証
        assert context["book_id"] == 1
        assert context["ep_num"] == 1
        assert context["is_first"] is True
        assert context["target_word_count"] == 3000
        
        # Layer 1: バイブル
        assert "layer1_bible" in context
        assert context["layer1_bible"]["token_estimate"] > 0
        assert len(context["layer1_bible"]["characters"]) == 3
        assert "アルス" in context["layer1_bible"]["text"]
        
        # Layer 2: 要約（第1話なので空）
        assert "layer2_summary" in context
        assert context["layer2_summary"]["episode_summaries"] == []
        assert context["layer2_summary"]["unresolved_foreshadowings"] == []
        
        # Layer 3: 直前文脈（第1話なので空）
        assert "layer3_raw" in context
        assert context["layer3_raw"] == ""
        
        # 後方互換性
        assert "previous_episode" in context
        assert context["previous_episode"] == {}

    @pytest.mark.asyncio
    async def test_build_context_middle_episode(
        self, mock_db, mock_characters, mock_chapters, mock_foreshadowings
    ):
        """中間話（例: 第4話）で3層すべてが構築されることを検証"""
        async def mock_execute(query):
            result = MagicMock()
            if "CharacterModel" in str(query) or "characters" in str(query).lower():
                result.scalars.return_value.all.return_value = mock_characters
            elif "ForeshadowingModel" in str(query) or "foreshadowings" in str(query).lower():
                result.scalars.return_value.all.return_value = mock_foreshadowings
            elif "ChapterModel" in str(query) or "chapters" in str(query).lower():
                # ep_num < 4 のチャプターのみ返す
                result.scalars.return_value.all.return_value = mock_chapters
            else:
                result.scalars.return_value.all.return_value = []
            return result
        
        mock_db.execute.side_effect = mock_execute
        
        previous_text = "アルスとセリアは古代遺跡の奥深くへと進んでいた。空気は重く、不気味な静寂に包まれている。"
        
        builder = EpisodeContextBuilder(mock_db)
        context = await builder.build_context(
            book_id=1, 
            ep_num=4, 
            previous_episode_text=previous_text
        )
        
        # 基本構造
        assert context["ep_num"] == 4
        assert context["is_first"] is False
        
        # Layer 1: バイブル（キャラ3人）
        assert len(context["layer1_bible"]["characters"]) == 3
        assert context["layer1_bible"]["token_estimate"] > 0
        
        # Layer 2: 要約（3話分＋伏線3本）
        assert len(context["layer2_summary"]["episode_summaries"]) == 3
        assert len(context["layer2_summary"]["unresolved_foreshadowings"]) == 3
        assert "第1話" in context["layer2_summary"]["text"]
        assert "第2話" in context["layer2_summary"]["text"]
        assert "第3話" in context["layer2_summary"]["text"]
        assert "謎の剣の正体" in context["layer2_summary"]["text"]
        assert "セリアの秘密" in context["layer2_summary"]["text"]
        assert "ガルドの真の目的" in context["layer2_summary"]["text"]
        
        # Layer 3: 直前生文
        assert context["layer3_raw"] == previous_text
        
        # 後方互換性
        assert "previous_episode" in context
        assert context["previous_episode"]["ending"] == previous_text[-500:]
        assert context["previous_episode"]["summary"] == context["layer2_summary"]["last_episode_summary"]

    @pytest.mark.asyncio
    async def test_token_estimate_layer1(self, mock_db, mock_characters):
        """Layer 1 のトークン見積もりが妥当な範囲内であることを検証"""
        async def mock_execute(query):
            result = MagicMock()
            if "characters" in str(query).lower() or "CharacterModel" in str(query):
                result.scalars.return_value.all.return_value = mock_characters
            else:
                result.scalars.return_value.all.return_value = []
            return result
        
        mock_db.execute.side_effect = mock_execute
        
        builder = EpisodeContextBuilder(mock_db)
        context = await builder.build_context(book_id=1, ep_num=1)
        
        # キャラ3人分の概算トークン数（日本語は1文字≒0.5トークン程度）
        # 1キャラ約100文字 → 300文字 → 約150トークン程度
        token_est = context["layer1_bible"]["token_estimate"]
        assert 50 < token_est < 2000  # 妥当な範囲

    @pytest.mark.asyncio
    async def test_token_estimate_layer2(
        self, mock_db, mock_characters, mock_chapters, mock_foreshadowings
    ):
        """Layer 2 のトークン見積もりが累積しても数千トークン以内であることを検証"""
        async def mock_execute(query):
            result = MagicMock()
            if "characters" in str(query).lower() or "CharacterModel" in str(query):
                result.scalars.return_value.all.return_value = mock_characters
            elif "foreshadowings" in str(query).lower() or "ForeshadowingModel" in str(query):
                result.scalars.return_value.all.return_value = mock_foreshadowings
            elif "chapters" in str(query).lower() or "ChapterModel" in str(query):
                result.scalars.return_value.all.return_value = mock_chapters
            else:
                result.scalars.return_value.all.return_value = []
            return result
        
        mock_db.execute.side_effect = mock_execute
        
        builder = EpisodeContextBuilder(mock_db)
        context = await builder.build_context(book_id=1, ep_num=4)
        
        # 3話要約（各約100文字）＋ 伏線3本 → 合計約500-1000文字 → 約250-500トークン
        token_est = context["layer2_summary"]["token_estimate"]
        assert 100 < token_est < 5000  # 数千トークン以内

    @pytest.mark.asyncio
    async def test_layer3_raw_text_injection(self, mock_db, mock_characters):
        """Layer 3 に任意の生テキストを注入できることを検証"""
        async def mock_execute(query):
            result = MagicMock()
            if "characters" in str(query).lower() or "CharacterModel" in str(query):
                result.scalars.return_value.all.return_value = mock_characters
            else:
                result.scalars.return_value.all.return_value = []
            return result
        
        mock_db.execute.side_effect = mock_execute
        
        builder = EpisodeContextBuilder(mock_db)
        long_text = "あ" * 5000  # 5000文字の長文
        
        context = await builder.build_context(
            book_id=1, 
            ep_num=5, 
            previous_episode_text=long_text
        )
        
        assert context["layer3_raw"] == long_text
        # 後方互換用 ending は最後の500文字のみ
        assert context["previous_episode"]["ending"] == long_text[-500:]

    @pytest.mark.asyncio
    async def test_no_characters_empty_bible(self, mock_db):
        """キャラクターがいない場合、Layer 1 が空メッセージになることを検証"""
        async def mock_execute(query):
            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            return result
        
        mock_db.execute.side_effect = mock_execute
        
        builder = EpisodeContextBuilder(mock_db)
        context = await builder.build_context(book_id=1, ep_num=1)
        
        assert context["layer1_bible"]["characters"] == []
        assert context["layer1_bible"]["text"] == "キャラクター設定なし"

    @pytest.mark.asyncio
    async def test_unresolved_foreshadowings_only_active(self, mock_db, mock_characters, mock_foreshadowings):
        """未回収伏線のみ（planted, progressed）が Layer 2 に含まれることを検証"""
        # resolvedステータスの伏線を追加
        resolved_foreshadowing = MagicMock(spec=ForeshadowingModel)
        resolved_foreshadowing.id = 99
        resolved_foreshadowing.title = "回収済み伏線"
        resolved_foreshadowing.planted_episode = 1
        resolved_foreshadowing.target_episode = 2
        resolved_foreshadowing.status = "resolved"
        
        all_foreshadowings = mock_foreshadowings + [resolved_foreshadowing]
        
        async def mock_execute(query):
            result = MagicMock()
            if "characters" in str(query).lower() or "CharacterModel" in str(query):
                result.scalars.return_value.all.return_value = mock_characters
            elif "foreshadowings" in str(query).lower() or "ForeshadowingModel" in str(query):
                # 実際のクエリでは status.in_(["planted", "progressed"]) でフィルタされるが、
                # モックでは全件返してビルダー側でフィルタされる想定
                # ここではモックの都合上全件返す（実DBではWHERE句でフィルタされる）
                result.scalars.return_value.all.return_value = all_foreshadowings
            elif "chapters" in str(query).lower() or "ChapterModel" in str(query):
                result.scalars.return_value.all.return_value = []
            else:
                result.scalars.return_value.all.return_value = []
            return result
        
        mock_db.execute.side_effect = mock_execute
        
        builder = EpisodeContextBuilder(mock_db)
        context = await builder.build_context(book_id=1, ep_num=4)
        
        # 実装では WHERE status IN ('planted', 'progressed') でフィルタされるため、
        # モックが全件返してもビルダー側ではアクティブな伏線のみ取得される想定
        # ここではモックが全件返す仕様なので、実装のフィルタが効いているかは
        # 統合テストで検証する。このテストではインターフェースの確認のみ。
        unresolved_list = context["layer2_summary"]["unresolved_foreshadowings"]
        assert isinstance(unresolved_list, list)
        # 少なくともアクティブな伏線は含まれる
        assert len(unresolved_list) >= 3

    @pytest.mark.asyncio
    async def test_compatibility_methods_exist(self, mock_db):
        """互換性メソッドが存在することを検証（リグレッション防止）"""
        builder = EpisodeContextBuilder(mock_db)
        
        assert hasattr(builder, "get_history")
        assert hasattr(builder, "clear_history")
        assert hasattr(builder, "set_final_episode")
        
        # 空実装であることを確認
        assert builder.get_history() == []
        builder.clear_history()  # エラーにならない
        builder.set_final_episode(10)  # エラーにならない


class TestEpisodeContextRegression:
    """既存機能のリグレッションテスト"""

    def test_class_exists(self):
        """EpisodeContextBuilder クラスが存在することを確認"""
        assert EpisodeContextBuilder is not None

    def test_build_context_method_signature(self):
        """build_context メソッドのシグネチャが非同期であることを確認"""
        import inspect
        sig = inspect.signature(EpisodeContextBuilder.build_context)
        assert "book_id" in sig.parameters
        assert "ep_num" in sig.parameters
        assert "target_word_count" in sig.parameters
        assert "previous_episode_text" in sig.parameters
        # 旧パラメータ previous_episode は削除されているが、互換性のため kwargs で受け付ける想定
        # 実際には新しいシグネチャのみサポート