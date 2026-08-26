# Simple script to replace except Exception with specific exceptions in server.py generate_easy function

# Read the file
with open('src/backend/server.py', 'rb') as f:
    data = f.read()

# Replace the specific except Exception line in generate_easy function
old_line = b'    except Exception as e:\r\n'
new_line = b'    except (ConnectionError, TimeoutError, OSError) as e:\r\n'
if old_line in data:
    print('Found the target line, replacing...')
    new_data = data.replace(old_line, new_line)
    print('Replacement completed')
else:
    print('Target line not found')
    # Let's see what we actually have around the area
    lines = data.split(b'\n')
    for i in range(345, 355):
        if i < len(lines):
            print('{}: {}'.format(i+1, repr(lines[i])))

# Write back
with open('src/backend/server.py', 'wb') as f2:
    f2.write(new_data)