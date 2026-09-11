"""异步数据库连接与会话管理。"""

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    """SQLAlchemy 声明式模型基类。"""


class Database:
    """管理应用使用的异步数据库引擎与会话工厂。"""

    def __init__(self, database_url: str) -> None:
        self.engine = create_async_engine(database_url)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_schema(self) -> None:
        """创建演示环境所需的元数据表。"""

        from trustquery import models as registered_models

        _ = registered_models
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        """释放数据库连接池。"""

        await self.engine.dispose()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """为单个请求提供数据库事务会话。"""

    async with request.app.state.database.sessions() as session:
        yield session
