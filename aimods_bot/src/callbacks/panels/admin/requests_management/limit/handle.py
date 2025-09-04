from telegram.ext import ContextTypes


def new_user_requests_limiting_item(context: ContextTypes.DEFAULT_TYPE):
    context.chat_data.setdefault("limit_user_requests", {
        "user_id": 0,
        "duration": 0,
        "topics": []
    })
