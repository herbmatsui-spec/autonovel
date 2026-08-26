import os

# Read the file
with open('src/backend/server.py', 'rb') as f:
    data = f.read()

# Replace the specific except Exception line in generate_easy function
old_line = b'    except Exception as e:\r\n'
new_line = b'    except (ConnectionError, TimeoutError, OSError) as e:\r\n'
if old_line in data:
    print('Found the target line, replacing...')
    new_data = data.replace(old_line, new_line)
    
    # Split into lines to modify the error message
    lines = new_data.split(b'\n')
    for i, line in enumerate(lines):
        if b'logger.error(f"Failed to enqueue easy mode task:' in line:
            print('Found logger.error line at index {}: {}'.format(i, repr(line)))
            # Look for the HTTPException detail line in the next few lines
            for j in range(i+1, min(len(lines), i+5)):
                if b'HTTPException' in lines[j] and b'detail=' in lines[j]:
                    print('Found HTTPException detail line at index {}: {}'.format(j, repr(lines[j])))
                    # Replace the detail line with proper Japanese
                    lines[j] = b'        raise HTTPException(status_code=500, detail=f"かんたんモードタスクのエンqueueに失敗しました: {str(e)}")'
                    print('Updated line to: {}'.format(repr(lines[j])))
                    break
            break
    
    new_data = b'\n'.join(lines)
    
    # Write back
    with open('src/backend/server.py', 'wb') as f2:
        f2.write(new_data)
    print('Replacement completed')
else:
    print('Target line not found')
    # Let's see what we actually have around the area
    lines = data.split(b'\n')
    for i in range(345, 355):
        if i < len(lines):
            print('{}: {}'.format(i+1, repr(lines[i])))