import copy
from copy import deepcopy
from datetime import datetime, timedelta

import telegram.error
from telegram.constants import ChatMemberStatus
from telegram.ext import ConversationHandler

from aimods_bot.modules.job_queue_functions import send_temporary_message
from constants import Scopes
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


# COMANDO RIMOZIONE MESSAGGI
async def delete_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
	message = copy.deepcopy(update.effective_message.reply_to_message)

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

	if message is None or message.forum_topic_created is not None:
		await send_private_alert(
			update=update,
			context=context,
			text="ℹ️ INFO\n\nPer poter eliminare un messaggio, selezionalo rispondendovi.",
			delay=1
		)
		return

	if datetime.now((message_date := message.date).tzinfo) - message_date > timedelta(hours=48):
		await send_private_alert(
			update=update,
			context=context,
			text="⚠️ Warning\n\nIl messaggio non può essere rimosso, perché è stato mandato più di 48 ore fa.",
			delay=1
		)
		return

	if context.args:
		reason = ': <b>' + ' '.join(context.args) + "</b>"
	else:
		reason = " (<b>no reason given</b>)"

	answer_text = (f"♻️ Message sent by {message.from_user.name} was removed: {reason}.\n\n"
				   f"ℹ <i>This message will be deleted in 5min</i>.")

	try:
		await update.effective_message.reply_to_message.delete()
		await job_queue_functions.send_temporary_message(
			update=update,
			context=context,
			text=answer_text,
			delay_delete=600
		)
	except telegram.error.BadRequest as e:
		bot_logger.error(f"Errore nella rimozione di un messaggio: {e}")
		await send_private_alert(
			update=update,
			context=context,
			text="❌ Error\n\nIl messaggio non può essere rimosso a causa di un errore. Controlla i log dei comandi.",
			delay=1
		)
		return
	
		# ultimare la rimozione automatica del messaggio di notifica


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
async def limit_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
	scopes = Scopes()
	message = deepcopy(update.message)
	if is_admin(update.effective_user.id, context):
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
		# noinspection PyUnboundLocalVariable
		if text:
			sent_message = await context.bot.send_message(
				chat_id=context.bot_data["group_chat_id"],
				text=text,
				message_thread_id=(message.message_thread_id
									if message.message_thread_id in scopes.FORUM_SCOPE.topics else None)
			)
			context.job_queue.run_once(
				callback=job_queue_functions.scheduled_delete_message,
				data={
					"chat_id": context.bot_data["group_chat_id"],
					"message_id": sent_message.id
				},
				when=60)
			return True
		
		if update.message.text.split(" ")[0].endswith("limit"):
			if user == user.RESTRICTED:
				pass
			else:
				#else
		if update.message.text.split(" ")[0].endswith("mute"):
			if user == user.RESTRICTED:
				pass
		if update.message.text.split(" ")[0].endswith("ban"):
			# ban_chat_member(chat_id, user_id, until_date=None, revoke_messages=None)
			'''
			Possibili scenari:
			/ban Motivo [In Risposta]
			/ban Motivo Tempo [In Risposta]
			/ban UsernameoID
			/ban UsernameoID Motivo
			/ban UsernameoID Motivo Tempo
			''''
			if len(update.message.text.split(" ")) == 2: 
				await context.bot.ban_chat_member(context.bot_data["group_chat_id"], update.message.text.split(" ")[1])
				# Inserire messaggio di servizio per il Ban. Son combattuto se inserire il bottone "Sbanna" sotto. Dato che spesso viene cliccato per errore dagli Admin
				return
			elif len(update.message.text.split(" ")) == 3:
				reason = update.message.text.split(" ")[2]

			pass
		if update.message.text.split(" ")[0].endswith("kick"):
			pass
	else:
		await job_queue_functions.send_temporary_message(
			update=update,
			context=context,
			text="⚠️ Solo gli admin possono eseguire questa azione.",
			delay_before=2,  # per la chat action
			delay_delete=10
		)
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
