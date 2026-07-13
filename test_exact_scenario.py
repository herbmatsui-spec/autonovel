import sys
sys.path.insert(0, '.')

# Recreate the EXACT test scenario from test_key_phrase_case_insensitive
from src.models.sharp_edge import SharpEdgeSpec

# This is the EXACT test from the file
edges = [SharpEdgeSpec(edge_type="protagonist_flaw", description="説明", key_phrase="Deep Hidden Power")]
after = "THE DEEP HIDDEN POWER GRANTED HIM NEW LIFE"

print("=== EXACT Test Scenario ===")
print(f"Key phrase: {repr(edges[0].key_phrase)}")
print(f"After content: {repr(after)}")
print(f"Key phrase lowercase: {repr(edges[0].key_phrase.lower())}")
print(f"After content lowercase: {repr(after.lower())}")

# Check if match
does_match = edges[0].key_phrase.lower() in after.lower()
print(f"Does match: {does_match}")

# Now test the actual function
from src.backend.sharp_edge_preserver import check_edges_preserved
result = check_edges_preserved("before", after, edges)
print(f"check_edges_preserved result: {result}")
print(f"Expected: [] (empty list, meaning preserved)")
print(f"Pass test: {result == []}")