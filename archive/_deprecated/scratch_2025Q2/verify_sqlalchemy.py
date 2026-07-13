import asyncio

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine


async def main():
    db_path = "temp_init.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        print("PRAGMAs set!")
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

    async with engine.connect() as conn:
        print("SQLAlchemy connection:", conn)
        raw_conn = await conn.get_raw_connection()
        aiosqlite_conn = raw_conn._connection
        print("Raw aiosqlite connection:", aiosqlite_conn)
        cursor = await aiosqlite_conn.execute("SELECT 1;")
        res = await cursor.fetchone()
        print("Result:", res)

if __name__ == "__main__":
    asyncio.run(main())

