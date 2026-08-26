with open('src/backend/server.py', 'rb') as f: data = f.read(); 
# Look for the try: line that corresponds to this finally
pos = 3438
# Look further back to find the try:
search_start = max(0, pos - 300)
search_area = data[search_start:pos]
# Look for try: with proper indentation
try_pos = search_area.rfind(b'    try:\r\n')
if try_pos != -1:
    actual_try_pos = search_start + try_pos
    print('Found try: at:', actual_try_pos)
    context_before = data[max(0, actual_try_pos-20):actual_try_pos]
    context_after = data[actual_try_pos:actual_try_pos+50]
    print('Context before:')
    print(repr(context_before))
    print('Context after:')
    print(repr(context_after))
else:
    print('try: not found with expected indentation')
    # Let's see what try patterns we can find
    i = 0
    while i < len(search_area) - 5:
        if search_area[i:i+2] == b'tr' and search_area[i+2:i+6] == b'ay:' and (search_area[i+6] == 58 or search_area[i+6] == 32):  # 58=: 32=space
            print('Found \"try:\" at relative pos', i, ':', repr(search_area[i:i+10]))
        i += 1