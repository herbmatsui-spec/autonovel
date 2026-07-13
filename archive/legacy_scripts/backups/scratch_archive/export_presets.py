import sys

import yaml

sys.path.append('d:/claude2')
from config_style_presets import _DEFAULT_AUTHOR_STYLE_PRESETS

with open('d:/claude2/prompts/templates/style_presets.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(_DEFAULT_AUTHOR_STYLE_PRESETS, f, allow_unicode=True, sort_keys=False)
print("Successfully dumped style presets to prompts/templates/style_presets.yaml")

