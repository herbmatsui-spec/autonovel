import os

for root, dirs, files in os.walk('.'):
    for file in files:
        if 'test_' in file and file.endswith('.py'):
            print(os.path.join(root, file))

