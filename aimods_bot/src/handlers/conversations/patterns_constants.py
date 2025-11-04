
class CallbackPatterns:
    """Pattern per CallbackQueryHandler"""
    
    # Menu e navigazione
    CLOSE_MENU = r"^.*close_menu.*$"
    NOT_CLOSE_MENU = r"^(?!.*close_menu).*$"
    NOT_CLOSE_AND_NOT_FROM_NOTIFICATION = r"^(?!.*close_menu)(?!(?=.*add_request)(?=.*from_notification)).*$"
    
    # Reset e back
    RESET_CONVERSATION = "^reset_conversation$"
    BACK_CATEGORY = "^back_category$"
    BACK_NOT_CATEGORY = r"^(?:back_(?!category\b).+|no_edit)$"
    BACK_ANY = "^back_.+$"
    
    # Request handling
    CONFIRM_REQUEST = "confirm_request"
    EDIT_OR_BOOL = "^(?:edit_|bool_).+"
    EDIT_ONLY = "^edit_.+$"
    BOOL_ONLY = "^bool_.+"
    
    # Alert
    ALERT = r"^alert_.+"


class EntryPatterns:
    """Pattern per entry points dei conversation handlers"""
    
    @staticmethod
    def from_notification(platform: str, category: str) -> str:
        """Pattern per entry da notifica"""
        return f"^user/add_request/{platform}/{category}/from_notification$"
    
    @staticmethod
    def category_direct(category: str) -> str:
        """Pattern per selezione diretta categoria"""
        return f"^{category}$"
    
    @staticmethod
    def platform_base(platform: str) -> str:
        """Pattern per base platform"""
        return f"user/add_request/{platform}"


class PrefixCommands:
    """Comandi con prefisso"""
    PREFIXES = [".", "/", "!"]
    START = "start"
