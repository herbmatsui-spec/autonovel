"""
Tests for PDCA controller.
"""

from src.generation.pdca_controller import PDCAController


def test_no_full_regeneration_when_max_zero():
    """max_regenerations=0 の場合、全文再生成は禁止される"""
    controller = PDCAController(max_regenerations=0)
    assert controller.should_regenerate_full_text() == False


def test_full_regeneration_allowed_when_max_positive():
    """max_regenerations > 0 の場合、一定回数まで全文再生成が許可される"""
    controller = PDCAController(max_regenerations=2)
    assert controller.should_regenerate_full_text() == True
    
    controller.record_full_regeneration()
    assert controller.should_regenerate_full_text() == True
    
    controller.record_full_regeneration()
    assert controller.should_regenerate_full_text() == False


def test_local_patch_limited_to_once():
    """max_local_patches=1 の場合、局所パッチは1回までしか許可されない"""
    controller = PDCAController(max_local_patches=1)
    assert controller.can_do_local_patch() == True
    
    controller.record_local_patch()
    assert controller.can_do_local_patch() == False


def test_local_patch_limited_to_n():
    """max_local_patches=N の場合、局所パッチはN回までしか許可されない"""
    controller = PDCAController(max_local_patches=3)
    assert controller.can_do_local_patch() == True
    
    controller.record_local_patch()
    assert controller.can_do_local_patch() == True
    
    controller.record_local_patch()
    assert controller.can_do_local_patch() == True
    
    controller.record_local_patch()
    assert controller.can_do_local_patch() == False


def test_defaults_are_no_full_regeneration_and_one_local_patch():
    """デフォルト設定では全文再生成禁止・局所パッチ1回"""
    controller = PDCAController()  # デフォルトコンストラクタ
    assert controller.max_regenerations == 0
    assert controller.max_local_patches == 1
    assert controller.should_regenerate_full_text() == False
    assert controller.can_do_local_patch() == True
    
    controller.record_local_patch()
    assert controller.can_do_local_patch() == False


def test_reset_counts():
    """カウントのリセットが正しく動作する"""
    controller = PDCAController(max_regenerations=2, max_local_patches=1)
    
    # いくつかの操作を実行
    controller.record_full_regeneration()
    controller.record_local_patch()
    
    assert controller.should_regenerate_full_text() == True  # 1回使ったのでまだ1回残っている
    assert controller.can_do_local_patch() == False  # 局所パッチは使い果たした
    
    # リセット
    controller.reset_counts()
    
    assert controller.should_regenerate_full_text() == True  # リセット後は再生成可能
    assert controller.can_do_local_patch() == True  # リセット後は局所パッチも可能