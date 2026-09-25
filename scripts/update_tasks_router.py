import re

path = 'src/backend/routers/tasks.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if 'redis_client = await get_async_redis_client()' in line:
        new_lines.append(line)
        new_lines.append('    if redis_client is not None:\n')
        new_lines.append('        try:\n')
        new_lines.append('            val = await redis_client.get(f"task_status:{task_id}")\n')
        new_lines.append('            if val:\n')
        new_lines.append('                data = json.loads(val)\n')
        new_lines.append('                task_user_id = data.get("user_id")\n')
        new_lines.append('                if task_user_id and current_user and task_user_id != getattr(current_user, "id", None) and getattr(current_user, "role", None) != "admin":\n')
        new_lines.append('                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="このタスクへのアクセス権限がありません")\n')
        new_lines.append('                return data\n')
        new_lines.append('        except HTTPException:\n')
        new_lines.append('            raise\n')
        new_lines.append('        except Exception as exc:\n')
        new_lines.append('            logger.warning("Redis task_status 取得失敗: %s", exc)\n')
        new_lines.append('\n')
        new_lines.append('    db = AppContainer.db()\n')
        new_lines.append('    if db is None:\n')
        new_lines.append('        return {"is_running": False, "message": "タスクが見つかりません", "logs": []}\n')
        skip = True
    elif skip:
        if 'async with db.get_session()' in line:
            new_lines.append(line)
            skip = False
    else:
        new_lines.append(line)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Updated tasks.py')
