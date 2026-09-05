import pytest
from src.models.illustration_point import IllustrationPoint


def test_illustration_point_creation():
    """IllustrationPoint オブジェクトの作成テスト"""
    ip = IllustrationPoint(
        id="IP-001",
        page="口絵1",
        scene_description="主人公とヒロインが夕焼け背景に背中合わせ",
        composition="主人公が左、ヒロインが右、二人の間に距離がある",
        props="主人公の剣とヒロインの杖を交差",
        expressions={"主人公": "決意した表情", "ヒロイン": "不安と信頼の混じった表情"},
        background="夕焼けに染まる荒野、廃城の尖塔"
    )
    
    assert ip.id == "IP-001"
    assert ip.page == "口絵1"
    assert ip.scene_description == "主人公とヒロインが夕焼け背景に背中合わせ"
    assert ip.composition == "主人公が左、ヒロインが右、二人の間に距離がある"
    assert ip.props == "主人公の剣とヒロインの杖を交差"
    assert ip.expressions == {"主人公": "決意した表情", "ヒロイン": "不安と信頼の混じった表情"}
    assert ip.background == "夕焼けに染まる荒野、廃城の尖塔"
    assert ip.notes is None


def test_illustration_point_with_notes():
    """notes付きIllustrationPoint オブジェクトの作成テスト"""
    ip = IllustrationPoint(
        id="IP-002",
        page="15",
        scene_description="主人公が雑魚敵を一刀両断",
        composition="主人公が中央に立ち、敵が左右に散らばる",
        props="主人公の刀に残像",
        expressions={"主人公": "余裕綽々だが目に死の気配"},
        background="暗い洞窟、壁に苔が生えている",
        notes="このシーンは第1章のクライマックス"
    )
    
    assert ip.notes == "このシーンは第1章のクライマックス"


def test_illustration_point_to_dict():
    """to_dict メソッドのテスト"""
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
    
    expected = {
        "id": "IP-003",
        "page": "口絵2",
        "scene_description": "二人が手をつなぎ歩く",
        "composition": "二人が画面中央からやや左に位置",
        "props": "なし",
        "expressions": {"ヒロイン": "幸せそうな笑顔"},
        "background": "桜並びの道、花びらが舞っている",
        "notes": "エンディングを彷彿とさせるシーン"
    }
    
    assert ip.to_dict() == expected


def test_illustration_point_from_dict():
    """from_dict メソッドのテスト"""
    data = {
        "id": "IP-004",
        "page": "25",
        "scene_description": "敵のリーダーと対峙する主人公",
        "composition": "主人公が前方に出て、敵が後方に構える",
        "props": "主人公の盾と敵の斧がぶつかり火花が散る",
        "expressions": {"主人公": "真剣な眼差し", "敵リーダー": "狂気的な笑み"},
        "background": "崖っぷちの決戦場、雷鳴が轟く",
        "notes": None
    }
    
    ip = IllustrationPoint.from_dict(data)
    
    assert ip.id == "IP-004"
    assert ip.page == "25"
    assert ip.scene_description == "敵のリーダーと対峙する主人公"
    assert ip.composition == "主人公が前方に出て、敵が後方に構える"
    assert ip.props == "主人公の盾と敵の斧がぶつかり火花が散る"
    assert ip.expressions == {"主人公": "真剣な眼差し", "敵リーダー": "狂気的な笑み"}
    assert ip.background == "崖っぷちの決戦場、雷鳴が轟く"
    assert ip.notes is None


def test_illustration_point_roundtrip():
    """to_dict -> from_dict のラウンドトリップテスト"""
    original = IllustrationPoint(
        id="IP-005",
        page="扉絵",
        scene_description="物語の世界観を示す広角ショット",
        composition="遠景に城が見え、手前に川が流れる",
        props="小舟が川を流れている",
        expressions={},
        background="青空に白い雲、遠くに山脈",
        notes="オープニングに使用推奨"
    )
    
    data = original.to_dict()
    restored = IllustrationPoint.from_dict(data)
    
    assert original == restored