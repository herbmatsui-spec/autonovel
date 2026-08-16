#!/usr/bin/env python3
"""
ENV_OVERRIDE_MAP と Settings フィールドの整合性検証スクリプト
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import Settings


def validate_env_override_map() -> int:
    """ENV_OVERRIDE_MAP の値が Settings フィールドと一致するか検証"""
    settings = Settings()
    settings_fields = set(settings.model_fields.keys())
    env_override_map = Settings.ENV_OVERRIDE_MAP
    
    print(f"Settings フィールド数: {len(settings_fields)}")
    print(f"ENV_OVERRIDE_MAP エントリ数: {len(env_override_map)}")
    
    errors = []
    warnings = []
    
    for env_var, field_name in env_override_map.items():
        if field_name not in settings_fields:
            errors.append(f"ENV_OVERRIDE_MAP['{env_var}'] = '{field_name}' → Settings にフィールド '{field_name}' が存在しません")
        else:
            # 型チェック (オプショナル)
            field_info = settings.model_fields[field_name]
            print(f"  OK: {env_var} → {field_name} ({field_info.annotation})")
    
    # 逆方向チェック: Settings フィールドで ENV_OVERRIDE_MAP にないもの
    mapped_fields = set(env_override_map.values())
    unmapped = settings_fields - mapped_fields
    if unmapped:
        for field in sorted(unmapped):
            # プライベートフィールドや ClassVar は除外
            if not field.startswith("_") and field not in ("model_config", "ENV_OVERRIDE_MAP"):
                warnings.append(f"Settings フィールド '{field}' が ENV_OVERRIDE_MAP にマッピングされていません")
    
    if errors:
        print("\n❌ エラー:")
        for e in errors:
            print(f"  {e}")
    
    if warnings:
        print("\n⚠️  警告 (環境変数での上書き不可):")
        for w in warnings:
            print(f"  {w}")
    
    if not errors:
        print("\n✅ 全 ENV_OVERRIDE_MAP エントリが Settings フィールドと一致しています")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(validate_env_override_map())