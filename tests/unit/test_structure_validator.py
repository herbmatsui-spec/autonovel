from src.services.structure_validator import (
    assign_phases,
    list_structures,
    load_structure,
    validate,
)


def test_load_structure():
    """定義済み構造テンプレートのロードと未知テンプレートのフォールバック検証。"""
    three_act = load_structure("three_act")
    assert three_act["name"] == "三幕構成"
    assert len(three_act["required_beats"]) == 5

    kisho = load_structure("kishotenketsu")
    assert kisho["name"] == "起承転結"

    # 未知の場合は three_act にフォールバック
    fallback = load_structure("unknown_structure")
    assert fallback["name"] == "三幕構成"


def test_assign_phases():
    """章ごとのフェーズ (0.0〜1.0) 割り当ての検証。"""
    chapters = [
        {"chapter_number": 1, "title": "第1章"},
        {"chapter_number": 2, "title": "第2章"},
        {"chapter_number": 3, "title": "第3章"},
        {"chapter_number": 4, "title": "第4章"},
    ]

    phased = assign_phases(chapters)
    assert len(phased) == 4
    assert phased[0]["_phase"] == 0.0
    assert phased[-1]["_phase"] == 1.0


def test_validate_structure_basic():
    """物語構造の整合性バリデーションの実行検証。"""
    chapters = [
        {"chapter_number": 1, "title": "日常と事件の発端", "summary": "事件が起きる", "tension": 2},
        {"chapter_number": 2, "title": "旅立ちと展開", "summary": "冒険に出る", "tension": 4},
        {"chapter_number": 3, "title": "決戦とクライマックス", "summary": "ボスを倒す", "tension": 10},
        {"chapter_number": 4, "title": "エピローグと結末", "summary": "平和が戻る", "tension": 1},
    ]

    result = validate(chapters, structure_name="kishotenketsu")
    assert "structure" in result
    assert "missing_beats" in result
    assert "climax" in result
    assert "is_healthy" in result


def test_list_structures():
    """利用可能な構造テンプレート一覧の取得検証。"""
    structures = list_structures()
    assert len(structures) >= 3
    assert any(s["key"] == "three_act" for s in structures)
