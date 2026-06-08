import os
from datetime import timedelta, datetime, timezone

from pydantic import ValidationError
from pyrogram import Client
from pyrogram.errors import RPCError
from telegram.ext import Application

import aimods_bot.src.helpers.constants.constants as constants
from aimods_bot.src.core.config_loader import load_configuration
from aimods_bot.src.core.customcontext import BotData
from aimods_bot.src.core.pydantic import Configuration, JobInfo, CommandConfig
from aimods_bot.src.helpers.constants.constants import (
    SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE, CHANNEL_JOIN_LINK, GROUP_JOIN_LINK
)
from aimods_bot.src.helpers.job_queue import (
    scheduled_remove_user_request_section_limitation,
    scheduled_remove_completed_requests,
)
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.job_names import (
    parse_job_name,
    AutoRecapJobName,
    RemoveInactiveRequestJobName,
    RequestLimitJobName,
)
from aimods_bot.src.helpers.models.jobs import RemoveCompletedRequestJob, RemoveSectionLimitationJob
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json, set_data_in_json
from aimods_bot.src.helpers.utils.time_utils import get_time_until_next_recap, get_last_monday_midnight
from aimods_bot.src.tasks.channel_recap import create_and_send_recaps

log = logger.getChild(__name__)


# ============================================================================
# ORCHESTRATOR
# ============================================================================

async def set_application_data(application: Application) -> None:
    """
    Punto d'ingresso del post_init: valida/popola bot_data, sincronizza dati
    statici, ripianifica i job persistiti e avvia le risorse esterne.
    """
    bot_data = _ensure_bot_data(application)

    # Tutta la sincronizzazione è subordinata a una configurazione valida:
    # se il caricamento fallisce manteniamo i dati precedenti e usciamo.
    if not _apply_configuration(bot_data):
        return

    await _sync_group_and_admins(application, bot_data)
    await _sync_static_texts(bot_data)
    await _sync_commands(bot_data)
    await _sync_hashtags(bot_data)

    application.bot_data.base_path = None

    _reschedule_persisted_jobs(application, bot_data)
    _setup_auto_recap(application, bot_data)

    await _init_pyrogram()
    await _handle_restart_flag(application)
    _apply_runtime_overrides(application)


# ============================================================================
# BOT DATA / CONFIGURATION
# ============================================================================

def _ensure_bot_data(application: Application) -> BotData:
    """Garantisce che application.bot_data sia un BotData valido."""
    try:
        if isinstance(application.bot_data, BotData):
            return application.bot_data
        bot_data = BotData.model_validate(application.bot_data)
    except ValidationError as e:
        log.error(f"Errori di struttura in Bot Data: {e}\n\nInizializzo.")
        bot_data = BotData()

    application.bot_data = bot_data
    return bot_data


def _apply_configuration(bot_data: BotData) -> bool:
    """
    Carica e valida la configurazione YAML. Ritorna True se applicata,
    False se non valida (in tal caso mantiene quella precedente).
    """
    configuration = load_configuration()
    try:
        validated_config = Configuration.model_validate(configuration)
    except ValidationError as e:
        log.error(f"Invalid configuration: {e}. I will use the old one.")
        return False

    bot_data.configuration = validated_config
    return True


# ============================================================================
# STATIC DATA SYNC
# ============================================================================

async def _sync_group_and_admins(application: Application, bot_data: BotData) -> None:
    group_id_env = os.getenv("GROUP_CHAT_ID")

    if group_id_env is None or not group_id_env.isnumeric():
        raise ValueError(f"GROUP_CHAT_ID env variable not found or not numeric ({group_id_env})!")

    group_chat_id = int(group_id_env)
    bot_data.group_chat_id = group_chat_id

    # noinspection PyTypeChecker
    admins = await get_admins(app=application, chat_id=bot_data.group_chat_id)
    bot_data.admins = admins


async def _sync_static_texts(bot_data: BotData) -> None:
    texts = await get_data_from_json("texts")

    user_joined = texts.get("user_joined_message_text")
    bot_data.user_joined_message_text = user_joined

    rules = texts.get("rules_text")
    bot_data.rules_text = rules


async def _sync_commands(bot_data: BotData) -> None:
    json_commands = await get_data_from_json("commands")
    commands = {key: CommandConfig(**value) for key, value in json_commands.items()}
    bot_data.commands = commands


async def _sync_hashtags(bot_data: BotData) -> None:
    hashtags = await get_data_from_json("hashtags")
    bot_data.hashtags = hashtags


# ============================================================================
# JOB RESCHEDULING (persisted -> live)
# ============================================================================

def _reschedule_persisted_jobs(application: Application, bot_data: BotData) -> None:
    """
    Itera i job persistiti, li ripianifica tramite nomi tipizzati e ricostruisce
    bot_data.jobs con i soli job ancora attivi. La voce auto_recap viene scartata
    qui e ricreata da _setup_auto_recap.
    """
    now = datetime.now(timezone.utc)
    surviving: dict[str, JobInfo] = {}

    for name, info in bot_data.jobs.items():
        parsed = parse_job_name(name)

        if parsed is None:
            # Chiave legacy/sconosciuta: la conservo per non perdere dati.
            log.warning(f"Unrecognized persisted job name '{name}', keeping as-is.")
            surviving[name] = info
            continue

        match parsed:
            case AutoRecapJobName():
                # Gestito interamente in _setup_auto_recap
                surviving[name] = info

            case RemoveInactiveRequestJobName() as p:
                kept = _reschedule_remove_inactive(application, bot_data, p, info, now)
                if kept is not None:
                    surviving[name] = kept

            case RequestLimitJobName() as p:
                kept = _reschedule_request_limit(application, bot_data, p, info, now)
                if kept is not None:
                    surviving[name] = kept

            case _:
                # Tipi senza ripianificazione al boot (es.: cooldown, opening check).
                surviving[name] = info

    bot_data.jobs = surviving


