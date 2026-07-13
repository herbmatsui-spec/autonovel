# Archive Inventory and Dependency Scan

## 1. File Inventory

### archive/legacy_scripts/
- `config_legacy.py`
- `database.py`
- `database_legacy.py`
- `engine_agents_legacy.py`
- `engine_prompts_legacy.py`
- `models_legacy.py`
- `test_easy_mode.py`
- `test_integration.py`
- `scratch_debug.py`
- `scratch_gemini_test.py`
- `scratch_schema_test.py`
- `scratch_test_audit.py`
- `backups/` (Numerous backup files including `database_v1_backup.py`, `sanitizer_bak.py`)
- `backups/old_scratch/` (Various test and utility scripts)
- `backups/scratch_archive/` (Recovery scripts and archived agents)

### archive/scratch/
- `arg_drafting_*.py` (Query/Content files)
- `drafting_candidate_*.py`
- `extract_*.py`
- `find_*.py`
- `tc_drafting_candidate_*.py`
- `test_*.py`
- `verify_sqlalchemy.py`

## 2. Dependency Scan (from src)
- `archive/legacy_scripts/` and `archive/scratch/` contain predominantly standalone scripts, recovery tools, or legacy versions of core modules.
- Most scripts in these directories are either self-contained or import from `config` (legacy versions).
- No critical active dependencies from `src/` to `archive/` were found. 
- A few legacy scripts might attempt to import `src` but they are not referenced by the main application.

## 3. Conclusion
The `archive/` directory is purely a historical repository and scratchpad. It can be safely isolated without affecting the current system stability.
