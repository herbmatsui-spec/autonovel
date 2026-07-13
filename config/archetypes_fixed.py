# Archetype constants for the application
CHEAT_DESCRIPTIONS = {
    "NONE": "No cheat abilities",
    "WEAK": "Minor cheat abilities",
    "MODERATE": "Moderate cheat abilities",
    "STRONG": "Strong cheat abilities",
    "OVERPOWERED": "Overpowered cheat abilities"
}

COST_DESCRIPTIONS = {
    "LOW": "Low cost",
    "MEDIUM": "Medium cost",
    "HIGH": "High cost",
    "EXTREME": "Extreme cost"
}

VILLAIN_STRATEGIES = [
    "direct_confrontation",
    "psychological_warfare",
    "resource_drain",
    "ally_corruption",
    "time_pressure"
]

DEBUFF_PROFILES = {
    "none": {"effect": 0, "duration": 0},
    "weak": {"effect": 0.1, "duration": 5},
    "moderate": {"effect": 0.3, "duration": 10},
    "strong": {"effect": 0.5, "duration": 15}
}

PLOT_STRUCTURES = {
    "hero_journey": ["departure", "initiation", "return"],
    "three_act": ["setup", "confrontation", "resolution"],
    "five_act": ["exposition", "rising_action", "climax", "falling_action", "denouement"]
}

STORY_ARCHETYPES = [
    "overcoming_the_monster",
    "rags_to_riches",
    "the_quest",
    "voyage_and_return",
    "comedy",
    "tragedy",
    "rebirth"
]

ARCHETYPE_KEY_ALIASES = {
    "pure_love": "純愛官能（情緒重視）",
    "bondage": "背徳官能（心理葛藤重視）",
    "fantasy": "ファンタジー官能（異種族・魔法感覚）",
    "married": "夫婦/既婚官能（日常情緒）"
}

EASY_MODE_KEYWORDS_MAP = {
    "easy": ["初心者向け", "やさしい", "簡単"],
    "normal": ["標準", "普通"],
    "hard": ["上級者向け", "難しい", "挑戦"]
}

WIZARD_GENRE_OPTIONS = [
    "ファンタジー",
    "SF",
    "現代",
    "歴史",
    "その他"
]

WIZARD_ARCHETYPE_LABELS = {
    "純愛官能（情緒重視）": "Pure Love",
    "背徳官能（心理葛藤重視）": "Bondage",
    "ファンタジー官能（異種族・魔法感覚）": "Fantasy",
    "夫婦/既婚官能（日常情緒）": "Married"
}

EASY_GENRES = ["コメディ", "日常", "学園"]

def resolve_archetype_key(key):
    """Resolve archetype key to canonical form."""
    return ARCHETYPE_KEY_ALIASES.get(key, key)

