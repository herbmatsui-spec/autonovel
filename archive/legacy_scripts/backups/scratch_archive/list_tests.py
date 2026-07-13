import os

for root, dirs, files in os.walk('tests'):
    for file in files:
        print(os.path.join(root, file))

