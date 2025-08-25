import re
from typing import Union

from telegram import Update
from telegram.ext import Application, ContextTypes
from aimods_bot.src.helpers.database import fetch_query, execute_query, add_to_table
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json

log = logger.getChild("channel-recap")


async def catch_post_from_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message.text and not update.effective_message.caption:
        return

    text = update.effective_message.caption or update.effective_message.text
    platforms = []
    hashtags = context.bot_data["hashtags"]

    if any(x in text for x in hashtags["platforms"]["Android"]):
        platforms.append("Android")
    if any(x in text for x in hashtags["platforms"]["iOS"]):
        platforms.append("iOS")
    if any(x in text for x in hashtags["platforms"]["Windows"]):
        platforms.append("Windows")
    if any(x in text for x in hashtags["platforms"]["MacOS"]):
        platforms.append("MacOS")
    if any(x in text for x in hashtags["platforms"]["Linux"]):
        platforms.append("Linux")

    if len(platforms) == 0:
        log.warning(f"Software platform(s) not captured in post #{update.effective_message.id} from channel.")
        return

    lines = text.splitlines()
    if "#richiesta" in lines[0]:
        lines.pop(0)

    first_line = re.sub(r"^\W+", "", lines[0])

    software_name = None
    for el in hashtags["software_associations"]:
        if hashtags["software_associations"][el] in text:
            software_name = el
            break

    if software_name is None:
        match = re.match(r"(?m)^\s*(.+?)(?:\s+((?:vt|vT|v|w)(?=\d)\S*|build(?=\d)\S*)(?:\s+(.*))?)?\s*$", first_line, re.IGNORECASE)
        if not match:
            log.warning(f"Software name not captured in post #{update.effective_message.id} from channel.")
            return
        software_name = match.group(1).strip()

    await add_to_table(
        table_name="recap_posts",
        content={
            "post_id": update.effective_message.id,
            "platforms": str(platforms).replace("'", ""),
            "software_name": software_name,
            "link": update.effective_message.link
        }
    )


async def create_and_send_recaps(context: Union[ContextTypes.DEFAULT_TYPE, Application]):
    query = "SELECT * FROM recap_posts"
    res = await fetch_query(query=query)
    if res is None:
        log.warning("Not able to create recaps due to database error: check logs.")
        return

    l = [dict(el) for el in res]

    android_recap_text = "📝 <b>Android – Recap Settimanale</b>\n"
    windows_recap_text = "📝 <b>Windows – Recap Settimanale</b>\n"
    ios_recap_text = "📝 <b>iOS – Recap Settimanale</b>\n"
    macos_recap_text = "📝 <b>MacOS – Recap Settimanale</b>\n"

    send = {
        "Android": False,
        "Windows": False,
        "iOS": False,
        "MacOS": False
    }

    for el in l:
        platforms = el["platforms"]
        new_item = (f"\n🔸 <b>{el['software_name']}</b>\n"
                    f"🔗 <a href=\"{el['link']}\">Link</a>")
        if "Android" in platforms:
            android_recap_text += new_item
            send["Android"] = True
        if "Windows" in platforms:
            windows_recap_text += new_item
            send["Windows"] = True
        if "iOS" in platforms:
            ios_recap_text += new_item
            send["iOS"] = True
        if "MacOS" in platforms:
            macos_recap_text += new_item
            send["MacOS"] = True

    not_sending = [key for key in send.keys() if not send[key]]
    if not_sending:
        log.info(f"Not sending recap for {', '.join(not_sending)} since I have no posts this time.")

    recap_topics = get_data_from_json("forum_topics")["recap"]

    for el in recap_topics:
        if recap_topics[el]["name"] in not_sending:
            continue

        text = ""

        if recap_topics[el]["name"] == "Android":
            text = android_recap_text

        elif recap_topics[el]["name"] == "Windows":
            text = windows_recap_text

        elif recap_topics[el]["name"] == "iOS":
            text = ios_recap_text

        elif recap_topics[el]["name"] == "MacOS":
            text = macos_recap_text

        if text:
            await context.bot.send_message(
                chat_id=context.bot_data["group_chat_id"],
                message_thread_id=int(recap_topics[el]["id"]),
                text=text,
                disable_web_page_preview=True,
                parse_mode="HTML"
            )

            await context.bot.send_sticker(
                chat_id=context.bot_data["group_chat_id"],
                message_thread_id=int(recap_topics[el]["id"]),
                sticker="aimods_bot/misc/images/official_stickers/sticker.webp"
            )

    # noinspection SqlWithoutWhere
    query = "DELETE FROM recap_posts"

    await execute_query(query=query)
