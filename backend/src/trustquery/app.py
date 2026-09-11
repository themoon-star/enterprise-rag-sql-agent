"""FastAPI 应用入口。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from trustquery.api import router
from trustquery.config import Settings, get_settings
from trustquery.datasources import CredentialCipher
from trustquery.db import Database
from trustquery.demo import bootstrap_demo
from trustquery.llm import OpenAICompatibleClient
from trustquery.rag.generator import ExtractiveAnswerGenerator, OpenAIAnswerGenerator
from trustquery.sql.executor import PostgresExecutor
from trustquery.sql.generator import DeterministicSqlGenerator, OpenAISqlGenerator


def create_app(settings: Settings | None = None) -> FastAPI:
    """创建可注入配置的 TrustQuery API 应用。"""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved_settings = settings or get_settings()
        database = Database(resolved_settings.database_url)
        app.state.settings = resolved_settings
        app.state.database = database
        app.state.model_client = None
        if resolved_settings.llm_mode == "openai":
            if resolved_settings.llm_api_key is None or resolved_settings.llm_model is None:
                raise RuntimeError("在线模型配置不完整")
            model_client = OpenAICompatibleClient(
                base_url=resolved_settings.llm_base_url,
                api_key=resolved_settings.llm_api_key.get_secret_value(),
                model=resolved_settings.llm_model,
            )
            app.state.model_client = model_client
            app.state.rag_answer_generator = OpenAIAnswerGenerator(model_client)
            app.state.sql_generator = OpenAISqlGenerator(model_client)
        else:
            app.state.rag_answer_generator = ExtractiveAnswerGenerator()
            app.state.sql_generator = DeterministicSqlGenerator()
        cipher = CredentialCipher(resolved_settings.credential_encryption_key)
        app.state.sql_executor = PostgresExecutor(cipher)
        if resolved_settings.auto_create_schema:
            await database.create_schema()
        if resolved_settings.demo_mode:
            async with database.sessions() as session:
                await bootstrap_demo(session, resolved_settings, cipher)
        yield
        if app.state.model_client is not None:
            await app.state.model_client.close()
        await database.close()

    application = FastAPI(title="TrustQuery API", version="0.1.0", lifespan=lifespan)
    application.include_router(router)

    @application.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