# noinspection PyUnresolvedReferences
def _reschedule_remove_inactive(
        application: Application,
        bot_data: BotData,
        parsed: RemoveInactiveRequestJobName,
        info: JobInfo,
        now: datetime,
) -> JobInfo | None:
    if not info or info.executed or not info.next_date:
        return None

    if info.next_date <= now:
        # Scaduto mentre il bot era offline: rimuovo la richiesta.
        bot_data.active_requests.pop(parsed.request_id, None)
        return None

    application.job_queue.run_once(
        callback=scheduled_remove_completed_requests,
        when=info.next_date,
        data=RemoveCompletedRequestJob(request_id=parsed.request_id),
        name=str(parsed),
    )
    return info


# noinspection PyUnresolvedReferences
def _reschedule_request_limit(
        application: Application,
        bot_data: BotData,
        parsed: RequestLimitJobName,
        info: JobInfo,
        now: datetime,
) -> JobInfo | None:
    if not info or info.executed:
        return None

    user_lim = bot_data.user_limitations.get(parsed.user_id)
    if not user_lim or not user_lim.requests:
        return None

    # Il nome job codifica UNA sezione: ripianifico solo la limitazione che la matcha.
    limitation = next(
        (l for l in user_lim.requests if l.section == parsed.section),
        None,
    )

    if limitation is None:
        # Job orfano (limitazione già rimossa altrove): lo scarto.
        return None

    if limitation.until is None:
        # Permanente: la limitazione resta, ma non serve job di rimozione.
        return None

    if limitation.until < now:
        # Scaduta offline: rimuovo la limitazione e scarto il job.
        user_lim.requests = [l for l in user_lim.requests if l.section != parsed.section]
        return None

    application.job_queue.run_once(
        callback=scheduled_remove_user_request_section_limitation,
        when=limitation.until,
        data=RemoveSectionLimitationJob(user_id=parsed.user_id, section=parsed.section),
        name=str(parsed),
    )
    return JobInfo(next_date=limitation.until, executed=False)


# noinspection PyUnresolvedReferences
def _setup_auto_recap(application: Application, bot_data: BotData) -> None:
    """
    Esegue il recap eventualmente saltato mentre il bot era offline, quindi
    pianifica il job ripetuto settimanale e ne registra il JobInfo.
    """
    job_name = str(AutoRecapJobName())
    previous = bot_data.jobs.pop(job_name, None)

    window_start = get_last_monday_midnight()
    already_done_this_window = (
            bot_data.last_auto_recap is not None
            and bot_data.last_auto_recap >= window_start
    )
    missed = (
            previous is not None
            and previous.next_date is not None
            and not previous.executed
            and previous.next_date <= datetime.now(timezone.utc)
            and not already_done_this_window
    )
    if missed:
        log.info("Missed auto-recap detected; scheduling immediate run.")
        application.job_queue.run_once(callback=create_and_send_recaps, when=1)
        bot_data.last_auto_recap = datetime.now(timezone.utc)

    time_until_next_recap = get_time_until_next_recap()
    job = application.job_queue.run_repeating(
        callback=create_and_send_recaps,
        interval=timedelta(days=7),
        first=time_until_next_recap,
        name=job_name,
    )
    log.info(f"Next recap settled at {job.next_t}")

    bot_data.jobs[job_name] = JobInfo(next_date=job.next_t, executed=False)


# ============================================================================
# EXTERNAL RESOURCES / RUNTIME
# ============================================================================

async def _init_pyrogram() -> None:
    try:
        pyro_inst = Client(
            name="bridge_bot",
            api_id=os.getenv("API_ID"),
            api_hash=os.getenv("API_HASH"),
            bot_token=os.getenv("BOT_TOKEN"),
        )
    except RPCError as e:
        log.error(f"Failed to initialize Pyrogram client: {e}")
        raise

    constants.pyro_instance = pyro_inst
    await constants.pyro_instance.start()


async def _handle_restart_flag(application: Application) -> None:
    r = await get_data_from_json("restarting")
    if not r.get("toggle", False):
        return

    await application.bot.send_message(
        chat_id=r["user_id"],
        text="ℹ️ Bot Riavviato Correttamente",
    )
    await set_data_in_json(key=["restarting", "toggle"], value=False)
    await set_data_in_json(key=["restarting", "user_id"], value=0)


def _apply_runtime_overrides(application: Application) -> None:
    application.bot_data.configuration.settings.request.cancel_timer = (
        SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE
    )
    application.bot_data.channel_join_link = CHANNEL_JOIN_LINK
    application.bot_data.group_join_link = GROUP_JOIN_LINK


# ============================================================================
# HELPERS (unchanged)
# ============================================================================

async def get_admins(app: Application, chat_id: int) -> dict:
    """Retrieves the list of administrators for the group chat."""
    admins = await app.bot.get_chat_administrators(chat_id=chat_id)
    return {admin["user"].id: admin["user"].name for admin in admins}
