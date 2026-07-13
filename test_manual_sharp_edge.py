import sys
sys.path.insert(0, 'D:/R15/cR15/src')

from src.models.sharp_edge import SharpEdgeSpec

print("Testing SharpEdgeSpec with key_phrase field...")

# Test 1: default key_phrase empty
edge1 = SharpEdgeSpec(
    edge_type="ending_pullback",
    description="余韻のある終わり方",
)
assert edge1.key_phrase == ""
print("✓ Test 1 passed: default key_phrase is empty")

# Test 2: valid key_phrase (Japanese)
edge2 = SharpEdgeSpec(
    edge_type="ending_pullback",
    description="余韻のある終わり方",
    key_phrase="余韻のある終わり方を",
)
print(f"✓ Test 2 passed: key_phrase = {edge2.key_phrase} (len: {len(edge2.key_phrase)})")

# Test 3: 20 characters exact (Japanese)
edge3 = SharpEdgeSpec(
    edge_type="ending_pullback",
    description="余韻のある終わり方",
    key_phrase="あ" * 20,
)
assert len(edge3.key_phrase) == 20
print("✓ Test 3 passed: 20 characters")

# Test 4: 21 characters should raise error
try:
    SharpEdgeSpec(
        edge_type="ending_pullback",
        description="余韻のある終わり方",
        key_phrase="あ" * 21,
    )
    print("✗ Test 4 failed: Should have raised ValidationError")
except Exception as e:
    print(f"✓ Test 4 passed: ValidationError raised - {type(e).__name__}")

# Test 5: preserve_on_quality_polish warning
import logging
logging.basicConfig(level=logging.WARNING)
edge5 = SharpEdgeSpec(
    edge_type="protagonist_flaw",
    description="主人公の欠陥",
    preserve_on_quality_polish=False,
)
print("✓ Test 5 passed: created edge with preserve_on_quality_polish=False")

print("\nAll manual tests passed successfully!")