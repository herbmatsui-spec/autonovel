import json


def analyze_tropes():
    tropes_file = 'config/tropes.json'
    arch_file = 'config/data/archetypes.json'

    try:
        with open(tropes_file, 'r', encoding='utf-8') as f:
            tropes_data = json.load(f).get('tropes', [])
    except Exception as e:
        print(f"Error reading {tropes_file}: {e}")
        tropes_set = set()
    else:
        trop_set = set(tropes_data)

    try:
        with open(arch_file, 'r', encoding='utf-8') as f:
            arch_data = json.load(f)
    except Exception as e:
        print(f"Error reading {arch_file}: {e}")
        return

    all_arch_tropes = set()

    # From PLOT_STRUCTURES
    for p in arch_data.get('PLOT_STRUCTURES', {}).values():
        all_arch_tropes.update(p.get('key_tropes', []))

    # From STORY_ARCHETYPES
    for a in arch_data.get('STORY_ARCHETYPES', {}).values():
        keywords = a.get('keywords')
        if keywords and isinstance(keywords, str):
            all_arch_tropes.update([k.strip() for k in keywords.split(',')])
        elif keywords and isinstance(keywords, list):
            all_arch_tropes.update([k.strip() for k in keywords])

    intersection = trop_set.intersection(all_arch_tropes)

    print("--- Trope Analysis ---")
    print(f"Tropes in tropes.json: {tropes_data}")
    print(f"Total unique tropes in archetypes.json: {len(all_arch_tropes)}")
    print(f"Intersection: {intersection}")
    print(f"Tropes in tropes.json NOT in archetypes: {trop_set - all_arch_tropes}")
    print(f"Tropes in archetypes NOT in tropes.json: {all_arch_tropes - trop_set}")

if __name__ == '__main__':
    analyze_tropes()

