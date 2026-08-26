import os

env_path = r'E:\aaaaaa\src\backend\alembic\env.py'
with open(env_path, 'r', encoding='utf-8') as f:
    content = f.read()

# patch target_metadata=target_metadata to target_metadata=None
patched_content = content.replace('target_metadata=target_metadata', 'target_metadata=None')

with open(env_path, 'w', encoding='utf-8') as f:
    f.write(patched_content)

print("Patched env.py")
