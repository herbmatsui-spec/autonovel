path = 'src/backend/routers/tasks.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

old_get_task_status = '''@router.get("/{task_id}/status")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    redis_client = await get_async_redis_client()
    if redis_client is not None:
        try:
            val = await redis_client.get(f"task_status:{task_id}")
            if val:
                data = json.loads(val)
        except Exception as exc:
            # Redis 取得失敗は DB フォールバックへ進む想定だが、原因を追跡できるようログは残す
            logger.warning(
                "Redis task_status 取得失敗、DB にフォールバックします: %s", exc, exc_info=True
            )

    db = AppContainer.db()
    async with db.get_session() as session:
        stmt = select(InternalState).where(InternalState.key == f"task_status:{task_id}")
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
    if not row:
        data = {"is_running": False, "message": "タスクが見つかりません", "logs": []}
    else:
        data = json.loads(row.value)

    # user_id がペイロードに含まれている場合は本人確認を実施
    task_user_id = data.get("user_id")
    if task_user_id and task_user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="このタスクへのアクセス権限がありません")
    return data'''

new_get_task_status = '''@router.get("/{task_id}/status")
async def get_task_status(
    task_id: str,
    current_user: User | None = Depends(get_current_user),
):
    redis_client = await get_async_redis_client()
    data = None
    if redis_client is not None:
        try:
            val = await redis_client.get(f"task_status:{task_id}")
            if val:
                data = json.loads(val)
        except Exception as exc:
            logger.warning(
                "Redis task_status 取得失敗、DB にフォールバックします: %s", exc, exc_info=True
            )

    if data is None:
        db = AppContainer.db()
        if db is not None:
            async with db.get_session() as session:
                stmt = select(InternalState).where(InternalState.key == f"task_status:{task_id}")
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
            if not row:
                data = {"is_running": False, "message": "タスクが見つかりません", "logs": []}
            else:
                data = json.loads(row.value)
        else:
            data = {"is_running": False, "message": "タスクが見つかりません", "logs": []}

    task_user_id = data.get("user_id")
    if task_user_id and current_user and task_user_id != getattr(current_user, "id", None) and getattr(current_user, "role", None) != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="このタスクへのアクセス権限がありません")
    return data'''

text = text.replace(old_get_task_status.replace('\r\n', '\n'), new_get_task_status.replace('\r\n', '\n'))
with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print('tasks.py successfully updated')
