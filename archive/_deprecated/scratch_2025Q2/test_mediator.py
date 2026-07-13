import asyncio
import sys

sys.path.append(r"d:\claude2")
from core.container import AppContainer


async def main():
    print("Initializing AppContainer...")
    container = AppContainer()
    container.config.from_dict({
        "DB_PATH": "test.db",
        "COOLDOWN_BASE": 1,
        "COOLDOWN_MIN": 1,
        "COOLDOWN_MAX": 1,
    })
    container.api_key.override("test_key")

    # Try resolving the agents
    print("Resolving PlanningAgent...")
    planner = container.planner()
    print("PlanningAgent mediator:", planner.mediator)

    print("Resolving WritingAgent...")
    writer = container.writer()
    print("WritingAgent mediator:", writer.mediator)

    print("Mediator Handlers:", writer.mediator._handlers)
    print("Success!")

if __name__ == "__main__":
    asyncio.run(main())

