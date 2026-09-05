import pytest
from src.services.pipeline_base import WorkflowContext
from src.models.foreshadowing import Foreshadowing
from src.models.hook import Hook
from src.models.illustration_point import IllustrationPoint


def test_workflow_context_foreshadowings_default():
    """WorkflowContext の foreshadowings フィールドが空リストで初期化されることを確認"""
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000
    )
    
    assert ctx.foreshadowings == []
    assert isinstance(ctx.foreshadowings, list)


def test_workflow_context_foreshadowings_can_be_set():
    """WorkflowContext の foreshadowings フィールドに値を設定できることを確認"""
    fs1 = Foreshadowing(
        id="F-001",
        content="主人公の秘密",
        hang_volume=1,
        hang_episode=2,
        hang_chapter=3,
        hang_type="implicit",
        importance="★★"
    )
    
    fs2 = Foreshadowing(
        id="F-002",
        content="古い遺跡",
        hang_volume=1,
        hang_episode=5,
        hang_chapter=2,
        hang_type="explicit",
        importance="★★★",
        resolution_volume=3,
        resolution_episode=1
    )
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        foreshadowings=[fs1, fs2]
    )
    
    assert len(ctx.foreshadowings) == 2
    assert ctx.foreshadowings[0] == fs1
    assert ctx.foreshadowings[1] == fs2
    assert ctx.foreshadowings[0].id == "F-001"
    assert ctx.foreshadowings[1].id == "F-002"


def test_workflow_context_foreshadowings_append():
    """WorkflowContext の foreshadowings フィールドに追加できることを確認"""
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000
    )
    
    # 初期状態では空
    assert ctx.foreshadowings == []
    
    # 項目を追加
    fs = Foreshadowing(
        id="F-003",
        content="転移の鍵",
        hang_volume=2,
        hang_episode=1,
        hang_chapter=5,
        hang_type="reader_task",
        importance="★"
    )
    
    ctx.foreshadowings.append(fs)
    
    assert len(ctx.foreshadowings) == 1
    assert ctx.foreshadowings[0] == fs
    assert ctx.foreshadowings[0].id == "F-003"
    assert ctx.foreshadowings[0].content == "転移の鍵"


def test_workflow_context_hook_fields_default():
    """WorkflowContext のフック関連フィールドがデフォルト値で初期化されることを確認"""
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000
    )
    
    # hooks フィールドが空リストで初期化されることを確認
    assert ctx.hooks == []
    assert isinstance(ctx.hooks, list)
    
    # hook_generation_index フィールドが 0 で初期化されることを確認
    assert ctx.hook_generation_index == 0
    
    # current_volume フィールドが 1 で初期化されることを確認
    assert ctx.current_volume == 1
    
    # current_episode フィールドが 0 で初期化されることを確認
    assert ctx.current_episode == 0


def test_workflow_context_hook_fields_can_be_set():
    """WorkflowContext のフック関連フィールドに値を設定できることを確認"""
    hook1 = Hook(
        id="H-001",
        type="mystery",
        content="謎のフック",
        target_position="episode_end",
        volume=1,
        episode=3,
        chapter=5
    )
    
    hook2 = Hook(
        id="H-002",
        type="threat",
        content="脅威のフック",
        target_position="volume_end",
        volume=2,
        episode=1,
        chapter=1
    )
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        hooks=[hook1, hook2],
        hook_generation_index=5,
        current_volume=3,
        current_episode=7
    )
    
    assert len(ctx.hooks) == 2
    assert ctx.hooks[0] == hook1
    assert ctx.hooks[1] == hook2
    assert ctx.hooks[0].id == "H-001"
    assert ctx.hooks[1].id == "H-002"
    assert ctx.hook_generation_index == 5
    assert ctx.current_volume == 3
    assert ctx.current_episode == 7


def test_workflow_context_hook_fields_append():
    """WorkflowContext のフック関連フィールドに追加できることを確認"""
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000
    )
    
    # 初期状態では空
    assert ctx.hooks == []
    assert ctx.hook_generation_index == 0
    assert ctx.current_volume == 1
    assert ctx.current_episode == 0
    
    # フックを追加
    hook = Hook(
        id="H-003",
        type="emotion",
        content="感情のフック",
        target_position="episode_end",
        volume=1,
        episode=5,
        chapter=3
    )
    
    ctx.hooks.append(hook)
    
    assert len(ctx.hooks) == 1
    assert ctx.hooks[0] == hook
    assert ctx.hooks[0].id == "H-003"
    assert ctx.hooks[0].content == "感情のフック"
    
    # インデックスをインクリメント
    ctx.hook_generation_index += 1
    assert ctx.hook_generation_index == 1
    
    # 巻数・話数を更新
    ctx.current_volume = 2
    ctx.current_episode = 10
    assert ctx.current_volume == 2
    assert ctx.current_episode == 10


