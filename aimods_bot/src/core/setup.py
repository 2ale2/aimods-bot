import os
import sys

from datetime import timedelta, datetime, timezone, time
from zoneinfo import ZoneInfo
from pydantic import ValidationError
from pyrogram import Client
from pyrogram.errors import RPCError
from telegram.ext import Application
from telegram.error import TelegramError

import aimods_bot.src.helpers.constants.constants as constants
from aimods_bot.src.core.config_loader import load_configuration
from aimods_bot.src.core.customcontext import BotData
from aimods_bot.src.core.pydantic import Configuration, JobInfo, CommandConfig
from aimods_bot.src.helpers.constants.constants import (
    SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE, CHANNEL_JOIN_LINK, GROUP_JOIN_LINK, RequestStatus
)
from aimods_bot.src.helpers.database import fetch_query
from aimods_bot.src.helpers.job_queue import (
    scheduled_remove_user_request_section_limitation,
    scheduled_remove_completed_requests,
    scheduled_send_reminder,
    schedule_unique_job,
    deliver_reminder
)
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.job_names import (
    parse_job_name,
    AutoRecapJobName,
    RemoveInactiveRequestJobName,
    RequestLimitJobName,
    ReminderJobName
)
from aimods_bot.src.helpers.models.jobs import RemoveCompletedRequestJob, RemoveSectionLimitationJob, ReminderJob
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json, set_data_in_json
from aimods_bot.src.helpers.utils.request_utils import request_from_record
from aimods_bot.src.helpers.reminders_utils import list_reminders, update_next_fire
from aimods_bot.src.helpers.utils.reminder_time_utils import advance_past
from aimods_bot.src.helpers.utils.time_utils import get_time_until_next_recap, get_last_monday_midnight
from aimods_bot.src.tasks.channel_recap import create_and_send_recaps, verify_recap_topics

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

    await _load_active_requests(bot_data)
    await _sync_groups_and_admins(application, bot_data)
    await _sync_static_texts(bot_data)
    await _sync_commands(bot_data)
    await _sync_hashtags(bot_data)

    application.bot_data.base_path = None

    _reschedule_persisted_jobs(application, bot_data)
    _reschedule_remove_inactive(application, bot_data)
    await _reschedule_reminders(application)
    await _setup_auto_recap(application, bot_data)

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


async def _load_active_requests(bot_data: BotData) -> None:
    inactive_request_statuses = [
        RequestStatus.COMPLETED.value,
        RequestStatus.REJECTED.value,
        RequestStatus.CANCELLED.value
    ]
    lingering_statuses = [
        RequestStatus.COMPLETED.value,
        RequestStatus.REJECTED.value,
    ]
    cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE
    )

    query = f"""
        SELECT * FROM {constants.REQUESTS_TABLE}
        WHERE status != ALL($1)
           OR (status = ANY($2) AND closed_at IS NOT NULL AND closed_at > $3)
    """
    rows = await fetch_query(
        query=query,
        params=[inactive_request_statuses, lingering_statuses, cutoff]
    )
    if not rows:
        bot_data.active_requests = {}
        return

    loaded = {}
    for row in rows:
        try:
            req = request_from_record(dict(row))
        except Exception as e:
            log.error(f"Skipping malformed active request during load: {e}")
            continue
        if req.id is not None:
            loaded[req.id] = req

    bot_data.active_requests = loaded
    log.info(f"Loaded {len(loaded)} active requests from DB.")


# ============================================================================
# STATIC DATA SYNC
# ============================================================================

