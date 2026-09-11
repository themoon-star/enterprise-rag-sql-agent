"""PostgreSQL schema 探测与只读查询执行器。"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from trustquery.datasources import CredentialCipher, DatasourceRecord
from trustquery.sql.validator import ValidatedQuery


class SqlExecutionError(RuntimeError):
    """安全查询在数据库执行阶段失败。"""


@dataclass(frozen=True, slots=True)
class QueryExecution:
    """数据库返回的列名与行数据。"""

    columns: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]


class PostgresExecutor:
    """使用独立连接、只读事务和语句超时执行查询。"""

    def __init__(self, cipher: CredentialCipher) -> None:
        self.cipher = cipher

    async def introspect(self, datasource: DatasourceRecord) -> dict[str, tuple[str, ...]]:
        """只读取白名单表的列名，供 SQL 生成器构造上下文。"""

        query = text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name IN :tables "
            "ORDER BY table_name, ordinal_position"
        ).bindparams(bindparam("tables", expanding=True))
        engine = self._engine(datasource)
        try:
            async with engine.connect() as connection, connection.begin():
                await connection.execute(text("SET TRANSACTION READ ONLY"))
                rows = (await connection.execute(query, {"tables": sorted(datasource.allowed_tables)})).all()
        except Exception as exc:
            raise SqlExecutionError("无法读取数据源 schema") from exc
        finally:
            await engine.dispose()

        schema: dict[str, list[str]] = {}
        for table_name, column_name in rows:
            schema.setdefault(table_name, []).append(column_name)
        return {table: tuple(columns) for table, columns in schema.items()}

    async def execute(self, datasource: DatasourceRecord, query: ValidatedQuery) -> QueryExecution:
        """在数据库只读事务中执行已经通过应用层校验的查询。"""

        engine = self._engine(datasource)
        timeout = int(datasource.statement_timeout_ms)
        try:
            async with engine.connect() as connection, connection.begin():
                await connection.execute(text("SET TRANSACTION READ ONLY"))
                await connection.execute(text(f"SET LOCAL statement_timeout = '{timeout}ms'"))
                result = await connection.execute(text(query.sql))
                rows = tuple(dict(row) for row in result.mappings().all())
                return QueryExecution(columns=tuple(result.keys()), rows=rows)
        except Exception as exc:
            raise SqlExecutionError("只读查询执行失败") from exc
        finally:
            await engine.dispose()

    def _engine(self, datasource: DatasourceRecord):
        raw_url = make_url(self.cipher.decrypt(datasource.encrypted_url))
        async_url = raw_url.set(drivername="postgresql+asyncpg")
        return create_async_engine(async_url)
