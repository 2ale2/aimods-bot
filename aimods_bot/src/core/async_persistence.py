import asyncio
import json
from logging import getLogger
from typing import Any, Dict, List, Optional, Tuple, Union

import asyncpg
from pydantic import ValidationError
from telegram.ext import DictPersistence

from aimods_bot.src.core.customcontext import BotData, ChatData, UserData
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild(__name__)
CDCData = Tuple[List[Tuple[str, float, Dict[str, Any]]], Dict[str, str]]


class AsyncPostgresPersistence(DictPersistence):
    """
    Persistenza async basata su asyncpg + pool, compatibile con PTB DictPersistence (v22.x).
    Usa la factory async: await AsyncPostgresPersistence.create(url=..., on_flush=..., coalesce_delay=...)
    """

    def __init__(
            self,
            url: str,
            on_flush: bool = False,
            coalesce_delay: float = 0.1,
            **kwargs: Any,
    ) -> None:
        """
        Inizializza la persistence caricando i dati dal database
        """
        if not url or not url.startswith("postgresql://"):
            raise TypeError(f"{url} non è una PostgreSQL URL valida.")

        self.url = url
        self.on_flush = on_flush
        self.coalesce_delay = coalesce_delay
        self.logger = getLogger(__name__)

        self._pool: Optional[asyncpg.Pool] = None
        self._initialized = False
        self._pool_lock = None
        self._flush_lock = None
        self._flush_task: Optional[asyncio.Task] = None
        self._flush_pending = False

        persistence_data = self._load_from_database_sync()

        # Passa i dati caricati a DictPersistence
        super().__init__(
            **persistence_data,
            **kwargs
        )

    def _load_from_database_sync(self) -> Dict[str, str]:
        """
        Carica i dati di persistenza dal database in modo sincrono
        """

        async def _load_async():
            # noinspection PyUnresolvedReferences
            pool = await asyncpg.create_pool(dsn=self.url, min_size=1, max_size=2, timeout=10)

            try:
                async with pool.acquire() as conn:
                    await conn.execute("""
                                       CREATE TABLE IF NOT EXISTS persistence_test
                                       (
                                           id   SMALLINT PRIMARY KEY DEFAULT 1,
                                           data JSONB NOT NULL
                                       );
                                       """)

                    row = await conn.fetchrow("SELECT data FROM persistence_test WHERE id = 1;")
                    if row is None:
                        await conn.execute(
                            "INSERT INTO persistence_test (id, data) VALUES (1, $1::jsonb);",
                            json.dumps({})
                        )
                        raw: Dict[str, Any] = {}
                    else:
                        payload = row["data"]
                        if isinstance(payload, dict):
                            raw = payload
                        else:
                            try:
                                raw = json.loads(payload) if payload else {}
                            except Exception:
                                raw = {}

                return {
                    "user_data_json": raw.get("user_data", "{}"),
                    "chat_data_json": raw.get("chat_data", "{}"),
                    "bot_data_json": raw.get("bot_data", "{}"),
                    "conversations_json": raw.get("conversations", "{}"),
                    "callback_data_json": raw.get("callback_data_json", ""),
                }
            finally:
                await pool.close()

        return asyncio.run(_load_async())

    async def _ensure_pool(self) -> None:
        """
        Assicura che il pool sia inizializzato nel loop corrente
        """
        if self._pool is not None:
            return

        if self._pool_lock is None:
            self._pool_lock = asyncio.Lock()
        if self._flush_lock is None:
            self._flush_lock = asyncio.Lock()

        async with self._pool_lock:
            if self._pool is not None:
                return

            try:
                # noinspection PyUnresolvedReferences
                self._pool = await asyncpg.create_pool(
                    dsn=self.url,
                    min_size=1,
                    max_size=10,
                    timeout=10
                )
                self._initialized = True
                self.logger.info("Database pool initialized successfully in PTB loop.")
            except Exception as e:
                self.logger.error(f"Failed to create database pool: {e}")
                raise

    async def initialize(self) -> None:
        """Per compatibilità con PTB"""
        await self._ensure_pool()

    @staticmethod
    def _dump_pydantic(obj: Union[BotData, ChatData, UserData]) -> Dict[str, Any]:
        if isinstance(obj, (ChatData, UserData)):
            return obj.model_dump(mode="json", exclude={'ephemeral'})
        return obj.model_dump(mode="json")

    @staticmethod
    def _load_bot_data(raw: Optional[Dict[str, Any]]) -> BotData:
        if raw is None:
            return BotData()
        try:
            return BotData.model_validate(raw)
        except ValidationError:
            log.warning("Something was wrong with persistence pydantic validation. Parsing what I can.")
            return migrate_bot_data(raw)

    @staticmethod
    def _load_user_data(raw: Optional[Dict[str, Any]]) -> UserData:
        if raw is None:
            return UserData()
        try:
            return UserData.model_validate(raw)
        except ValidationError:
            log.warning("UserData validation failed, building empty object.")
            # It's dangerous loading an empty object. Consider building a migrate method just like bot_data
            return UserData()

    @staticmethod
    def _load_chat_data(raw: Optional[Dict[str, Any]]) -> ChatData:
        if raw is None:
            return ChatData()
        try:
            return ChatData.model_validate(raw)
        except ValidationError:
            log.warning("ChatData validation failed, building empty object.")
            # It's dangerous loading an empty object. Consider building a migrate method just like bot_data
            return ChatData()

    def _dump_into_json(self) -> Dict[str, Any]:
        return {
            "chat_data": self.chat_data_json,
            "user_data": self.user_data_json,
            "bot_data": self.bot_data_json,
            "conversations": self.conversations_json,
            "callback_data_json": self.callback_data_json,
        }

    async def _update_database(self) -> None:
        await self._ensure_pool()
        assert self._pool is not None

        logical = self._dump_into_json()
        payload_text = json.dumps(logical)

        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        """
                        INSERT INTO persistence_test (id, data)
                        VALUES (1, $1::jsonb)
                        ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
                        """,
                        payload_text,
                    )
            self.logger.info("Updated persistence successfully.")
        except Exception as exc:
            self.logger.error("Failed to save data in the database (async).", exc_info=exc)

    async def _schedule_flush(self) -> None:
        """
        Raggruppa più update vicini in un unico write dopo coalesce_delay.
        """
        if self._flush_lock is None:
            self._flush_lock = asyncio.Lock()

        self._flush_pending = True
        if self._flush_task and not self._flush_task.done():
            return

        try:
            self._flush_task = asyncio.create_task(self._flush_after_delay())
        except RuntimeError:
            self.logger.warning("Cannot schedule flush: event loop is closed")

    async def _flush_after_delay(self) -> None:
        try:
            await asyncio.sleep(self.coalesce_delay)
            if self._flush_lock is None:
                self._flush_lock = asyncio.Lock()

            async with self._flush_lock:
                if self._flush_pending:
                    await self._update_database()
                    self._flush_pending = False
        except asyncio.CancelledError:
            # Task cancellato durante lo shutdown
            pass
        except Exception as e:
            self.logger.error(f"Error in flush after delay: {e}", exc_info=True)

    async def get_bot_data(self) -> BotData:
        await self._ensure_pool()
        base_dict: Dict[str, Any] = await super().get_bot_data()
        return self._load_bot_data(base_dict)

    async def get_chat_data(self) -> ChatData:
        await self._ensure_pool()
        base_dict: Dict[str, Any] = await super().get_chat_data()
        return self._load_chat_data(base_dict)

    async def get_user_data(self) -> UserData:
        await self._ensure_pool()
        base_dict: Dict[str, Any] = await super().get_user_data()
        return self._load_user_data(base_dict)

    async def update_conversation(self, name: str, key: Tuple[int, ...], new_state: Optional[object]) -> None:
        await super().update_conversation(name, key, new_state)
        if not self.on_flush:
            await self._schedule_flush()

    async def update_user_data(self, user_id: int, data: Any) -> None:
        payload = self._dump_pydantic(data)
        await super().update_user_data(user_id, payload)
        if not self.on_flush:
            await self._schedule_flush()

    async def update_chat_data(self, chat_id: int, data: Any) -> None:
        payload = self._dump_pydantic(data)
        await super().update_chat_data(chat_id, payload)
        if not self.on_flush:
            await self._schedule_flush()

    async def update_bot_data(self, data: Any) -> None:
        payload = self._dump_pydantic(data)
        await super().update_bot_data(payload)
        if not self.on_flush:
            await self._schedule_flush()

    async def update_callback_data(self, data: CDCData) -> None:
        await super().update_callback_data(data)
        if not self.on_flush:
            await self._schedule_flush()

    async def flush(self) -> None:
        """
        PTB chiama flush() secondo update_interval o allo shutdown.
        """
        try:
            if self._flush_lock is None:
                self._flush_lock = asyncio.Lock()

            async with self._flush_lock:
                self._flush_pending = False
                await self._update_database()
        except Exception as e:
            self.logger.error(f"Error during flush: {e}", exc_info=True)

    async def aclose(self) -> None:
        """
        Chiusura sicura delle risorse
        """
        self.logger.info("Starting AsyncPostgresPersistence cleanup...")

        # Cancella il task di flush se è ancora in esecuzione
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await asyncio.wait_for(self._flush_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                self.logger.error(f"Error cancelling flush task: {e}")

        # Flush finale prima di chiudere
        if self._pool and not self._pool._closed:
            try:
                if self._flush_pending:
                    await self._update_database()
            except Exception as e:
                self.logger.error(f"Error in final flush: {e}")

        # Chiudi il pool
        if self._pool and not self._pool._closed:
            try:
                await asyncio.wait_for(self._pool.close(), timeout=5.0)
                self._pool = None
                self.logger.info("Database pool closed successfully.")
            except asyncio.TimeoutError:
                self.logger.warning("Pool close timed out")
            except Exception as e:
                self.logger.error(f"Error closing pool: {e}")


def migrate_bot_data(raw: Dict[str, Any]) -> BotData:
    try:
        return BotData.model_validate(raw)
    except ValidationError:
        pass

    partial: Dict[str, Any] = {}
    for name, field in BotData.model_fields.items():
        if name not in raw:
            continue
        value = raw[name]
        try:
            ta = field.annotation
            from pydantic import TypeAdapter
            partial[name] = TypeAdapter(ta).validate_python(value)
        except Exception:
            continue

    bd = BotData(**partial)

    if getattr(BotData, "model_config", None) and getattr(BotData.model_config, "extra", None) == "allow":
        for k, v in raw.items():
            if k not in partial:
                log.warning(f"Item {k}: {v} not parsed cause of persistence validation error.")
                setattr(bd, k, v)
    return bd
