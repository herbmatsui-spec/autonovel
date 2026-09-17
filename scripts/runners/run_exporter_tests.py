import importlib.util
import sys
# Load the services exporters base module directly from file to avoid any package issues
spec = importlib.util.spec_from_file_location("exporters_base", "E:\\hhh\\src\\services\\exporters\\base.py")
exporters_base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = exporters_base
spec.loader.exec_module(exporters_base)

# Now import the test module
spec_test = importlib.util.spec_from_file_location("test_base", "E:\\hhh\\tests\\unit\\services\\exporters\\test_base.py")
test_module = importlib.util.module_from_spec(spec_test)
sys.modules[spec_test.name] = test_module
spec_test.loader.exec_module(test_module)

# Get all functions from test module that start with 'test_'
import inspect
test_functions = [getattr(test_module, name) for name, obj in inspect.getmembers(test_module) if inspect.isfunction(obj) and name.startswith('test_')]

def run_tests():
    for test_func in test_functions:
        try:
            test_func()
            print("PASS:", test_func.__name__)
        except Exception as e:
            print("FAIL:", test_func.__name__, e)
            # import traceback
            # traceback.print_exc()

if __name__ == "__main__":
    run_tests()
    print("All tests completed.")