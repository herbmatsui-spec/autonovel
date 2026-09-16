import importlib.util
import sys
import os

# Function to load a module from a file path
def load_module(file_path):
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

# Load the three test modules
test_hook = load_module("E:/hhh/tests/unit/services/test_hook_diagnoser.py")
test_ep = load_module("E:/hhh/tests/unit/services/test_episode_context.py")
test_audit = load_module("E:/hhh/tests/unit/services/test_audit_service.py")

# Collect all test functions (those starting with 'test_')
import inspect
test_functions = []
for module in [test_hook, test_ep, test_audit]:
    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj) and name.startswith('test_'):
            test_functions.append(obj)

# Run each test function
def run_all():
    failed = 0
    passed = 0
    for test_func in test_functions:
        try:
            test_func()
            print(f"PASS: {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {test_func.__name__} - {e}")
            # Uncomment below to see traceback
            # import traceback
            # traceback.print_exc()
            failed += 1
    print(f"\nTotal: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)