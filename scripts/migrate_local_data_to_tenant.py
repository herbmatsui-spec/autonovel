import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.backend.database.models import Base, User, Book
from src.backend.security.password import hash_password

# 既存のデータベースファイル
DB_URL = "sqlite+aiosqlite:///autonovel.db"

async def migrate_data():
    engine = create_async_engine(DB_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. 管理者ユーザーの作成
        admin = User(
            email="admin@autonovel.local",
            hashed_password=hash_password("admin_password_change_me"),
            display_name="Admin",
            role="admin"
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        print(f"Created admin user: {admin.id}")

        # 2. user_id が NULL の Book を検索
        from sqlalchemy import select
        result = await session.execute(select(Book).where(Book.user_id == None))
        books = result.scalars().all()

        # 3. user_id を紐付け
        for book in books:
            book.user_id = admin.id
            print(f"Migrated book '{book.title}' to user {admin.id}")

        await session.commit()
        print("Migration completed.")

if __name__ == "__main__":
    asyncio.run(migrate_data())
