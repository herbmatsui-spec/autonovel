with open('src/services/retry_decorator.py', 'rb') as f: data = f.read();
# Find the except Exception block
import re
matches = list(re.finditer(b'except Exception as e:', data))
if matches:
    match = matches[0]
    pos = match.start()
    # Show what we're going to replace
    context = data[max(0, pos-20):pos+100]
    print('Replacing:')
    print(repr(context))
    # Replace with more specific exceptions
    old_text = b'except Exception as e:\r\n                    # \xe3\x82\xb3\xe3\x83\xbc\xe3\x83\x89\xe3\x81\xae\xe3\x83\x90\xe3\x82\xb0\xe3\x82\x84\xe3\x83\x97\xe3\x82\xb0\xe3\x83\xa9\xe3\x83\xa0\xe8\xab\x96\xe7\x90\x86\xe3\x82\xa8\xe3\x83\xa9\xe3\x83\xbc\xe3\x81\xafFail-Fast\xe3\x81\xa7\xe5\x8d\xb3\xe5\xba\xa7\xe3\x81\xab\xe6\x8a\x95\xe3\x81\x92\xe3\x82\x8b\r\n                    if isinstance(e, (TypeError, NameError, AttributeError, KeyError)):\r\n                        raise e\r\n\r\n                    err_msg = str(e).lower() or repr(e).lower()\r\n\r\n                    # 1. トークン超過の判定（Fail-Fast対象）'
    new_text = b'except (ConnectionError, TimeoutError, OSError, ValueError) as e:\r\n                    # \xe3\x82\xb3\xe3\x83\xbc\xe3\x83\x89\xe3\x81\xae\xe3\x83\x90\xe3\x82\xb0\xe3\x82\x84\xe3\x83\x97\xe3\x82\xb0\xe3\x83\xa9\xe3\x83\xa0\xe8\xab\x96\xe7\x90\x86\xe3\x82\xa8\xe3\x83\xa9\xe3\x83\xbc\xe3\x81\xafFail-Fast\xe3\x81\xa7\xe5\x8d\xb3\xe5\xba\xa7\xe3\x81\xab\xe6\x8a\x95\xe3\x81\x92\xe3\x82\x8b\r\n                    if isinstance(e, (TypeError, NameError, AttributeError, KeyError)):\r\n                        raise e\r\n\r\n                    err_msg = str(e).lower() or repr(e).lower()\r\n\r\n                    # 1. トークン超過の判定（Fail-Fast対象）'
    if old_text in data:
        print('Found exact match, replacing...')
        new_data = data.replace(old_text, new_text)
        # Write back
        with open('src/services/retry_decorator.py', 'wb') as f2:
            f2.write(new_data)
        print('Replacement completed')
    else:
        print('Exact match not found')
else:
    print('No except Exception found')