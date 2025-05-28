# modulo per i recap e le task automatiche
from telegram import LinkPreviewOptions
from telegram.ext import Application
from utils import *


async def create_and_send_recaps(context: ContextTypes.DEFAULT_TYPE | Application):
    query = "SELECT * FROM recap_posts"
    res = await execute_query(query=query, for_value=True)
    if res is None:
        bot_logger.warning("Not able to create recaps due to database error: check logs.")
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
        bot_logger.info(f"Not sending recap for {', '.join(not_sending)} since I have no posts this time.")

    recap_topics = get_data_from_json("forum_topics")["recap"]

    for el in recap_topics:
        if recap_topics[el]["name"] in not_sending:
            continue

        if recap_topics[el]["name"] == "Android":
            await context.bot.send_message(
                chat_id=context.bot_data["group_chat_id"],
                message_thread_id=int(el["id"]),
                text=android_recap_text,
                disable_web_page_preview=True
            )
            continue
        if recap_topics[el]["name"] == "Windows":
            await context.bot.send_message(
                chat_id=context.bot_data["group_chat_id"],
                message_thread_id=int(el["id"]),
                text=windows_recap_text,
                disable_web_page_preview=True
            )
            continue
        if recap_topics[el]["name"] == "iOS":
            await context.bot.send_message(
                chat_id=context.bot_data["group_chat_id"],
                message_thread_id=int(el["id"]),
                text=ios_recap_text,
                disable_web_page_preview=True
            )
            continue
        if recap_topics[el]["name"] == "MacOS":
            await context.bot.send_message(
                chat_id=context.bot_data["group_chat_id"],
                message_thread_id=int(el["id"]),
                text=macos_recap_text,
                disable_web_page_preview=True
            )
            continue
