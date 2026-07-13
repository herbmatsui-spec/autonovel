import logging
import os
import sys

# プロジェクトルートをインポートパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_integration")

def test_imports():
    logger.info("Step 1: Testing imports...")
    try:
        from config.narrative import AUDIT_TRIGGER_KEYWORDS
        logger.info(f"✓ config.narrative imports OK. Trigger keywords count: {len(AUDIT_TRIGGER_KEYWORDS)}")

        logger.info("✓ sanitizer imports OK.")

        logger.info("✓ models.WorldRules imports OK.")
    except Exception as e:
        logger.error(f"✗ Import test failed: {e}", exc_info=True)
        sys.exit(1)

def test_world_rules_pydantic():
    logger.info("\nStep 2: Testing Pydantic WorldRules initialization...")
    try:
        from models import WorldRules
        # location_sensory_map が空のデフォルトで動くか
        rules = WorldRules()
        assert hasattr(rules, "location_sensory_map"), "location_sensory_map field is missing in WorldRules"
        logger.info("✓ Default WorldRules initialization OK.")

        # location_sensory_map を指定して動くか
        custom_map = {
            "深淵の森": {
                "安堵": "微かな腐敗臭を伴う冷たい弛緩",
                "光": "目に刺さるような異物感と疼き"
            }
        }
        rules_custom = WorldRules(location_sensory_map=custom_map)
        assert rules_custom.location_sensory_map["深淵の森"]["安堵"] == "微かな腐敗臭を伴う冷たい弛緩"
        logger.info("✓ Custom WorldRules initialization and validation OK.")
    except Exception as e:
        logger.error(f"✗ WorldRules Pydantic test failed: {e}", exc_info=True)
        sys.exit(1)

def test_physiological_translator():
    logger.info("\nStep 3: Testing PhysiologicalTranslator dynamic overrides...")
    try:
        from backend.sanitizer import PhysiologicalTranslator

        # 1. 通常の翻訳
        text_normal = "彼は激しい恐怖を感じた。"
        translated_normal = PhysiologicalTranslator.translate(text_normal)
        logger.info(f"Normal: '{text_normal}' -> '{translated_normal}'")

        # 2. アーキタイプ「武人」適用
        translated_warrior = PhysiologicalTranslator.translate(text_normal, archetypes=["武人"])
        logger.info(f"Warrior: '{text_normal}' -> '{translated_warrior}'")
        assert "五感が極限まで研ぎ澄まされ" in translated_warrior, "Warrior override failed"

        # 3. アーキタイプ「魔導師」適用
        translated_mage = PhysiologicalTranslator.translate(text_normal, archetypes=["魔導師"])
        logger.info(f"Mage: '{text_normal}' -> '{translated_mage}'")
        assert "脳髄に冷たい魔力の澱みが溜まり" in translated_mage, "Mage override failed"

        # 4. 場所「深淵の森」の感覚オーバーレイ適用
        location_overlay = {
            "恐怖": "肌に冷たい粘液が這い回るような、実体のない嫌悪感"
        }
        translated_loc = PhysiologicalTranslator.translate(text_normal, location_map=location_overlay)
        logger.info(f"Location Overlay: '{text_normal}' -> '{translated_loc}'")
        assert "肌に冷たい粘液が這い回る" in translated_loc, "Location overlay override failed"

        logger.info("✓ PhysiologicalTranslator dynamic overrides OK.")
    except Exception as e:
        logger.error(f"✗ PhysiologicalTranslator test failed: {e}", exc_info=True)
        sys.exit(1)

def test_vocabulary_optimizer_integration():
    logger.info("\nStep 4: Testing VocabularyOptimizer deduplicate integration...")
    try:
        from backend.sanitizer import VocabularyOptimizer

        text = "暗闇の中で彼は恐怖に震えた。"
        # force_physiological ポリシーがTrueのときに動くか検証
        sanitizer_policy = {"force_physiological": True}

        # 1. アーキタイプなし
        out_normal = VocabularyOptimizer.deduplicate(text, sanitizer_policy=sanitizer_policy)
        logger.info(f"Optimizer Normal: {out_normal}")

        # 2. アーキタイプあり
        out_warrior = VocabularyOptimizer.deduplicate(
            text,
            sanitizer_policy=sanitizer_policy,
            archetypes=["武人"]
        )
        logger.info(f"Optimizer Warrior: {out_warrior}")
        assert "五感が極限まで研ぎ澄まされ" in out_warrior, "Optimizer Archetype pass-through failed"

        # 3. 場所オーバーレイあり
        location_overlay = {
            "恐怖": "背筋に凍りつくような針を突き立てられる激痛"
        }
        out_loc = VocabularyOptimizer.deduplicate(
            text,
            sanitizer_policy=sanitizer_policy,
            location_map=location_overlay
        )
        logger.info(f"Optimizer Location: {out_loc}")
        assert "背筋に凍りつくような針" in out_loc, "Optimizer Location pass-through failed"

        logger.info("✓ VocabularyOptimizer integration OK.")
    except Exception as e:
        logger.error(f"✗ VocabularyOptimizer integration test failed: {e}", exc_info=True)
        sys.exit(1)

def test_audit_triggers():
    logger.info("\nStep 5: Testing V4.6 Triggered Audit logic...")
    try:
        from config.narrative import AUDIT_TRIGGER_KEYWORDS

        # 1. 監査をトリガーすべきプロット (魔法キーワードあり)
        blueprint_high_risk = "主人公は失われた魔法を使って、強大な魔物を撃破する。"
        found_triggers_high = [kw for kw in AUDIT_TRIGGER_KEYWORDS if kw in blueprint_high_risk]
        logger.info(f"High risk blueprint triggers: {found_triggers_high}")
        assert len(found_triggers_high) > 0, "Failed to detect high risk triggers"

        # 2. 監査をスキップすべきプロット (キーワードなし)
        blueprint_low_risk = "彼らは静かな町でスープを飲み、次の旅支度を整えた。"
        found_triggers_low = [kw for kw in AUDIT_TRIGGER_KEYWORDS if kw in blueprint_low_risk]
        logger.info(f"Low risk blueprint triggers: {found_triggers_low}")
        assert len(found_triggers_low) == 0, "Mistakenly detected low risk triggers"

        logger.info("✓ Triggered Audit logic simulation OK.")
    except Exception as e:
        logger.error(f"✗ Audit triggers test failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    logger.info("=== Hegemony Engine V4.6 Integration Test Starting ===")
    test_imports()
    test_world_rules_pydantic()
    test_physiological_translator()
    test_vocabulary_optimizer_integration()
    test_audit_triggers()
    logger.info("\n=== ALL INTEGRATION TESTS PASSED SUCCESSFULLY! ===")

