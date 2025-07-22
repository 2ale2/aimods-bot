from typing import Union, Optional
from telegram import Update, Message, TextQuote, ReplyParameters
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from aimods_bot.src.helpers.job_queue import send_action_message_after
from aimods_bot.src.helpers.utils.telegram_utils import safe_delete
from aimods_bot.src.helpers.loggers import logger

log = logger.getChild("echo")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE, full_command: str):
	"""Scrive un messaggio facendo le veci del bot. Gestisce i comandi 'annuncio' e 'echo'."""
	message = update.effective_message

	if message.media_group_id:
		log.info("Il messaggio ha più di un allegato. Verrà gestito conseguentemente.")
		return
	
	await safe_delete(update, context)
	reply_parameters=_get_reply_parameters(message.reply_to_message)
	text = _get_announce_text(message)
	attachments = _get_attachments(message)
	
	# await send_action_message_after(...)
	

def _get_reply_parameters(reply_message: Optional[Message], allow_sending_without_reply=True):
	if not reply_message:
		return None
	
	reply_message_id = reply_message.id
	reply_quote = _get_reply_quote(reply_message.quote)
	
	return ReplyParameters(
		message_id=reply_message_id,
		allow_sending_without_reply=allow_sending_without_reply,
		quote=reply_quote,
		quote_parse_mode=ParseMode.HTML
	)
	
			
def _get_reply_quote(quote: Optional[TextQuote]) -> Optional[str]:
	if not quote:
		return None
	
	if quote.is_manual:
		return quote.text
		
		
def _get_announce_text(message: Union[Message, str]):
	"""Ritorna il testo senza '[.!/]annuncio'."""
	
	if isinstance(message, str):
		text = message
	else:
		text = message.caption_html_urled or message.text_html_urled
	
	if not text:
		return None
	
	s = text.split(None, 1)
	if s[0].lower().endswith("annuncio", "announce", "echo"):
		return s[1]
	return text


async def _get_attachments(message: Message):
	pass