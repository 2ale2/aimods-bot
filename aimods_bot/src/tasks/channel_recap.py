import os
import re
from datetime import datetime, timezone

from telegram import Update, LinkPreviewOptions
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import Application

from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import RECAP_POSTS_TABLE
from aimods_bot.src.helpers.database import fetch_query, add_to_table, execute_query
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.job_names import AutoRecapJobName
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json
from aimods_bot.src.helpers.utils.time_utils import get_last_monday_midnight
from aimods_bot.src.core.pydantic import JobInfo

log = logger.getChild(__name__)

_RECAP_PLATFORMS = ("Android", "Windows", "iOS", "MacOS")

_STICKER_PATH = os.getenv(
    "RECAP_STICKER_PATH",
    "/app/aimods_bot/misc/images/official_stickers/sticker.webp",
)


async def catch_post_from_channel(update: Update, context: CustomContext):
    if not update.effective_message.text and not update.effective_message.caption:
        return

    if not check_post_timestamp(update=update):
        log.info(f"Skipping post {update.effective_message.id} (was published before this week)")
        return

    text = update.effective_message.caption or update.effective_message.text
    hashtags = context.pydb.hashtags

    platforms = [
        platform
        for platform, tags in hashtags["platforms"].items()
        if any(tag in text for tag in tags)
    ]

    if len(platforms) == 0:
        log.warning(f"Software platform(s) not captured in post #{update.effective_message.id} from channel.")
        return

    lines = text.splitlines()
    if "#richiesta" in lines[0].lower():
        lines.pop(0)

    first_line = re.sub(r"^\W+", "", lines[0])

    software_name = None
    for el in hashtags["software_associations"]:
        if hashtags["software_associations"][el] in text:
            software_name = el
            break

    if software_name is None:
        match = re.match(
            r"^\s*(.+?)(?:\s+((?:vt|v|w)(?=\d)\S*|build(?=\d)\S*)(?:\s+(.*))?)?\s*$",
            first_line,
            re.IGNORECASE,
        )
        if not match:
            log.warning(f"Software name not captured in post #{update.effective_message.id} from channel.")
            return
        software_name = match.group(1).strip()

    await add_to_table(
        table_name=RECAP_POSTS_TABLE,
        content={
            "post_id": update.effective_message.id,
            "platforms": str(platforms).replace("'", ""),
            "software_name": software_name,
            "link": update.effective_message.link
        }
    )


def check_post_timestamp(update: Update) -> bool | None:
    """
    Verifica se il post è stato pubblicato a partire dall'ultimo lunedì.
    Ritorna True se il post rientra nella settimana corrente, False altrimenti.
    """
    monday_midnight = get_last_monday_midnight()
    return monday_midnight <= update.effective_message.date


async def verify_recap_topics() -> None:
    """Controlla che ogni piattaforma con recap abbia un topic corrispondente."""
    try:
        recap_topics = (await get_data_from_json("forum_topics"))["recap"]
    except (KeyError, TypeError, ValueError) as e:
        log.error(f"Impossibile leggere i topic di recap da forum_topics.json: {e}")
        return

    names = {topic["name"] for topic in recap_topics.values()}
    missing = set(_RECAP_PLATFORMS) - names
    if missing:
        log.error(
            f"Topic di recap mancanti o con nome non corrispondente in forum_topics.json: "
            f"{sorted(missing)}. Trovati: {sorted(names)}"
        )
    else:
        log.info(f"Topic di recap verificati: {sorted(names)}")


async def create_and_send_recaps(context: CustomContext | Application):
    bot_data = context.pydb if isinstance(context, CustomContext) else context.bot_data

    res = await fetch_query(query=f"SELECT * FROM {RECAP_POSTS_TABLE}")
    if res is None:
        log.warning("Not able to create recaps due to database error: check logs.")
        return

    posts = [dict(el) for el in res]

    recap_texts = {
        platform: f"📝 <b>{platform} – Recap Settimanale</b>\n"
        for platform in _RECAP_PLATFORMS
    }
    send = {key: False for key in recap_texts}

    for el in posts:
        platforms = el["platforms"]
        new_item = (f"\n🔸 <b>{el['software_name']}</b>\n"
                    f"🔗 <a href=\"{el['link']}\">Link</a>")
        matched = False
        for platform in recap_texts:
            if platform in platforms:
                recap_texts[platform] += new_item
                send[platform] = True
                matched = True

        if not matched:
            log.info(
                f"Post #{el['post_id']} ({el['software_name']}, {platforms}) non incluso "
                f"in nessun recap: nessuna piattaforma con topic dedicato."
            )

    not_sending = [key for key, will_send in send.items() if not will_send]
    if not_sending:
        log.info(f"Not sending recap for {', '.join(not_sending)} since I have no posts this time.")

    group_id = bot_data.group_chat_id
    if group_id is None:
        raise ValueError("Group ID must not be None here!")

    recap_topics = (await get_data_from_json("forum_topics"))["recap"]
    sticker_id = None

    for el in recap_topics:
        topic_name = recap_topics[el]["name"]
        if topic_name in not_sending:
            continue

        text = recap_texts.get(topic_name)
        if not text:
            log.warning(
                f"Topic '{topic_name}' of forum_topics.json doesn't match any "
                f"platform with recap ({sorted(recap_texts)}): skipped."
            )
            continue

        thread_id = int(recap_topics[el]["id"])
        try:
            await context.bot.send_message(
                chat_id=group_id,
                message_thread_id=thread_id,
                text=text,
                link_preview_options=LinkPreviewOptions(is_disabled=True),
                parse_mode=ParseMode.HTML,
            )
            sticker_message = await context.bot.send_sticker(
                chat_id=group_id,
                message_thread_id=thread_id,
                sticker=sticker_id or _STICKER_PATH,
            )
            if not sticker_id:
                sticker_id = sticker_message.sticker.file_id
        except TelegramError as e:
            log.error(
                f"Failed to send recap for topic '{topic_name}' (thread {thread_id}): {e}. "
                f"I post di questo recap verranno comunque rimossi: se serve, va rifatto a mano."
            )

    bot_data.last_auto_recap = datetime.now(timezone.utc)

    if posts:
        await execute_query(query=f"TRUNCATE TABLE {RECAP_POSTS_TABLE}")

    name = str(AutoRecapJobName())
    scheduled = context.job_queue.get_jobs_by_name(name)
    bot_data.jobs[name] = JobInfo(next_date=scheduled[0].next_t if scheduled else None, executed=True)
