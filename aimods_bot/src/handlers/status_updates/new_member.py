from telegram.ext import ConversationHandler, ChatJoinRequestHandler, CallbackQueryHandler
from aimods_bot.src.panel.user.new_member import *


new_member_handler = ConversationHandler(
        entry_points=[
            ChatJoinRequestHandler(
                callback=new_member_join
            ),
            CallbackQueryHandler(
                callback=new_member_join,
                pattern="^recreate_captcha$"
            )
        ],
        states={
            NewMemberJoinedForum.RULES_AGREED: [
                CallbackQueryHandler(
                    callback=new_member_rules_agreed,
                    pattern="^accept_rules.+$"
                )
            ]
        },
        fallbacks=[
            CallbackQueryHandler(
                callback=new_member_join,
                pattern="^recreate_captcha$"
            )
        ],
        per_chat=False,
        name="join_handler",
        persistent=True
)