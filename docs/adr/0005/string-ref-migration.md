# String Provide Reference Migration

Target: Replace `Provide["..."]` with `Provide[Symbol]`

## Current Occurrences

1. `src/services/prompt_version_service.py:20-21`
   - `Provide["config.container.AppContainer.uow"]` → `Provide[AppContainer.uow]`
   - `Provide["config.container.AppContainer.prompt_repo"]` → 新規 provider 追加後

## Migration Steps

1. `from src.core.container import AppContainer` を追加
2. 文字列参照をシンボル参照に置換
3. `prompt_repo` provider が存在しない場合は `AppContainer` に追加
