import json


def merge_tropes():
    tropes_file = 'config/tropes.json'
    arch_file = 'config/data/archetypes.json'
    output_file = 'config/tropes_consolidated.json'

    # Read tropes.json
    try:
        with open(tropes_file, 'r', encoding='utf-8') as f:
            tropes_data = json.load(f)
            original_tropes = set(tropes_data.get('tropes', []))
            replacements = tropes_data.get('forbidden_words_replacements', {})
    except Exception as e:
        print(f"Error reading {tropes_file}: {e}")
        original_tropes = set()
        replacements = {}

    # Read archetypes.json
    try:
        with open(arch_file, 'r', encoding='utf-8') as f:
            arch_data = json.load(f)
    except Exception as e:
        print(f"Error reading {arch_file}: {e}")
        return

    all_arch_tropes = set()

    # Extract from PLOT_STRUCTURES
    for p in arch_data.get('PLOT_STRUCTURES', {}).values():
        all_arch_tropes.update(p.get('key_tropes', []))

    # Extract from STORY_ARCHETYPES
    for a in arch_data.get('STORY_ARCHETYPES', {}).values():
        keywords = a.get('keywords')
        if keywords and isinstance(keywords, str):
            all_arch_tropes.update([k.strip() for k in keywords.split(',')])
        elif keywords and isinstance(keywords, list):
            all_arch_tropes.update([k.strip() for k in keywords])

    # Merge sets
    final_tropes = sorted(list(original_tropes.union(all_arch_tropes)))

    consolidated_data = {
        "tropes": final_tropes,
        "forbidden_words_replacements": replacements
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(consolidated_data, f, ensure_ascii=False, indent=2)

    print(f"Consolidated tropes written to {output_file}")
    print(f"Total tropes: {len(final_tropes)}")

if __name__ == '__main__':
    merge_tropes()

