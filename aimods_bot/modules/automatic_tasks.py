# modulo per i recap e le task automatiche
import copy
import os

import telegram.error
from pyrogram import utils, enums
from pyrogram.errors import PeerIdInvalid
from telegram.constants import ChatMemberStatus
from telegram.ext import ConversationHandler

from aimods_bot.modules.database_functions import add_to_table
from constants import Permissions
from utils import *

async def new_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = update.message.text
    nome_match = re.search(r"🎉\s*(.*?)\s*\(", testo)
    nome_app = nome_match.group(1).strip() if nome_match else "Nome non trovato"
    
    piattaforma_match = re.search(r"🤖\s*(Android|iOS|Windows|macOS)", testo, re.IGNORECASE)
    piattaforma = piattaforma_match.group(1).capitalize() if piattaforma_match else "Piattaforma non trovata"
   
    link_match = re.search(r"https://play\.google\.com/store/apps/details\?id=[\w\.]+", testo)
    link_post = link_match.group(0) if link_match else "Link non trovato"

    data_for_database = {
        "app_name": nome_app,
        "app_platform": piattaforma,
        "post_link": link_post
    }
    await add_to_table(table_name="recap_messages", content=data_for_database)

