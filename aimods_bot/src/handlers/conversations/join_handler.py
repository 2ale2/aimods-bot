from telegram.ext import ConversationHandler, ChatJoinRequestHandler, CallbackQueryHandler

from aimods_bot.src.callbacks.status_updates.new_member import new_member_joined_forum
from aimods_bot.src.callbacks.status_updates.accept_rules import new_member_accepted_the_rules
from aimods_bot.src.helpers.constants.conversation_states.new_user import NewUserState


new_member_handler = ConversationHandler(
        entry_points=[
            ChatJoinRequestHandler(callback=new_member_joined_forum),
            CallbackQueryHandler(callback=new_member_joined_forum, pattern="^recreate_captcha$"
            )
        ],
        states={
            NewUserState.WAITING_RULES_ACCEPTANCE: [
                CallbackQueryHandler(
                    callback=new_member_accepted_the_rules,
                    pattern="^accept_rules.+$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(callback=new_member_joined_forum, pattern="^recreate_captcha$")
        ],
        per_chat=False,
        name="join_handler",
        persistent=True
    )
