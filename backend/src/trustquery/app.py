"""FastAPI 应用入口。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from trustquery.api import router
from trustquery.config import Settings, get_settings
from trustquery.db import Database


def create_app(settings: Settings | None = None) -> FastAPI:
    """创建可注入配置的 TrustQuery API 应用。"""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved_settings = settings or get_settings()
        database = Database(resolved_settings.database_url)
        app.state.settings = resolved_settings
        app.state.database = database
        if resolved_settings.auto_create_schema:
            await database.create_schema()
        yield
        await database.close()

    application = FastAPI(title="TrustQuery API", version="0.1.0", lifespan=lifespan)
    application.include_router(router)

    @application.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
