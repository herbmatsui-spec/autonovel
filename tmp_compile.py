source = '"key": {\n}\n'
try:
    compile(source, 'test.py', 'exec')
except SyntaxError as e:
    print('SyntaxError:', e.msg)
    print('text:', e.text)
    print('offset:', e.offset)

