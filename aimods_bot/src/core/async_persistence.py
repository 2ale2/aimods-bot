import asyncio
import json
from logging import getLogger
from typing import Any, Dict, List, Optional, Tuple
from pydantic import ValidationError

import asyncpg
from telegram.ext import DictPersistence

from aimods_bot.src.core.customcontext import BotData
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
        __init__ non fa I/O. Qui chiamiamo solo super().__init__(**kwargs)
        per fissare store_data / update_interval di PTB. Il load vero avviene in _initialize().
        """
        if not url or not url.startswith("postgresql://"):
            raise TypeError(f"{url} non è una PostgreSQL URL valida.")
        self.url = url
        self.on_flush = on_flush
        self.coalesce_delay = coalesce_delay
        self.logger = getLogger(__name__)

        self._pool: Optional[asyncpg.Pool] = None
        self._initialized = False

        self._flush_lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._flush_pending = False

        super().__init__(**kwargs)

    async def initialize(self) -> None:
        await self._initialize()

    async def _initialize(self) -> None:
        if self._initialized:
            return

        # noinspection PyUnresolvedReferences
        self._pool = await asyncpg.create_pool(
            dsn=self.url,
            min_size=1,
            max_size=10,
            timeout=10
        )

        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS persistence (
                    id SMALLINT PRIMARY KEY DEFAULT 1,
                    data JSONB NOT NULL
                );
            """)

            row = await conn.fetchrow("SELECT data FROM persistence WHERE id = 1;")
            if row is None:
                await conn.execute(
                    "INSERT INTO persistence (id, data) VALUES (1, $1::jsonb);",
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

        user_data_json = raw.get("user_data", "{}")
        chat_data_json = raw.get("chat_data", "{}")
        bot_data_json = raw.get("bot_data", "{}")
        conversations_json = raw.get("conversations", "{}")
        callback_data_json = raw.get("callback_data_json", "")

        self._user_data = None
        self._chat_data = None
        self._bot_data = None
        self._callback_data = None
        self._conversations = None

        self._user_data_json = user_data_json
        self._chat_data_json = chat_data_json
        self._bot_data_json = bot_data_json
        self._conversations_json = conversations_json
        self._callback_data_json = callback_data_json

        self._initialized = True
        self.logger.info("Database loaded successfully (async pool).")

    @staticmethod
    def _dump_pydantic(obj: BotData) -> Dict[str, Any]:
        return obj.model_dump()

    @staticmethod
    def _load_bot_data(raw: Optional[Dict[str, Any]]) -> BotData:
        if raw is None:
            return BotData()
        try:
            return BotData.model_validate(raw)
        except ValidationError:
            log.warning("Something was wrong with persistence pydantic validation. Parsing what I can.")
            return migrate_bot_data(raw)

    def _dump_into_json(self) -> Dict[str, Any]:
        """
        Costruisce il payload logico da salvare.
        Usiamo la chiave 'callback_data_json' (coerente con DictPersistence).
        """
        return {
            "chat_data": self.chat_data_json,
            "user_data": self.user_data_json,
            "bot_data": self.bot_data_json,
            "conversations": self.conversations_json,
            "callback_data_json": self.callback_data_json,
        }

    async def _update_database(self) -> None:
        """
        Scrive lo stato nel DB usando il pool. Mantiene il formato fisico storico:
        data = {"jsondata": "<stringa json>"}.
        """
        if not self._initialized:
            await self._initialize()
        assert self._pool is not None

        logical = self._dump_into_json()
        payload_text = json.dumps(logical)
        try:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    # noinspection SqlWithoutWhere
                    await conn.execute(
                        """
                        INSERT INTO persistence (id, data)
                        VALUES (1, $1::jsonb)
                        ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
                        """,
                        payload_text,
                    )
            self.logger.info("Updated persistence successfully.")
        except Exception as exc:
            self.logger.error("Failed to save data in the database (async).", exc_info=exc)
            raise

    # ---------- Coalescing dei flush ravvicinati ----------

    async def _schedule_flush(self) -> None:
        """
        Raggruppa più update vicini in un unico write dopo coalesce_delay.
        """
        self._flush_pending = True
        if self._flush_task and not self._flush_task.done():
            return
        self._flush_task = asyncio.create_task(self._flush_after_delay())

    async def _flush_after_delay(self) -> None:
        await asyncio.sleep(self.coalesce_delay)
        async with self._flush_lock:
            if self._flush_pending:
                await self._update_database()
                self._flush_pending = False

    # ---------- Override dei metodi di DictPersistence ----------

    async def get_bot_data(self) -> BotData:  # type: ignore[override]
        """
        DictPersistence per default restituisce un dict.
        Noi qui ricostruiamo e ritorniamo BotData per compatibilità con ContextTypes(bot_data=BotData).
        """
        if not self._initialized:
            await self._initialize()

        # noinspection PyTypeChecker
        base_dict: Dict[str, Any] = await super().get_bot_data()
        return self._load_bot_data(base_dict)

    async def update_conversation(self, name: str, key: Tuple[int, ...], new_state: Optional[object]) -> None:
        await super().update_conversation(name, key, new_state)
        if not self.on_flush:
            await self._schedule_flush()

    async def update_user_data(self, user_id: int, data: Dict) -> None:
        await super().update_user_data(user_id, data)
        if not self.on_flush:
            await self._schedule_flush()

    async def update_chat_data(self, chat_id: int, data: Dict) -> None:
        await super().update_chat_data(chat_id, data)
        if not self.on_flush:
            await self._schedule_flush()

    async def update_bot_data(self, data: Any) -> None:
        """
        PTB (con ContextTypes.bot_data=BotData) passerà istanze BotData qui.
        Convertiamo in dict JSON-serializzabile e deleghiamo a DictPersistence.
        """
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
        Qui forziamo subito la write.
        """
        async with self._flush_lock:
            self._flush_pending = False
            await self._update_database()

    async def aclose(self) -> None:
        # chiudi eventuale task di coalescing
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except Exception:
                pass

        if self._pool:
            await self._pool.close()
            self._pool = None
            self.logger.info("Database pool closed.")


# ======== FUNZIONI UTILITY ========

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

