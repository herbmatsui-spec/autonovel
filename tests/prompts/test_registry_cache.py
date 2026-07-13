import os
import time

from prompts.registry import PromptRegistry


def test_prompt_registry_cache_hit():
    """キャッシュが正しく機能し、2回目以降のアクセスでファイルI/Oが削減されることを検証する"""
    # テスト用の一時ファイルを作成
    test_dir = os.path.abspath("tests/prompts/temp_templates")
    os.makedirs(test_dir, exist_ok=True)
    template_path = os.path.join(test_dir, "test_prompt.j2")

    with open(template_path, "w", encoding="utf-8") as f:
        f.write("---\nversion: 1.0\n---\nHello {{ name }}!")

    registry = PromptRegistry(templates_dir=test_dir)

    # 1回目の呼び出し: キャッシュミス -> ファイル読み込み
    source1 = registry._get_template_source_sync("test_prompt.j2")
    assert "Hello {{ name }}!" in source1
    assert "test_prompt.j2" in registry._template_cache

    # キャッシュ内容を確認
    cached = registry._template_cache["test_prompt.j2"]
    initial_mtime = cached.mtime

    # 2回目の呼び出し: キャッシュヒット
    # 内部的に logger.debug が呼ばれるはず
    source2 = registry._get_template_source_sync("test_prompt.j2")
    assert source1 == source2
    assert registry._template_cache["test_prompt.j2"].mtime == initial_mtime

def test_prompt_registry_cache_expiration():
    """ファイルが更新された際にキャッシュが正しく無効化されることを検証する"""
    test_dir = os.path.abspath("tests/prompts/temp_templates")
    os.makedirs(test_dir, exist_ok=True)
    template_path = os.path.join(test_dir, "test_prompt_update.j2")

    with open(template_path, "w", encoding="utf-8") as f:
        f.write("Version 1")

    registry = PromptRegistry(templates_dir=test_dir)

    # 初回ロード
    source1 = registry._get_template_source_sync("test_prompt_update.j2")
    assert source1 == "Version 1"

    # ファイルを更新 (mtimeを確実に変更させるため少し待機)
    time.sleep(0.1)
    with open(template_path, "w", encoding="utf-8") as f:
        f.write("Version 2")

    # 2回目の呼び出し: キャッシュはあるが mtime が新しいため更新されるべき
    source2 = registry._get_template_source_sync("test_prompt_update.j2")
    assert source2 == "Version 2"

def test_prompt_registry_lru_eviction():
    """キャッシュが最大サイズに達したときに古いエントリが削除されることを検証する"""
    test_dir = os.path.abspath("tests/prompts/lru_test")
    os.makedirs(test_dir, exist_ok=True)

    registry = PromptRegistry(templates_dir=test_dir)
    registry._cache_max_size = 2  # テスト用にサイズを小さく設定

    # 3つのテンプレートを擬似的にキャッシュに登録
    for i in range(3):
        name = f"tpl_{i}.j2"
        # 実際にはファイルが必要なので作成
        with open(os.path.join(test_dir, name), "w") as f:
            f.write(f"Content {i}")
        registry._get_template_source_sync(name)

    # 最大サイズ2なので、最初に入れた tpl_0.j2 は削除されているはず
    assert "tpl_0.j2" not in registry._template_cache
    assert "tpl_1.j2" in registry._template_cache
    assert "tpl_2.j2" in registry._template_cache