def test_workflow_context_illustration_points_default():
    """WorkflowContext の illustration_points フィールドが空リストで初期化されることを確認"""
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000
    )
    
    assert ctx.illustration_points == []
    assert isinstance(ctx.illustration_points, list)


def test_workflow_context_illustration_points_can_be_set():
    """WorkflowContext の illustration_points フィールドに値を設定できることを確認"""
    ip1 = IllustrationPoint(
        id="IP-001",
        page="口絵1",
        scene_description="主人公とヒロインが夕焼け背景に背中合わせ",
        composition="主人公が左、ヒロインが右、二人の間に距離がある",
        props="主人公の剣とヒロインの杖を交差",
        expressions={"主人公": "決意した表情", "ヒロイン": "不安と信頼の混じった表情"},
        background="夕焼けに染まる荒野、廃城の尖塔"
    )
    
    ip2 = IllustrationPoint(
        id="IP-002",
        page="15",
        scene_description="主人公が雑魚敵を一刀両断",
        composition="主人公が中央に立ち、敵が左右に散らばる",
        props="主人公の刀に残像",
        expressions={"主人公": "余裕綽々だが目に死の気配"},
        background="暗い洞窟、壁に苔が生えている",
        notes="このシーンは第1章のクライマックス"
    )
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        illustration_points=[ip1, ip2]
    )
    
    assert len(ctx.illustration_points) == 2
    assert ctx.illustration_points[0] == ip1
    assert ctx.illustration_points[1] == ip2
    assert ctx.illustration_points[0].id == "IP-001"
    assert ctx.illustration_points[1].id == "IP-002"


def test_workflow_context_illustration_points_append():
    """WorkflowContext の illustration_points フィールドに追加できることを確認"""
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000
    )
    
    # 初期状態では空
    assert ctx.illustration_points == []
    
    # 項目を追加
    ip = IllustrationPoint(
        id="IP-003",
        page="口絵2",
        scene_description="二人が手をつなぎ歩く",
        composition="二人が画面中央からやや左に位置",
        props="なし",
        expressions={"ヒロイン": "幸せそうな笑顔"},
        background="桜並びの道、花びらが舞っている",
        notes="エンディングを彷彿とさせるシーン"
    )
    
    ctx.illustration_points.append(ip)
    
    assert len(ctx.illustration_points) == 1
    assert ctx.illustration_points[0] == ip
    assert ctx.illustration_points[0].id == "IP-003"
    assert ctx.illustration_points[0].scene_description == "二人が手をつなぎ歩く"


def test_workflow_context_all_fields_together():
    """すべてのフィールドが同時に機能することを確認"""
    # フォアショドウイング
    fs = Foreshadowing(
        id="F-001",
        content="古い約束",
        hang_volume=1,
        hang_episode=3,
        hang_chapter=5,
        hang_type="implicit",
        importance="★★"
    )
    
    # フック
    hook = Hook(
        id="H-001",
        type="mystery",
        content="なぜ、彼女は俺の名を知っていたのか──",
        target_position="episode_end",
        volume=1,
        episode=3,
        chapter=5
    )
    
    # 挿絵ポイント
    ip = IllustrationPoint(
        id="IP-001",
        page="口絵1",
        scene_description="主人公とヒロインが夕焼け背景に背中合わせ",
        composition="主人公が左、ヒロインが右、二人の間に距離がある",
        props="主人公の剣とヒロインの杖を交差",
        expressions={"主人公": "決意した表情", "ヒロイン": "不安と信頼の混じった表情"},
        background="夕焼けに染まる荒野、廃城の尖塔"
    )
    
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="魔法,剣",
        archetype_key="チート主人公",
        target_eps=10,
        initial_limit=3,
        word_count=2000,
        foreshadowings=[fs],
        hooks=[hook],
        illustration_points=[ip],
        current_volume=1,
        current_episode=3
    )
    
    # すべてのフィールドが正しく設定されていることを確認
    assert len(ctx.foreshadowings) == 1
    assert ctx.foreshadowings[0] == fs
    
    assert len(ctx.hooks) == 1
    assert ctx.hooks[0] == hook
    
    assert len(ctx.illustration_points) == 1
    assert ctx.illustration_points[0] == ip
    
    assert ctx.current_volume == 1
    assert ctx.current_episode == 3