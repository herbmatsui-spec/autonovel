import sys
sys.stdout.reconfigure(encoding='utf-8')
try:
    compile(open('src/agents/erotic_integrity.py','r',encoding='utf-8').read(), 'erotic_integrity.py', 'exec')
    print('OK')
except SyntaxError as e:
    print('SYNTAX ERROR:', e)