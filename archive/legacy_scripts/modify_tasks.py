import re

with open('src/backend/tasks.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports after the line "from src.core.observability import with_trace_context"
import_insert = '''from src.backend.database.uow import UnitOfWork
from prompts.manager import prompt_manager
'''
pattern = r'from src\.core\.observability import with_trace_context'
if re.search(pattern, content):
    # Insert after that line
    content = re.sub(pattern, r'\g<0>\n' + import_insert, content)

# Now add the periodic task after the async def _process_outbox_events_async function
# Find the function definition
match = re.search(r'async def _process_outbox_events_async\(\):', content)
if match:
    # Find the next @huey.task() after the function
    search_start = match.end()
    next_decorator = re.search(r'@huey\.task\(\)', content[search_start:])
    if next_decorator:
        # Position to insert is at the start of the decorator (relative to whole string)
        insert_pos = search_start + next_decorator.start()
        new_block = '''\n@huey.periodic_task(crontab(minute='*'))
def save_prompt_metrics():
    logger.info("Saving prompt metrics snapshot...")
    try:
        asyncio.run(_save_prompt_metrics_async())
    except Exception as e:
        logger.error(f"Failed to save prompt metrics: {e}")

async def _save_prompt_metrics_async():
    # Get the PromptManager singleton
    from prompts.manager import prompt_manager
    registry = prompt_manager.registry
    metrics = registry.get_metrics()
    # Get database session
    from config.container import Container
    from src.backend.database.uow import UnitOfWork
    container = Container()
    db = container.db()
    async with UnitOfWork(db=db) as uow:
        await uow.prompt_metrics.save_metrics_snapshot(metrics)
'''
        # Insert the new block before the decorator
        content = content[:insert_pos] + new_block + content[insert_pos:]

with open('src/backend/tasks.py', 'w', encoding='utf-8') as f:
    f.write(content)
