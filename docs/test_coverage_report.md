============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.0.3, pluggy-1.6.0
rootdir: i:\R15\cR15
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.12.1, langsmith-0.8.8, asyncio-1.4.0, cov-7.1.0, mock-3.15.1, xdist-3.8.0, typeguard-4.5.2
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 172 items / 5 errors

=================================== ERRORS ====================================
__________ ERROR collecting tests/integration/test_enigma_engine.py ___________
ImportError while importing test module 'i:\R15\cR15\tests\integration\test_enigma_engine.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
C:\Python314\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\integration\test_enigma_engine.py:4: in <module>
    from src.agents.audit import InternalLogicValidator
E   ImportError: cannot import name 'InternalLogicValidator' from 'src.agents.audit' (i:\R15\cR15\src\agents\audit.py)
______________ ERROR collecting tests/test_background_worker.py _______________
ImportError while importing test module 'i:\R15\cR15\tests\test_background_worker.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
C:\Python314\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\test_background_worker.py:5: in <module>
    from src.backend.tasks import run_test_coro, huey
src\backend\tasks.py:5: in <module>
    from src.core.observability import with_trace_context
E   ImportError: cannot import name 'with_trace_context' from 'src.core.observability' (i:\R15\cR15\src\core\observability.py)
________________ ERROR collecting tests/test_outbox_worker.py _________________
ImportError while importing test module 'i:\R15\cR15\tests\test_outbox_worker.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
C:\Python314\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\test_outbox_worker.py:4: in <module>
    from src.backend.tasks import _process_outbox_events_async
src\backend\tasks.py:5: in <module>
    from src.core.observability import with_trace_context
E   ImportError: cannot import name 'with_trace_context' from 'src.core.observability' (i:\R15\cR15\src\core\observability.py)
____________ ERROR collecting tests/unit/test_commercial_roles.py _____________
C:\Users\keide\AppData\Roaming\Python\Python314\site-packages\_pytest\python.py:507: in importtestmodule
    mod = import_path(
C:\Users\keide\AppData\Roaming\Python\Python314\site-packages\_pytest\pathlib.py:587: in import_path
    importlib.import_module(module_name)
C:\Python314\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen importlib._bootstrap>:1398: in _gcd_import
    ???
<frozen importlib._bootstrap>:1371: in _find_and_load
    ???
<frozen importlib._bootstrap>:1342: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:938: in _load_unlocked
    ???
C:\Users\keide\AppData\Roaming\Python\Python314\site-packages\_pytest\assertion\rewrite.py:197: in exec_module
    exec(co, module.__dict__)
tests\unit\test_commercial_roles.py:11: in <module>
    from config.archetypes import (
E     File "i:\R15\cR15\config\archetypes.py", line 1
E       CHEAT_DESCRIPTIONS = {\n    \"CRAFTY_PLANNING\": \"Enemies anticipate and counter your strategic moves,\\\"\n    \"BETRAYAL\": \"Allies suddenly turn hostile,\\\"\n    \"STALEMATE\": \"Enemy forces become unbreakably equal in power,\\\"\n}\
E                              ^
E   SyntaxError: unexpected character after line continuation character
_____________ ERROR collecting tests/unit/test_llm_service_di.py ______________
ImportError while importing test module 'i:\R15\cR15\tests\unit\test_llm_service_di.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
C:\Python314\Lib\importlib\__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\unit\test_llm_service_di.py:5: in <module>
    from src.llm.provider_factory import LLMProviderFactory
src\llm\provider_factory.py:3: in <module>
    from src.llm.gemini_provider import GeminiProvider
src\llm\gemini_provider.py:6: in <module>
    from src.core.observability import track_llm_call
E   ImportError: cannot import name 'track_llm_call' from 'src.core.observability' (i:\R15\cR15\src\core\observability.py)
============================== warnings summary ===============================
C:\Users\keide\AppData\Roaming\Python\Python314\site-packages\google\genai\types.py:42
  C:\Users\keide\AppData\Roaming\Python\Python314\site-packages\google\genai\types.py:42: DeprecationWarning: '_UnionGenericAlias' is deprecated and slated for removal in Python 3.17
    VersionedUnionType = Union[builtin_types.UnionType, _UnionGenericAlias]

C:\Users\keide\AppData\Roaming\Python\Python314\site-packages\langchain_core\utils\pydantic.py:41
  C:\Users\keide\AppData\Roaming\Python\Python314\site-packages\langchain_core\utils\pydantic.py:41: UserWarning: Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.
    from pydantic.v1 import BaseModel as BaseModelV1

C:\Users\keide\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\keide\AppData\Roaming\Python\Python314\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

C:\Users\keide\AppData\Roaming\Python\Python314\site-packages\pythonjsonlogger\jsonlogger.py:11
  C:\Users\keide\AppData\Roaming\Python\Python314\site-packages\pythonjsonlogger\jsonlogger.py:11: DeprecationWarning: pythonjsonlogger.jsonlogger has been moved to pythonjsonlogger.json
    warnings.warn(

scripts\generate_plot.py:53
  i:\R15\cR15\scripts\generate_plot.py:53: PydanticDeprecatedSince20: Pydantic V1 style `@validator` validators are deprecated. You should migrate to Pydantic V2 style `@field_validator` validators, see the migration guide for more details. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.12/migration/
    @validator("genre")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
ERROR tests/integration/test_enigma_engine.py
ERROR tests/test_background_worker.py
ERROR tests/test_outbox_worker.py
ERROR tests/unit/test_commercial_roles.py
ERROR tests/unit/test_llm_service_di.py
!!!!!!!!!!!!!!!!!!! Interrupted: 5 errors during collection !!!!!!!!!!!!!!!!!!!
================= 5 warnings, 5 errors in 1178.61s (0:19:38) ==================