async def _sync_groups_and_admins(application: Application, bot_data: BotData) -> None:
    group_id_env = os.getenv("GROUP_CHAT_ID")

    if group_id_env is None or not group_id_env.replace("-", "").isnumeric():
        raise ValueError(f"GROUP_CHAT_ID env variable not found or not numeric ({group_id_env})!")

    group_chat_id = int(group_id_env)
    bot_data.group_chat_id = group_chat_id

    staff_id_env = os.getenv("STAFF_CHAT_ID")

    if staff_id_env is None or not staff_id_env.replace("-", "").isnumeric():
        raise ValueError(f"STAFF_CHAT_ID env variable not found or not numeric ({staff_id_env})!")

    bot_data.staff_chat_id = int(staff_id_env)

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

            case RemoveInactiveRequestJobName():
                # Non più persistiti: rigenerati al boot da closed_at
                # (vedi _reschedule_remove_inactive). Scarto le voci legacy.
                continue

            case RequestLimitJobName() as p:
                kept = _reschedule_request_limit(application, bot_data, p, info, now)
                if kept is not None:
                    surviving[name] = kept

            case _:
                # Tipi senza ripianificazione al boot (es.: cooldown, opening check).
                surviving[name] = info

    bot_data.jobs = surviving


# noinspection PyUnresolvedReferences
def _reschedule_remove_inactive(application: Application, bot_data: BotData) -> None:
    window = timedelta(seconds=SECONDI_RIMOZIONE_RICHIESTE_ATTIVE_COMPLETATE)

    for req in bot_data.active_requests.values():
        if req.status not in (RequestStatus.COMPLETED, RequestStatus.REJECTED):
            continue
        if req.closed_at is None or req.id is None:
            continue

        application.job_queue.run_once(
            callback=scheduled_remove_completed_requests,
            when=req.closed_at + window,
            data=RemoveCompletedRequestJob(request_id=req.id),
            name=str(RemoveInactiveRequestJobName(request_id=req.id)),
        )


async def _reschedule_reminders(application: Application) -> None:
    reminders = await list_reminders(only_enabled=True)
    now = datetime.now(timezone.utc)
    scheduled = 0

    for reminder in reminders:
        if reminder.id is None:
            log.warning("Reminder without ID; skipping...")
            continue

        next_fire, missed = advance_past(reminder, now=now)

        if missed:
            # UN solo messaggio anche con molte occorrenze mancate:
            # bot giù 10 giorni con intervallo 3 => 1 messaggio, non 4.
            try:
                await deliver_reminder(application.bot, reminder, recovery=True)
            except TelegramError as e:
                log.error(f"Recupero reminder {reminder.id} fallito: {e}")
            await update_next_fire(reminder.id, next_fire, last_fired_at=now)

        if next_fire is None:
            log.info(f"Reminder {reminder.id} was one-shot")
            continue

        schedule_unique_job(
            job_queue=application.job_queue,
            job_name=ReminderJobName(reminder_id=reminder.id),
            callback=scheduled_send_reminder,
            when=next_fire,
            data=ReminderJob(reminder_id=reminder.id),
        )
        scheduled += 1

    log.info(f"Rescheduled reminders: {scheduled}/{len(reminders)}")


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
async def _setup_auto_recap(application: Application, bot_data: BotData) -> None:
    """
    Esegue il recap eventualmente saltato mentre il bot era offline, quindi
    pianifica il job ripetuto settimanale.
    """
    await verify_recap_topics()

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

    time_until_next_recap = get_time_until_next_recap()
    next_run = datetime.now(timezone.utc) + time_until_next_recap
    application.job_queue.run_daily(
        callback=create_and_send_recaps,
        time=time(hour=0, minute=0, tzinfo=ZoneInfo("Europe/Rome")),
        days=(0,),  # domenica
        name=job_name,
    )
    log.info(f"Next recap settled at {next_run}")

    bot_data.jobs[job_name] = JobInfo(next_date=next_run, executed=False)


# ============================================================================
# EXTERNAL RESOURCES / RUNTIME
# ============================================================================

async def _init_pyrogram() -> None:
    try:
        api_id = int(os.getenv("API_ID"))
    except (TypeError, ValueError):
        log.error("API_ID must be an integer. Exiting...")
        sys.exit(1)

    # noinspection unbound-local-variable
    pyro_inst = Client(
        name="bridge_bot",
        api_id=api_id,
        api_hash=os.getenv("API_HASH"),
        bot_token=os.getenv("BRIDGE_TOKEN"),
    )

    try:
        await pyro_inst.start()
    except RPCError as e:
        log.error(f"Failed to start Pyrogram client: {e}")
        raise

    constants.pyro_instance = pyro_inst


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
