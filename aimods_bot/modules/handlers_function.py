import copy
import os
from datetime import datetime, timedelta

import telegram.error
from telegram.constants import ChatMemberStatus
from telegram.ext import ConversationHandler

from aimods_bot.modules.database_functions import add_to_table
from aimods_bot.modules.job_queue_functions import send_temporary_message
from utils import *

RULES_ACCEPTED = 0

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
	"""
	La risposta dipende dall'utente: se è admin, allora stampo il pannello di controllo; altrimenti do il benvenuto.
	--> Basta semplicemente aggiungere un Benvenuto standard e, se Admin, aggiungere un bottone con "Settings"
	"""
	if is_admin(update.effective_user.id, context):
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
	"""
	L'utente ha accettato le regole. La richiesta viene approvata e l'utente è indirizzato al gruppo.

	:param update: Update: l'Update da gestire
	:param context: ContextTypes: il contesto dell'istanza di Application
	:return: ConversationHandler.END
	"""
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
	message_text = update.message.text
	match = re.match(r"^[/!.]([a-zA-Z0-9_]+)(?:\s(.*))?$", message_text)

	if match:
		command = match.group(1)
		args = match.group(2) if len(match.groups()) == 2 else None

		match command:
			case "start":
				await start_command(update=update, context=context)
			case "rules":
				await send_rules(update=update, context=context)
			case "del":
				await delete_group_message(update=update, context=context, args=args)
			case "ban":
				await limit_user(update=update, context=context, command=command, args=args)


# COMANDO RIMOZIONE MESSAGGI
async def delete_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE, args: str | None):
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
async def limit_user(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str, args: str | None):
	message = copy.deepcopy(update.message)
	if not is_admin(update.effective_user.id, context):
		await job_queue_functions.send_temporary_message(
			update=update,
			context=context,
			text="⚠️ Solo gli admin possono eseguire questa azione.",
			delay_before=2,  # per la chat action
			delay_delete=10
		)
		return

	user = await context.bot.get_chat_member(
		chat_id=context.bot_data["group_chat_id"],
		user_id=update.effective_user.id
	)
	text = None
	if user.status == user.LEFT:
		text = "⚠️ L'utente non è nel gruppo."
	elif user.status == user.ADMINISTRATOR or user.status == user.OWNER:
		text = "⚠️ Non è consentito limitare gli altri admin."
	elif user.status == user.BANNED:
		text = "⚠️ L'utente è bannato."

	if text is not None:
		await send_private_alert(
			update=update,
			context=context,
			text=text
		)
		return True

	if command == "limit":
		if user == user.RESTRICTED:
			pass
	elif command == "mute":
		if user == user.RESTRICTED:
			pass
	if command == "ban":  # ban_chat_member(chat_id, user_id, until_date=None, revoke_messages=None)
		if update.message.reply_to_message:
			await context.bot.ban_chat_member(
				chat_id=update.message.chat.id,
				user_id=update.message.reply_to_message.from_user.id
			)
			
			part = update.message.text.split(" ", 1) # Split per verificare quale dei 3 scenari possibili avviene in risposta

			if len(part) == 1: #Scenario /ban in risposta
				await send_temporary_message(
					update=update,
					context=context,
					text="Ho bannato l'utente",
					delay_before=2,
					delay_delete=60
				)
				return True

			else: #Scenario multiplo
				#Tabella conversione per le durate delle punizioni --> Da definire come Globale/Costante
				conversione = {
					"minuti": 1,
					"minuto": 1,
					"ore": 60,
					"ora": 60,
					"giorni": 1440,
					"giorno": 1440,
					"settimane": 10080,
					"settimana": 10080,
					"mesi": 43800,
					"mese": 43800,
					"anni": 525600,
					"anno": 525600
				}

				# Tentiamo di capire se il primo elemento è una durata
				durata_parte = part.split(" ", 1)[0]
				motivo = part.split(" ", 1)[1] if len(part.split(" ", 1)) > 1 else ""

				# Se la durata è solo un numero → sono minuti
				if durata_parte.isdigit():
					durata_minuti = int(durata_parte)
				else:
					# Proviamo a estrarre numero + unità di tempo
					durata_split = durata_parte.split(" ", 1)
					if len(durata_split) == 2 and durata_split[1] in conversione:
						numero, unita = durata_split
						if numero.isdigit():
							durata_minuti = int(numero) * conversione[unita]
						else:
							durata_minuti = None  # Non valido
					else:
						# Se non è riconosciuto come durata, trattiamolo come parte del motivo
						await send_temporary_message(
							update=update,
							context=context,
							text=f"Ho bannato l'utente\nMotivo: {part[1]}",
							delay_before=2,
							delay_delete=60
						)
						return True
				await send_temporary_message(
					update=update,
					context=context,
					text=f"Ho bannato l'utente per {durata_minuti} minuti\nMotivo: {part[1]}",
					delay_before=2,
					delay_delete=60
				)
				return True

		elif len(update.message.text.split(" ")) == 3:
			reason = update.message.text.split(" ")[2]

		pass
	if update.message.text.split(" ")[0].endswith("kick"):
		pass


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
