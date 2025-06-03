import copy
import locale
import os
import html
from datetime import timezone

import pytz
import telegram.error
from pyrogram import utils
from pyrogram.errors import PeerIdInvalid
from telegram import InputMediaPhoto, InputMediaAudio, InputMediaVideo, InputMediaDocument
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from database_functions import add_to_table
from constants import Permissions, ModerationSettingsStates
from utils import *

RULES_ACCEPTED = 0

locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        print(f"{update.callback_query.data}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    La risposta dipende dall'utente: se è admin, allora stampo il pannello di controllo; altrimenti do il benvenuto.
    --> Basta semplicemente aggiungere un Benvenuto standard e, se Admin, aggiungere un bottone con "Settings"
    """
    if not (edit_bool := True if update.callback_query else False):
        await safe_delete(update=update, context=context)
    if await is_admin(update.effective_user.id, context):
        keyboard = [
            [
                InlineKeyboardButton(text="♟ Moderazione", callback_data="moderation"),
                InlineKeyboardButton(text="⚙ Impostazioni", callback_data="settings")
            ],
            [
                InlineKeyboardButton(text="❔ Gestione Richieste", callback_data="requests"),
                InlineKeyboardButton(text="🔐 Chiudi", callback_data="close")
            ]
        ]
        if not edit_bool:
            await context.bot.send_message(
                text="🎛 <b>Pannello di Controllo</b>\n\n"
                     "▫️ Questo è il pannello di controllo per l'amministrazione del canale e del gruppo.\n\n"
                     "🔹 Scegli un'opzione per cominciare.",
                chat_id=update.effective_user.id,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        else:
            await context.bot.edit_message_text(
                message_id=update.effective_message.message_id,
                text="🎛 <b>Pannello di Controllo</b>\n\n"
                     "▫️ Questo è il pannello di controllo per l'amministrazione del canale e del gruppo.\n\n"
                     "🔹 Scegli un'opzione per cominciare.",
                chat_id=update.effective_user.id,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )

        return ConversationHandler.END
    else:
        # stampa
        pass


# {DOPPIA VERIFICA
async def new_member_joined_forum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # check banlist
    if (uid := update.effective_user.id) in context.bot_data["ban_list"]:
        ban_data = context.bot_data["ban_list"][uid]
        if ban_data["expires_at"] is not None:
            rome_until_date = (until_date := ban_data['expires_at']).astimezone(pytz.timezone('Europe/Rome'))
        else:
            until_date = None
            rome_until_date = None
        await context.bot_data["pyro_instance"].ban_chat_member(
            chat_id=context.bot_data["group_chat_id"],
            user_id=uid,
            until_date=until_date
        )

        await add_to_table(
            table_name="bans",
            content={
                "admin": ban_data["admin"],
                "user_id": uid,
                "reason": ban_data["reason"],
                "expires_at": until_date
            }
        )

        service_text = f"🚫 Utente <b>in blacklist</b> {update.effective_user.name} (<code>{uid}</code>) <b>bannato</b> "

        if rome_until_date:
            service_text += (f"fino al <b>{rome_until_date.strftime('%d %B %Y')}</b> "
                             f"alle {rome_until_date.strftime('%H:%M')}.")
        else:
            service_text += "a <b>tempo indeterminato</b>."

        if reason := ban_data["reason"]:
            service_text += f"\n<b>Motivo</b>: <i>{reason}</i>."

        service_text += "\n\nℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>."

        await job_queue_functions.send_temporary_message(
            update=update,
            context=context,
            text=service_text,
            delay_delete=300
        )
        return ConversationHandler.END

    if await user_is_banned(
            user_id=update.effective_user.id,
            chat_id=context.bot_data["group_chat_id"],
            context=context
    ):
        await job_queue_functions.send_temporary_message(
            update=update,
            context=context,
            text="❌ Il tuo ID è stato <b>bannato</b>.\n\nNon puoi unirti al gruppo.",
            delay_delete=10
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

    if str(update.effective_user.id) != update.callback_query.data.split(" ")[1]:
        return None

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
    message_text = update.message.text_html_urled or update.message.caption_html_urled
    parts = message_text.split(None, 1)
    command = parts[0][1:].lower()

    match command:
        case "start":
            await start_command(update=update, context=context)
        case "rules":
            await send_rules(update=update, context=context)
        case "del" | "delmute" | "delban" | "delkick":
            await limit_user(update=update, context=context, command=command, full_command=message_text)
        case "ban" | "unban" | "mute" | "unmute" | "kick" | "warn" | "unwarn":
            await limit_user(update=update, context=context, command=command, full_command=message_text)
        case "limit" | "unlimit":
            await limit_user(update=update, context=context, command=command, full_command=message_text)
        case "annuncio":
            await announce(update=update, context=context)


# COMANDO RIMOZIONE MESSAGGI
async def delete_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE, args: str | None, log_message=True):
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
            "user_id": message_to_delete.from_user.id,
            "reason": re.sub(r'</?b>|\(|\)|:', '', reason).strip(),
            "content": (message_to_delete.text
                        if message_to_delete.effective_attachment is None
                        else message_to_delete.caption),
            "username": message_to_delete.from_user.name,
            "media": forwarded_media.link if forwarded_media is not None else None
        }
        await add_to_table(table_name="deleted_messages", content=data_for_database)


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

    parsed = await parse_command(update=update, context=context, command=command.replace("del", ""),
                                 full_command=full_command)

    if not parsed:
        return

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

    now_utc = datetime.now(timezone.utc)
    until_date = (now_utc + parsed["duration"]) if parsed["duration"] else utils.zero_datetime()
    rome_until_date = until_date.astimezone(pytz.timezone('Europe/Rome'))

    # resolving del peer
    try:
        user = await context.bot_data["pyro_instance"].get_users(
            user_ids=parsed["user"] or replied.from_user.id
        )
    except PeerIdInvalid:
        if not command.endswith("ban"):
            await send_private_alert(
                update=update,
                context=context,
                text="⚠️ Warning\n\n▪️ L'utente sembra non esistere, oppure non è mai stato visto dal bot."
            )
            return
        parsed_user = parsed["user"] or replied.from_user.id
        if command == "ban":
            # il resolving di uno username non genera mai PeerIdInvalid, quindi, se siamo qua, parsed[user] è un ID
            context.bot_data["ban_list"][parsed_user] = {
                # senza fuso orario per evitare di convertire 10 volte
                "expires_at": until_date.astimezone(pytz.UTC) if until_date != utils.zero_datetime() else None,
                "reason": parsed["message"] or None,
                "admin": message.from_user.id
            }
            await job_queue_functions.send_temporary_message(
                update=update,
                context=context,
                text=f"🖊 Utente <code>{parsed_user}</code> <b>aggiunto in blacklist</b>. "
                     f"Verrà bannato al primo ingresso.\n\nℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>.",
                delay_delete=300
            )
            return
        if command == "unban":
            if parsed_user in context.bot_data["ban_list"]:
                del context.bot_data["ban_list"][parsed_user]
                await job_queue_functions.send_temporary_message(
                    update=update,
                    context=context,
                    text=f"🖊 Utente <code>{parsed_user}</code> <b>rimosso dalla blacklist</b>.\n\n"
                         f"ℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>.",
                    delay_delete=300
                )
                return
            await send_private_alert(
                update=update,
                context=context,
                text="⚠️ Warning\n\n"
                     "▪️ L'utente non è mai stato nel gruppo oppure il bot non lo ha mai visto.\n\nSbannalo "
                     "manualmente dalle impostazioni (se l'utente non ha username, salvalo prima nei contatti)."
            )
            # Lo sban manuale non consente il log automatico nel database. Possiamo però gestire l'evento di ban
            # manuale da parte di un admin per aggiornare il database.
            return
        
    except Exception as e:
        bot_logger.error(f"Errore nel resolving del peer: {e}")
        await send_private_alert(
            update=update,
            context=context,
            text="❌ Error\n\n▪️ Errore nel resolving del peer: leggi i log."
        )
        return

    # resolving del membro della chat
    try:
        # UnboundLocalError: cannot access local variable 'user' where it is not associated with a value
        # Da errore di variabile vuota se si usa unban su un utente che non è mai stato visto dal bot
        # FIX - Adesso il comando 'unban', in caso di errore nel parsing, è gestito nel ramo; tutte le altre eccezioni
        # sono gestite con clausola 'except Exception' (vedi sopra).

        # noinspection PyUnboundLocalVariable
        member = await context.bot_data["pyro_instance"].get_chat_member(
            chat_id=context.bot_data["group_chat_id"],
            user_id=user.id
        )
    except telegram.error.BadRequest as e:
        if not command.endswith("ban"):
            bot_logger.warning(f"Utente non trovato (Bad Request): {e}")
            await send_private_alert(
                update=update,
                context=context,
                text="⚠️ Warning\n\n▪️ L'utente non è mai stato nel gruppo oppure il bot non lo ha mai visto."
            )
            return
        member = None

    text = None
    admins = await update.effective_message.chat.get_administrators()
    for el in admins:
        if el.user.id == user.id:
            text = "⚠️ Warning\n\n▪️ Non è consentito compiere questa azione su altri admin."
            break
    if member is not None:
        if member.status == 'left' and command != "ban":
            if command == "unban":
                text = "⚠️ Warning\n\n▪️ L'utente è già sbannato."
            else:
                text = "⚠️ Warning\n\n▪️ L'utente non è nel gruppo."
        if member.status == 'kicked' and command != "unban":
            if command == "ban":
                text = "⚠️ Warning\n\n▪️ L'utente è già bannato."
            else:
                text = "⚠️ Warning\n\n▪️ L'utente è bannato: sbannalo prima di compiere questa azione."

    if text is not None:
        await send_private_alert(
            update=update,
            context=context,
            text=text
        )
        return

    if member is not None:
        # noinspection PyUnboundLocalVariable
        mention = (
            f'<a href="tg://user?id={member.user.id}">{member.user.first_name}</a>'
            if member.user.username is None
            else f"@{member.user.username}"
        )
    else:
        if parsed["user"]:
            mention = f"<code>{parsed["user"]}</code>" if parsed["user"].isnumeric() else f"{parsed['user']}"
        else:
            # se parsed["user"] non contiene un utente, allora, per i controlli precedenti, l'admin ha risposto a un
            # messaggio.
            mention = (
                f'<a href="tg://user?id={replied.from_user.id}">{replied.from_user.first_name}</a>'
                if replied.from_user.username is None
                else f"@{replied.from_user.username}"
            )

    if "del" in command:
        await delete_group_message(
            update=update,
            context=context,
            args=parsed["message"],
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
                service_text = (f"🔓 Utente {mention} (<code>{member.user.id}</code>) non più limitato "
                                f"(<b>tutti i permessi aggiunti</b>).")
            else:
                service_text = (f"🔒 Utente {mention} (<code>{member.user.id}</code>) limitato "
                                f"(<b>tutti i permessi rimossi</b>).")
        else:
            actual = member.permissions.__dict__ if member.permissions is not None else {perm.name: True for perm in p}
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
            user_id=member.user.id,
            permissions=new_permissions,
            until_date=until_date,
            use_independent_chat_permissions=True
        )

        if parsed["permissions"] != [11]:
            if command == "limit":
                service_text = f"🔒 Utente {mention} (<code>{member.user.id}</code>) <b>limitato</b> "
                if parsed["duration"]:
                    service_text += (f"fino al <b>{rome_until_date.strftime('%d %B %Y')}</b> alle "
                                     f"{rome_until_date.strftime('%H:%M')}.")
                else:
                    service_text += "a <b>tempo indeterminato</b>."

                service_text += "\n\n<u>Permessi Rimossi</u>"

                for el in permissions_texts:
                    if el in parsed["permissions"]:
                        service_text += f"\n\t▪️ {permissions_texts[el]}"
            else:
                service_text = (f"🔓 Utente {mention} (<code>{member.user.id}</code>) <b>non più limitato</b>.\n\n"
                                f"<u>Permessi Aggiunti</u>")
                for el in permissions_texts:
                    if el in parsed["permissions"]:
                        service_text += f"\n\t▪️ {permissions_texts[el]}"

            if parsed["message"]:
                service_text += f"\n\n<b>Motivo</b>: {parsed['message']}."

        await add_to_table(
            table_name="limitations",
            content={
                "admin": message.from_user.id,
                "user_id": member.user.id,
                "what": parsed["permissions"],
                "expires_at": until_date.astimezone(pytz.UTC) if until_date != utils.zero_datetime() else None,
                "reason": parsed["message"],
                "unlimit": False if command == "limit" else True
            }
        )

    elif command == "mute" or command == "unmute":
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=member.user.id,
            permissions={"can_send_messages": False if command == "mute" else True},
            until_date=until_date,
            use_independent_chat_permissions=False  # l'utente non può mandare nessun tipo di messaggio
        )

        if command == "mute":
            service_text = f"🔒 Utente {mention} (<code>{member.user.id}</code>) <b>mutato</b> "
            if parsed["duration"]:
                service_text += (f"fino al <b>{rome_until_date.strftime('%d %B %Y')}</b> "
                                 f"alle {rome_until_date.strftime('%H:%M')}.")
            else:
                service_text += "a <b>tempo indeterminato</b>."

            if parsed["message"]:
                service_text += f"\n\n<b>Motivo</b>: {parsed['message']}."
        else:
            service_text = f"🔒 Utente {mention} (<code>{member.user.id}</code>) <b>smutato</b>."

        await add_to_table(
            table_name="limitations",
            content={
                "admin": message.from_user.id,
                "user_id": member.user.id,
                "what": [0, 1, 2, 5, 6, 7, 8, 9, 10],
                "expires_at": until_date.astimezone(pytz.UTC) if until_date != utils.zero_datetime() else None,
                "reason": parsed["message"],
                "unlimit": False if command == "mute" else True
            }
        )

    elif command == "ban" or command == "unban":
        if command == "ban":
            try:
                await context.bot_data["pyro_instance"].ban_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=user.id,
                    until_date=until_date
                )
            except Exception as e:
                bot_logger.error(f"Errore durante il ban dell'utente {user.user_id}: {e}")
                await send_private_alert(
                    update=update,
                    context=context,
                    text="❌ Error\n\n▪️ C'è stato un errore in fase di ban dell'utente. Leggi i log."
                )
        else:
            res = await revoke_last_action("bans", user.id)
            if res is False:
                await send_private_alert(
                    update=update,
                    context=context,
                    text="⚠️ Warning\n\n▪️ Non risulta alcun record sul ban dell'utente."
                )
                return
            if res is not True:
                await send_private_alert(
                    update=update,
                    context=context,
                    text="❌ Error\n\n▪️ Errore in fase di registrazione dell'unban. Leggi i log."
                )

            try:
                # Aggiunto rimozione dalla blacklist in caso di unban di un utente blacklistato
                if user.id in context.bot_data.get("ban_list", {}): 
                    context.bot_data.get("ban_list", {}).pop(user.id, None)
                await context.bot_data["pyro_instance"].unban_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=user.id
                )
            except Exception as e:
                bot_logger.error(f"Errore durante l'unban dell'utente {user.id}: {e}")
                await send_private_alert(
                    update=update,
                    context=context,
                    text="❌ Error\n\n▪️ C'è stato un errore in fase di unban dell'utente. Leggi i log."
                )
                return

        if command == "ban":
            if not mention.isnumeric():
                service_text = f"🚫 Utente {mention} (<code>{user.id}</code>) <b>bannato</b> "
            else:
                service_text = f"🚫 Utente <code>{mention}</code> <b>bannato</b> "

            if parsed["duration"]:
                service_text += (f"fino al <b>{rome_until_date.strftime('%d %B %Y')}</b> "
                                 f"alle {rome_until_date.strftime('%H:%M')}.")
            else:
                service_text += "a <b>tempo indeterminato</b>."
        else:
            if not mention.isnumeric():
                service_text = f"⛓️‍💥 Utente {mention} (<code>{user.id}</code>) <b>sbannato</b>."
            else:
                service_text = f"⛓️‍💥 Utente <code>{mention}</code> <b>sbannato</b> "

        if parsed["message"]:
            service_text += f"\n<b>Motivo</b>: {parsed['message']}."

        if command == "ban":
            await add_to_table("bans", {
                "admin": update.effective_user.id,
                "user_id": user.id,
                "reason": parsed["message"] if parsed["message"] else "",
                "expires_at": until_date.astimezone(pytz.UTC) if until_date != utils.zero_datetime() else None,
                "unban": False if command == "ban" else True
            })

    elif command == "kick":
        await context.bot.unban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=member.user.id
        )

        service_text = f"🥊 Utente {mention} (<code>{member.user.id}</code>) <b>kickato</b>."

        if parsed["message"]:
            service_text += f"\n<b>Motivo</b>: {parsed['message']}."

        await add_to_table("kicks", {
            "admin": update.effective_user.id,
            "user_id": member.user.id,
            "reason": parsed["message"] if parsed["message"] else ""
        })

    elif command == "warn":
        await add_to_table("warnings", {
            "admin": update.effective_user.id,
            "user_id": member.user.id,
            "expires_at": until_date.astimezone(pytz.UTC) if until_date != utils.zero_datetime() else None,
            "reason": parsed["message"] if parsed["message"] else ""
        })

        warns_count = await get_user_warnings(user_id=member.user.id)
        if not isinstance(warns_count, int):
            await send_private_alert(
                update=update,
                context=context,
                text="⚠️ Warning\n\nNon è stato possibile ottenere il numero di ammonizioni dell'utente. Leggi i log."
            )
            return

        max_warns = 3

        if warns_count >= max_warns:
            try:
                await context.bot_data["pyro_instance"].ban_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=member.user.id,
                    until_date=until_date
                )
            except Exception as e:
                bot_logger.error(f"Errore durante il ban dell'utente {member.user.id}: {e}")
                await send_private_alert(
                    update=update,
                    context=context,
                    text="❌ Error\n\n▪️ C'è stato un errore in fase di ban dell'utente. Leggi i log."
                )
                return

            service_text = (f"\n\n🚫 Utente {mention} (<code>{member.user.id}</code>) <b>ammonito</b> "
                            f"(<code>{warns_count}/{max_warns}</code> → <b>Bannato</b>).")

            if parsed["duration"]:
                service_text += (f"\n\n<i>Fino al {rome_until_date.strftime('%d %B %Y')} "
                                 f"alle {rome_until_date.strftime('%H:%M')}</i>.")

            if parsed["message"]:
                service_text += f"\n\n<b>Motivo</b>: {parsed['message']}."

            await add_to_table("bans", {
                "admin": update.effective_user.id,
                "user_id": member.user.id,
                "reason": parsed["message"] if parsed["message"] else "",
                "expires_at": until_date.astimezone(pytz.UTC) if until_date != utils.zero_datetime() else None
            })

        else:
            service_text = (f"\n\n⚠️ Utente {mention} (<code>{member.user.id}</code>) <b>ammonito</b> "
                            f"(<code>{warns_count}/{max_warns}</code>).")

            if parsed["duration"]:
                service_text += (f"\n\n<i>Fino al {rome_until_date.strftime('%d %B %Y')} "
                                 f"alle {rome_until_date.strftime('%H:%M')}</i>.")

            if parsed["message"]:
                service_text += f"\n\n<b>Motivo</b>: {parsed['message']}."

    elif command == "unwarn":
        res = await revoke_last_action(table="warnings", user_id=member.user.id)
        if res is False:
            await send_private_alert(
                update=update,
                context=context,
                text="⚠️ Warning\n\nL'utente non ha ammonizioni attive."
            )
            return

        warns_count = await get_user_warnings(user_id=member.user.id)
        max_warns = 3
        service_text = (f"✅ <b>Ammonizione rimossa</b> per {mention} (<code>{member.user.id}</code>)\n\n"
                        f"🔹 <b>Ammonizioni Attuali</b>: "
                        f"<code>{warns_count if warns_count is not None else 0}/{max_warns}</code>")

        if parsed["message"]:
            service_text += f"\n\n<b>Motivo</b>: {parsed['message']}."

    service_text += "\n\nℹ️ <i>Questo messaggio verrà rimosso in 5 minuti</i>."

    await job_queue_functions.send_temporary_message(
        update=update,
        context=context,
        text=service_text,
        delay_delete=300
    )


async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_delete(update=update, context=context)

    if update.effective_chat.id != int(context.bot_data["group_chat_id"]):
        return

    mes = update.effective_message
    reply_parameters = telegram.ReplyParameters(
        message_id=mes.reply_to_message.id if mes.reply_to_message else None
    )

    text_content = mes.caption_html_urled or mes.text_html_urled

    parts = text_content.split(None, 1)
    cleaned_content = parts[1]

    if att := mes.effective_attachment:
        match type(att):
            case _ if isinstance(att, tuple):
                att = InputMediaPhoto(media=att[-1])
            case telegram.Audio:
                att = InputMediaAudio(media=att)

            case telegram.Video:
                att = InputMediaVideo(media=att)
            case _:
                att = InputMediaDocument(media=att)

        await send_action_message_after(
            update=update,
            context=context,
            text=cleaned_content,
            additional_job_data={
                "attachments": [att],
                "reply_parameters": reply_parameters,
                "message_thread_id": mes.message_thread_id
            }
        )
    else:
        await send_action_message_after(
            update=update,
            context=context,
            text=cleaned_content,
            additional_job_data={
                "reply_parameters": reply_parameters,
                "message_thread_id": mes.message_thread_id
            }
        )


async def catch_post_from_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message.text and not update.effective_message.caption:
        return

    text = update.effective_message.text
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
        bot_logger.warning(f"Software platform(s) not captured in post #{update.effective_message.id} from channel.")
        return

    lines = text.splitlines()
    if "#richiesta" in lines[0]:
        lines.pop(0)

    first_line = re.sub(r"^\W+", "", lines[0])

    match = re.match(r"(.+?)\s+([vw]\d[\d.]*|build\s+\d+)", first_line, re.IGNORECASE)

    if not match:
        bot_logger.warning(f"Software name not captured in post #{update.effective_message.id} from channel.")
        return

    software_name = None
    for el in hashtags["software_associations"]:
        if hashtags["software_associations"][el] in text:
            software_name = el
            break

    if software_name is None:
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


async def moderation_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(user_id=update.callback_query.from_user.id, context=context):
        return ConversationHandler.END

    # scelta dal menu principale
    if update.callback_query.data == "moderation":
        text = ("♟ <b>Impostazioni – Moderazione Gruppo e Canale</b>\n\n"
                "▫️ Da questo menù puoi regolare le impostazioni di moderazione del gruppo e del canale di "
                "<i>AIMods</i>.\n\n🔹 Scegli un'opzione.")

        keyboard = [
            [InlineKeyboardButton(text="🔐 Sicurezza e Filtri", callback_data="security_filters_settings")],
            [InlineKeyboardButton(text="⚠️ Moderazione Utenti", callback_data="user_moderation_settings")],
            [InlineKeyboardButton(text="🎞 Messaggi e Contenuti", callback_data="media_contents_settings")],
            [InlineKeyboardButton(text="👥 Gestione Community", callback_data="community_settings")],
            [InlineKeyboardButton(text="🏠 Home", callback_data="main_menu")]
        ]

        await update.effective_message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

        return ModerationSettingsStates.MAIN_MENU_CHOICE

    # scelta secondaria
    match update.callback_query.data:
        case "security_filters_settings":
            text = "<b>🔐 Sicurezza e Filtri</b>\n\n🔹 Scegli un'opzione."
            keyboard = [
                [InlineKeyboardButton(text="📨 Anti-Spam", callback_data="antispam_settings")],
                [InlineKeyboardButton(text="🌊 Anti-Flood", callback_data="anti_flood_settings")],
                [InlineKeyboardButton(text="🖊 Parole Bandite", callback_data="forbidden_words_settings")],
                [InlineKeyboardButton(text="👁‍🗨 Controlli", callback_data="check_settings")],
                [InlineKeyboardButton(text="🔞 Contenuti Inappropriati", callback_data="inappropriate_content_settings")],
                [InlineKeyboardButton(text="📏 Lunghezza Messaggi", callback_data="length_settings")],
                [InlineKeyboardButton(text="🔙 Indietro", callback_data="moderation")]
            ]
            await update.effective_message.edit_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            return ModerationSettingsStates.SECURITY_FILTERS_CHOICE
        case "user_moderation_settings":
            pass
        case "media_contents_settings":
            pass
        case "community_settings":
            pass

    return None


async def antispam_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(user_id=update.effective_user.id, context=context):
        return ConversationHandler.END

    if update.callback_query:
        callback_data = update.callback_query.data
    else:
        callback_data = "antispam_set_punishment"

    punishment_emojis = {
        "ban": "🚫",
        "kick": "🥊",
        "mute": "🔒",
        "warn": "⚠️"
    }

    antispam_configuration = context.bot_data['configuration']['moderation']['antispam']
    toggle = antispam_configuration['toggle']
    punishment = antispam_configuration['punishment']['type']
    time_total_seconds = antispam_configuration['punishment']['time']
    time_text = await get_time_text(time_total_seconds) if time_total_seconds > 30 else "♾️ A Tempo Indeterminato"

    if callback_data in ["antispam_settings", "antispam_toggle_on", "antispam_toggle_off"]:
        if callback_data == "antispam_toggle_on":
            toggle = context.bot_data['configuration']['moderation']['antispam']['toggle'] = True
        elif callback_data == "antispam_toggle_off":
            toggle = context.bot_data['configuration']['moderation']['antispam']['toggle'] = False

        text = ("📨 <b>Impostazioni Anti-Spam</b>"
                "\n\n▫️ Qui puoi configurare le <b>difese automatiche</b> contro <b>spammer e bot malevoli</b>. "
                "Attiva solo ciò che serve per evitare falsi positivi.\n\n"
                f"🔸 <u>Stato</u> – {'☂️' if toggle else '🌂'} <i>{toggle}</i>\n"
                f"🔸 <u>Punizione</u> – {punishment_emojis[punishment]} <i>{punishment.capitalize()}</i>\n"
                f"🔸 <u>Tempo</u> – <i>{time_text}</i>\n\n")

        if time_total_seconds <= 30:
            text += ("⚠️ <b>Per regole imposte da Telegram, "
                     "un tempo inferiore a 30 secondi equivale a tempo indeterminato</b>.\n\n")

        text += "🔹 Scegli un'opzione."

        keyboard = [
            [
                InlineKeyboardButton(text="On ☂️", callback_data="antispam_toggle_on"),
                InlineKeyboardButton(text="Off 🌂", callback_data="antispam_toggle_off")
            ],
            [InlineKeyboardButton(text="⚖️ Punizione", callback_data="antispam_set_punishment")],
            [InlineKeyboardButton(text="⛓️‍💥 Blocco Link e Menzioni", callback_data="antispam_set_links")],
            [InlineKeyboardButton(text="👥 Blocco Inoltro", callback_data="antispam_set_forward")],
            [InlineKeyboardButton(text="🎞 Blocco Media", callback_data="antispam_set_media")],
            [InlineKeyboardButton(text="🔙 Indietro", callback_data="security_filters_settings")]
        ]

        # controllo necessario per evitare bad requests
        if html.unescape(update.effective_message.text_html_urled) != text:
            await update.effective_message.edit_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )

        return ModerationSettingsStates.ANTISPAM_MAIN_PANEL

    # menu.sicurezza_e_filtri.antispam.set_punishment
    if callback_data.startswith("antispam_set_punishment"):
        if any(x in callback_data.split('_')[-1] for x in ["ban", "warn", "mute", "kick"]):
            punishment = context.bot_data['configuration']['moderation']['antispam']['punishment']['type'] = callback_data.split('_')[-1]
        text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
                "↦ ⚖️ <i>Impostazioni Punizione</i>\n\n"
                "▫️ Puoi scegliere da qui la punizione da comminare a chi spamma e impostarne la durata.\n\n"
                f"🔸 <u>Punizione</u> – {punishment_emojis[punishment]} <i>{punishment.capitalize()}</i>\n"
                f"🔸 <u>Tempo</u> – <i>{time_text}</i>\n\n")

        if time_total_seconds <= 30:
            text += ("⚠️ <b>Per regole imposte da Telegram, "
                     "un tempo inferiore a 30 secondi equivale a tempo indeterminato</b>.\n\n")

        text += "ℹ️ Il tempo non viene considerato se la punzione scelta è <i>Kick</i>."

        keyboard = [
            [InlineKeyboardButton(text="⏳ Imposta Durata Punizione",
                                  callback_data="antispam_set_punishment_duration")],
            [
                InlineKeyboardButton(text="🚫 Ban", callback_data="antispam_set_punishment_ban"),
                InlineKeyboardButton(text="🥊 Kick", callback_data="antispam_set_punishment_kick")
            ],
            [
                InlineKeyboardButton(text="🔒 Mute", callback_data="antispam_set_punishment_mute"),
                InlineKeyboardButton(text="⚠️ Warn", callback_data="antispam_set_punishment_warn")
            ],
            [InlineKeyboardButton(text="🔙 Indietro", callback_data="antispam_settings")]
        ]

        if "settings_main_message" not in context.user_data:
            # controllo necessario per evitare bad requests
            if html.unescape(update.effective_message.text_html_urled) != text:
                await update.effective_message.edit_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.HTML
                )
        else:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['settings_main_message'],
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            del context.user_data['settings_main_message']
        return ModerationSettingsStates.ANTISPAM_SET_PUNISHMENT

    match callback_data:
        case "antispam_set_links":
            # manu impostazioni link (attiva, disattiva, blacklist e whitelist, ...)
            keyboard = [
                [

                ]
            ]
            return None
        case "antispam_set_forward":
            # menu impostazioni inoltro (attiva, disattiva, da dove)
            return None
        case "antispam_set_media":
            # manu impostazioni media (attiva, disattiva, ...)
            return None
        case "security_filters_settings":
            await moderation_settings(update=update, context=context)
            return ConversationHandler.END

    return None


async def antispam_set_punishment_duration(update: Update, context: CallbackContext):
    if not await is_admin(update.effective_user.id, context):
        return ConversationHandler.END

    update_data = update.callback_query.data if update.callback_query else update.effective_message.text
    if update_data == "antispam_set_punishment_duration" and update.callback_query:
        context.user_data["settings_main_message"] = update.effective_message.id
        text = ("📨 <b>Impostazioni Anti-Spam</b>\n\n"
                "↦ 🕔 <i>Tempo Punizione</i>\n\n"
                "▫️ Puoi impostare da qui la durata della punizione comminata a chi spamma.\n\n"
                "❓ Indica una durata del tipo <code>52 giorni 4 ore 100 minuti 20 secondi</code>\n\n"
                "ℹ️ Il tempo non viene considerato se la punzione scelta è <i>Kick</i>.")
        keyboard = [
            [InlineKeyboardButton(
                text="♾️ Tempo Indeterminato",
                callback_data="antispam_set_punishment_duration_endless")
            ],
            [InlineKeyboardButton(
                text="🔙 Indietro",
                callback_data="antispam_set_punishment")
            ]
        ]
        await update.effective_message.edit_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return ModerationSettingsStates.ANTISPAM_SET_PUNISHMENT_DURATION

    elif update_data == "antispam_set_punishment" and update.callback_query:
        await antispam_settings(update=update, context=context)
        return ConversationHandler.END

    elif update_data == "antispam_set_punishment_duration_endless" and update.callback_query:
        context.bot_data['configuration']['moderation']['antispam']['punishment']['time'] = 1
        await antispam_settings(update=update, context=context)
        return ConversationHandler.END

    else:
        await safe_delete(update=update, context=context)
        parsed_duration = await parse_duration(str(update_data))
        if parsed_duration is None:
            await send_action_message_after(
                update=update,
                context=context,
                text="⚠️ La sintassi non è corretta: non usare segni di punteggiatura o parole non necessarie.\n\n"
                     "<b>Esempi</b>\n\t"
                     "<code>3 giorni 4 ore 32 minuti 10 secondi</code>\n\t"
                     "<code>1 giorno 2 minuti 32 ore</code>\n\t"
                     "<code>4 ore 1 giorno 2 ore 1 minuto</code>",
                recipient_id=update.effective_user.id,
                additional_job_data={
                    "reply_markup": InlineKeyboardMarkup(
                        [[InlineKeyboardButton(text="🚮 Chiudi", callback_data="close")]]
                    )
                }
            )
            return ModerationSettingsStates.ANTISPAM_SET_PUNISHMENT_DURATION
        else:
            context.bot_data['configuration']['moderation']['antispam']['punishment']['time'] = parsed_duration.total_seconds()
            await antispam_settings(update=update, context=context)
            return ConversationHandler.END
