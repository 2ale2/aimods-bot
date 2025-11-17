import os
import asyncpg
from asyncpg import Pool
from typing import Optional
from contextlib import asynccontextmanager

from aimods_bot.src.core.exceptions import DatabaseBotException
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("database_pool")


class DatabasePool:
    """Gestisce il connection pool PostgreSQL centralizzato per tutta l'applicazione."""
    _pool: Optional[Pool] = None

    @classmethod
    async def get_pool(cls) -> Pool:
        """
        Ottiene o crea il pool di connessioni.

        Returns:
            Pool di connessioni asyncpg.

        Raises:
            DatabaseBotException: Se la creazione del pool fallisce.
        """
        if cls._pool is None:
            try:
                # noinspection PyUnresolvedReferences
                cls._pool = await asyncpg.create_pool(
                    os.getenv("POSTGRES_CONNECTION_URL"),
                    ssl=False,
                    min_size=5,
                    max_size=20,
                    command_timeout=60,
                    max_queries=50000,
                    max_inactive_connection_lifetime=300
                )
                log.info("✅ Connection pool creato con successo")
            except Exception as e:
                raise DatabaseBotException(f"Errore creazione pool: {e}")
        return cls._pool

    @classmethod
    def get_existing_pool(cls) -> Optional[Pool]:
        return cls._pool

    @classmethod
    async def close_pool(cls):
        """Chiude il pool di connessioni."""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            log.info("Connection pool chiuso")

    @classmethod
    def is_initialized(cls) -> bool:
        """Verifica se il pool è già inizializzato."""
        return cls._pool is not None


@asynccontextmanager
async def get_connection():
    """
    Context manager per ottenere una connessione dal pool.

    Yields:
        Connection: Connessione dal pool.

    Example:
        async with get_connection() as conn:
            result = await conn.fetch("SELECT * FROM users")
    """
    pool = await DatabasePool.get_pool()
    async with pool.acquire() as conn:
        yield conn
