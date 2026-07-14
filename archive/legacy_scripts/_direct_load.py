import sys, importlib.util
sys.stdout.reconfigure(encoding='utf-8')
spec = importlib.util.spec_from_file_location('e', r'I:\R15\cR15\src\agents\erotic_integrity.py')
m = importlib.util.module_from_spec(spec)
print('loading...')
spec.loader.exec_module(m)
print('OK')
print(dir(m))