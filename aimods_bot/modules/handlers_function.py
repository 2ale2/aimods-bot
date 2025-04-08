import copy
import os
from datetime import datetime

import pytz
import telegram.error
from pyrogram import utils, enums
from pyrogram.errors import PeerIdInvalid
from pyrogram.types import ChatPermissions
from telegram.constants import ChatMemberStatus
from telegram.ext import ConversationHandler
from constants import Permissions

from aimods_bot.modules.database_functions import add_to_table
from utils import *

RULES_ACCEPTED = 0

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    La risposta dipende dall'utente: se è admin, allora stampo il pannello di controllo; altrimenti do il benvenuto.
    --> Basta semplicemente aggiungere un Benvenuto standard e, se Admin, aggiungere un bottone con "Settings"
    """
    if await is_admin(update.effective_user.id, context):
        # stampa pannello di controllo
        pass
    else:
        # stampa
        pass

    # per ora stampiamo semplicemente il benvenuto
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Hi A&I Mods Staff! :)"
    )


# {DOPPIA VERIFICA
async def new_member_joined_forum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await user_is_banned(
            user_id=update.effective_user.id,
            chat_id=context.bot_data["group_chat_id"],
            context=context
    ):
        message = await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="❌ Il tuo ID è stato <b>bannato</b>.\n\nNon puoi unirti al gruppo.",
            parse_mode="HTML"
        )
        context.job_queue.run_once(
            callback=job_queue_functions.scheduled_delete_message,
            when=10,
            data={
                "message_id": message.message_id,
                "chat_id": update.effective_user.id}
        )
        return ConversationHandler.END

    if update.callback_query is not None:
        await delete_effective_message(update, context)

    inline_keyboard = [
        [
            InlineKeyboardButton(
                text="Ho letto e accetto le regole 🖋",
                callback_data="accept_rules " + str(update.effective_user.id)
            )
        ]
    ]

    keyboard_markup = InlineKeyboardMarkup(
        inline_keyboard=inline_keyboard
    )

    message = await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=context.bot_data["user_joined_message_text"].format(update.effective_user.full_name),
        parse_mode="HTML",
        reply_markup=keyboard_markup,
        link_preview_options=telegram.LinkPreviewOptions(is_disabled=True)
    )

    keyboard = [
        [
            InlineKeyboardButton(
                text="🔄 Ricarica Captcha",
                callback_data="recreate_captcha"
            )
        ]
    ]

    context.job_queue.run_once(
        callback=job_queue_functions.scheduled_edit_message,
        data={
            'chat_id': update.effective_user.id,
            'message_id': message.message_id,
            'text': '⚠️ <b>Non hai completato la verifica</b>.\n\nPer ricaricare la doppia verifica, puoi premere il '
                    'tasto sotto.',
            'reply_markup': InlineKeyboardMarkup(keyboard)
        },
        when=5,  # tempo massimo di accettazione delle regole
        name=f'captcha_failed_{update.effective_user.id}')

    return RULES_ACCEPTED


async def new_member_accepted_the_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if job := context.job_queue.get_jobs_by_name(f'captcha_failed_{update.effective_user.id}'):
        job[0].schedule_removal()

    if str(update.effective_user.id) == update.callback_query.data.split(" ")[1]:
        await context.bot.delete_message(
            chat_id=update.effective_user.id,
            message_id=update.effective_message.message_id
        )
        await context.bot.approve_chat_join_request(
            chat_id=context.bot_data["group_chat_id"],
            user_id=update.effective_user.id
        )
        clean_id = str(context.bot_data["group_chat_id"]).removeprefix("-100")
        clean_url = f"https://t.me/c/{clean_id}/1"

        keyboard = [
            [
                InlineKeyboardButton(
                    text="Vai al Gruppo ↗️",
                    url=clean_url)
            ]
        ]

        await send_action_message_after(
            update=update,
            context=context,
            text="✅ <b>La tua richiesta è stata approvata</b>\n\nLo staff di A&I Mods ti dà il benvenuto. "
                 "Grazie per averci scelto 😃",
            additional_job_data={
                "reply_markup": InlineKeyboardMarkup(keyboard)
            }
        )

        return ConversationHandler.END

# }


async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text_html_urled
    match = re.match(r"^[/!.]([a-zA-Z0-9_]+)(?:\s(.*))?$", message_text)

    if match:
        command = match.group(1)
        args = match.group(2) if len(match.groups()) == 2 else None

        match command:
            case "start":
                await start_command(update=update, context=context)
            case "rules":
                await send_rules(update=update, context=context)
            case "del" | "delmute" | "delban" | "delkick":
                await delete_group_message(update=update, context=context, args=args, command=command, full_command=message_text)
            case "ban" | "unban" | "mute" | "unmute" | "kick" | "warn":
                await limit_user(update=update, context=context, command=command, full_command=message_text)
            case "limit" | "unlimit":
                await limit_user(update=update, context=context, command=command, full_command=message_text)


# COMANDO RIMOZIONE MESSAGGI
async def delete_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE, args: str | None, command: str, full_command: str, log_message=True):
    message_to_delete = copy.deepcopy(update.effective_message.reply_to_message)
    message_from_admin = copy.deepcopy(update.effective_message)
    forwarded_media = None

    await delete_effective_message(update, context)

    if not await is_admin(update.effective_user.id, context):
        await job_queue_functions.send_temporary_message(
            update=update,
            context=context,
            text="⚠️ Solo gli admin possono eseguire questa azione.",
            delay_before=2,  # per la chat action
            delay_delete=10
        )
        return

    if message_to_delete is None or message_to_delete.forum_topic_created is not None:
        await send_private_alert(
            update=update,
            context=context,
            text="ℹ️ INFO\n\nPer poter eliminare un messaggio, selezionalo rispondendovi.",
            delay=1
        )
        return

    if datetime.now((message_date := message_to_delete.date).tzinfo) - message_date > timedelta(hours=48):
        await send_private_alert(
            update=update,
            context=context,
            text="⚠️ Warning\n\nIl messaggio non può essere rimosso, perché è stato mandato più di 48 ore fa.",
            delay=1
        )
        return

    if args:
        reason = ': <b>' + args + "</b>"
    else:
        reason = " (<b>no reason given</b>)"

    answer_text = (f"♻️ Message sent by {message_to_delete.from_user.name} was removed{reason}.\n\n"
                   f"ℹ <i>This message will be deleted in 5min</i>.")

    try:
        if message_to_delete.effective_attachment is not None:
            forwarded_media = await message_to_delete.forward(
                chat_id=os.getenv("DELETED_MEDIA_CHANNEL_ID")
            )
        await message_to_delete.delete()
        if log_message:
            await job_queue_functions.send_temporary_message(
                update=update,
                context=context,
                text=answer_text,
                delay_delete=300
            )
    except telegram.error.BadRequest as e:
        bot_logger.error(f"Errore nella rimozione di un messaggio: {e}")
        await send_private_alert(
            update=update,
            context=context,
            text="❌ Error\n\nIl messaggio non può essere rimosso a causa di un errore. Controlla i log dei comandi.",
            delay=1
        )
    else:
        data_for_database = {
            "message_id": message_to_delete.message_id,
            "admin": message_from_admin.from_user.id,
            "deletion_time": datetime.now(),
            "user_id": message_to_delete.from_user.id,
            "reason": re.sub(r'</?b>|\(|\)|:', '', reason).strip(),
            "content": (message_to_delete.text
                        if message_to_delete.effective_attachment is None
                        else message_to_delete.caption),
            "username": message_to_delete.from_user.name,
            "media": forwarded_media.link if forwarded_media is not None else None,
            "manual": False
        }
        await add_to_table(table_name="deleted_messages", content=data_for_database)

    # opzione 1

    if action := command.replace("del", ""):
        parts = full_command.split(" ", 1)
        if len(parts) > 1:
            full_command = f"/{action} {message_to_delete.from_user.id} {parts[1]}"
        else:
            full_command = f"/{action} {message_to_delete.from_user.id}"

        await limit_user(update = update, context = context, command = action, full_command = full_command)


async def send_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.id)
    except telegram.error.BadRequest:
        pass

    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=context.bot_data["rules_text"],
        parse_mode="HTML"
    )
    keyboard = [
        [
            InlineKeyboardButton(
                text="Close 📖",
                callback_data=f"close {message.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.edit_message_reply_markup(
        chat_id=update.effective_user.id,
        message_id=message.message_id,
        reply_markup=reply_markup
    )


# COMANDO LIMITAZIONE UTENTE
async def limit_user(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str, full_command: str):
    message = copy.deepcopy(update.message)
    await delete_effective_message(update, context)

    if not await is_admin(update.effective_user.id, context):
        await job_queue_functions.send_temporary_message(
            update=update,
            context=context,
            text="⚠️ Solo gli admin possono eseguire questa azione.",
            delay_before=2,  # per la chat action
            delay_delete=10
        )
        return

    parsed = await parse_command(update=update, context=context, command=command, full_command=full_command)

    if parsed["user"] is None:
        if message.reply_to_message is None or message.reply_to_message.forum_topic_created is not None:
            await send_private_alert(
                update=update,
                context=context,
                text="⚠️ Warning\n\n▪️ Se non rispondi ad un messaggio, devi indicare un utente."
            )
            return

    if message.reply_to_message is not None and message.reply_to_message.forum_topic_created is None:
        replied = message.reply_to_message
    else:
        replied = None

    try:
        text = None
        try:
            user = await context.bot_data["pyro_instance"].get_chat_member(
                chat_id=context.bot_data["group_chat_id"],
                user_id=parsed["user"] or replied.from_user.id
            )
        except ValueError:
            await send_private_alert(
                update=update,
                context=context,
                text="⚠️ Warning\n\n▪️ L'utente sembra non esistere."
            )
            return
        if user.status == enums.ChatMemberStatus.LEFT:
            text = "⚠️ Warning\n\n▪️ L'utente non è nel gruppo."
        elif user.status == enums.ChatMemberStatus.ADMINISTRATOR or user.status == enums.ChatMemberStatus.OWNER:
            text = "⚠️ Warning\n\n▪️ Non è consentito limitare gli admin."
        elif user.status == enums.ChatMemberStatus.BANNED:
            text = "⚠️ Warning\n\n▪️ L'utente è bannato."
    except PeerIdInvalid:
        text = "⚠️ Warning\n\n▪️ L'utente non è nel gruppo."

    if text is not None:
        await send_private_alert(
            update=update,
            context=context,
            text=text
        )
        return

    italian_tz = pytz.timezone("Europe/Rome")

    # noinspection PyUnboundLocalVariable
    mention = (
        # se arriviamo a questo punto del codice, user è definita necessariamente
        f'<a href="tg://user?id={user.user.id}">{user.user.first_name}</a>'
        if user.user.username is None
        else f"@{user.user.username}"
    )

    now_italy = datetime.now(tz=italian_tz).replace(tzinfo=None)
    until_date = (now_italy + parsed["duration"]) if parsed["duration"] else utils.zero_datetime()

    # opzione 2

    if "del" in command:
        await delete_group_message(
            update=update,
            context=context,
            args=parsed["message"],
            command="del",
            full_command=f"/del {parsed['message']}" if parsed["message"] is not None else "/del",
            log_message=False
        )
        command = command.replace("del", "")

    if command == "limit" or command == "unlimit":
        p = Permissions
        new_permissions = {}
        permissions_texts = {
            0: "Inviare messaggi",
            1: "Inviare sondaggi",
            2: "Inviare stickers e GIFs",
            3: "Aggiungere Web Previews",
            4: "Invitare altri membri",
            5: "Inviare file audio",
            6: "Inviare documenti",
            7: "Inviare foto",
            8: "Inviare video",
            9: "Inviare note video",
            10: "Inviare note vocali"
        }
        if parsed["permissions"] == [11]:  # "non è un bug, è una feature;)"
            for perm in p:
                new_permissions[perm.name] = True if command == "limit" else False
            if command == "limit":
                service_text = (f"🔓 Utente {mention} (<code>{user.user.id}</code>) non più limitato "
                                f"(<b>tutti i permessi aggiunti</b>).")
            else:
                service_text = (f"🔒 Utente {mention} (<code>{user.user.id}</code>) limitato "
                                f"(<b>tutti i permessi rimossi</b>).")
        else:
            actual = user.permissions.__dict__ if user.permissions is not None else {perm.name: True for perm in p}
            if command == "limit":
                new_permissions = {
                    perm.name: (actual[perm.name] if perm.value not in parsed["permissions"] else False) for perm in p
                }
            else:
                for perm in p:
                    if perm.value not in parsed["permissions"]:
                        new_permissions[perm.name] = True
                    else:
                        new_permissions[perm.name] = actual[perm.name]

        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user.user.id,
            permissions=new_permissions,
            until_date=until_date,
            use_independent_chat_permissions=True
        )

        if parsed["permissions"] != [11]:
            if command == "limit":
                service_text = f"🔒 Utente {mention} (<code>{user.user.id}</code>) <b>limitato</b> "
                if parsed["duration"]:
                    service_text += f"fino al <b>{until_date.strftime('%d %B %Y')}</b> alle {until_date.strftime('%H:%M')}."
                else:
                    service_text += "a <b>tempo indeterminato</b>."

                service_text += "\n\n<u>Permessi Rimossi</u>"

                for el in permissions_texts:
                    if el in parsed["permissions"]:
                        service_text += f"\n\t▪️ {permissions_texts[el]}"

                if parsed["message"]:
                    service_text += f"\n\n<b>Motivo</b>: {parsed['message']}."
            else:
                service_text = (f"🔓 Utente {mention} (<code>{user.user.id}</code>) <b>non più limitato</b>.\n\n"
                                f"<u>Permessi Aggiunti</u>")
                for el in permissions_texts:
                    if el in parsed["permissions"]:
                        service_text += f"\n\t▪️ {permissions_texts[el]}"

        await add_to_table(
            table_name="limitations",
            content={
                "admin": message.from_user.id,
                "user_id": user.user.id,
                "what": parsed["permissions"],
                "limitation_time": datetime.now().astimezone(tz=italian_tz).replace(tzinfo=None),
                "expiration": (until_date.astimezone(tz=italian_tz).replace(tzinfo=None)
                               if until_date != utils.zero_datetime() else None),
                "reason": parsed["message"],
                "unlimit": False if command == "limit" else True
            }
        )

    if command == "mute" or command == "unmute":
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user.user.id,
            permissions={"can_send_messages": False if command == "mute" else True},
            until_date=until_date,
            use_independent_chat_permissions=False  # l'utente non può mandare nessun tipo di messaggio
        )

        if command == "mute":
            service_text = f"🔒 Utente {mention} (<code>{user.user.id}</code>) <b>mutato</b> "
            if parsed["duration"]:
                service_text += f"fino al <b>{until_date.strftime('%d %B %Y')}</b> alle {until_date.strftime('%H:%M')}."
            else:
                service_text += "a <b>tempo indeterminato</b>."

            if parsed["message"]:
                service_text += f"\n\n<b>Motivo</b>: {parsed['message']}."
        else:
            service_text = f"🔒 Utente {mention} (<code>{user.user.id}</code>) <b>smutato</b>."

        await add_to_table(
            table_name="limitations",
            content={
                "admin": message.from_user.id,
                "user_id": user.user.id,
                "what": [0, 1, 2, 5, 6, 7, 8, 9, 10],
                "limitation_time": datetime.now().astimezone(tz=italian_tz).replace(tzinfo=None),
                "expiration": (until_date.astimezone(tz=italian_tz).replace(tzinfo=None)
                               if until_date != utils.zero_datetime() else None),
                "reason": parsed["message"],
                "unlimit": False if command == "mute" else True
            }
        )

    if command == "ban" or command == "unban":
        if command == "ban":
            await context.bot_data["pyro_instance"].ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=user.user.id,
                until_date=until_date
            )
        else:
            await context.bot_data["pyro_instance"].unban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=user.user.id
            )

        if command == "ban":
            service_text = f"🚫 Utente {mention} (<code>{user.user.id}</code>) <b>bannato</b> "

            if parsed["duration"]:
                service_text += f"fino al <b>{until_date.strftime('%d %B %Y')}</b> alle {until_date.strftime('%H:%M')}."
            else:
                service_text += "a <b>tempo indeterminato</b>."
        else:
            service_text = f"⛓️‍💥 Utente {mention} (<code>{user.user.id}</code>) <b>sbannato</b> "

        if parsed["message"]:
            service_text += f"\n<b>Motivo</b>: {parsed['message']}."

        await add_to_table("bans", {
            "admin": update.effective_user.id,
            "user_id": user.user.id,
            "ban_time": datetime.now().astimezone(tz=italian_tz).replace(tzinfo=None),
            "reason": parsed["message"] if parsed["message"] else "",
            "until_date": (until_date.astimezone(tz=italian_tz).replace(tzinfo=None)
                           if until_date != utils.zero_datetime() else None),
            "unban": False if command == "ban" else True
        })

    if command == "kick":
        await context.bot.unban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user.user.id
        )

        service_text = f"🥊 Utente {mention} (<code>{user.user.id}</code>) <b>kickato</b> "

        if parsed["message"]:
            service_text += f"\n<b>Motivo</b>: {parsed['message']}."

        await add_to_table("kicks", {
            "admin": update.effective_user.id,
            "user_id": user.user.id,
            "kick_time": datetime.now().astimezone(tz=italian_tz).replace(tzinfo=None),
            "reason": parsed["message"] if parsed["message"] else ""
        })  

    if command == "warn":
        warn = 0 #Leggi i Warn dal DB
        maxwarn = 3
        service_text = f"🟡 Utente {mention} (<code>{user.user.id}</code>) <b>Ammonito {warn}/{maxwarn}</b> "

        if parsed["message"]:
            service_text += f"\n<b>Motivo</b>: {parsed['message']}."

        if warn >= maxwarn:
            service_text += f"\n\n🚫 Utente {mention} (<code>{user.user.id}</code>) <b>bannato</b> "
            service_text += f"\n<b>Motivo</b>: Superamento delle ammonizioni massime consentite."
         
            await context.bot_data["pyro_instance"].ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user.user.id,
            until_date=until_date
            )
            
            await add_to_table("bans", {
            "admin": update.effective_user.id,
            "user_id": user.user.id,
            "ban_time": datetime.now().astimezone(tz=italian_tz).replace(tzinfo=None),
            "reason": parsed["message"] if parsed["message"] else "",
            "until_date": None,
            "unban": False
            })

        await add_to_table("kicks", {
            "admin": update.effective_user.id,
            "user_id": user.user.id,
            "kick_time": datetime.now().astimezone(tz=italian_tz).replace(tzinfo=None),
            "reason": parsed["message"] if parsed["message"] else ""
        })  

    service_text += "\n\nℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>."

    await job_queue_functions.send_temporary_message(
        update=update,
        context=context,
        text=service_text,
        delay_delete=300
    )


async def is_admin(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    return str(user_id) in context.bot_data["admins"].keys()


async def user_in_chat(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    # tells if user_id is already in chat_id
    res = await context.bot.get_chat_member(
        user_id=user_id,
        chat_id=chat_id
    )
    if res.status is ChatMemberStatus.MEMBER or res.status is ChatMemberStatus.ADMINISTRATOR:
        return True
    return False


async def user_is_banned(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    res = await context.bot.get_chat_member(
        user_id=user_id,
        chat_id=chat_id
    )
    if res.status is ChatMemberStatus.BANNED:
        return True
    return False


async def callback_close_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Deletes the message by gathering its id from given call back data
    :param update: Update: l'Update da gestire
    :param context: ContextTypes: il contesto dell'istanza di Application
    :return:
    """
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.callback_query.data.split(" ")[1]
        )
    except telegram.error.BadRequest:
        pass
