"""`ButtonItem` porta fino a Telegram l'emoji premium e il colore del bottone."""
from aimods_bot.src.ui.panel import ButtonItem, Panel, PanelConfig

EMOJI_ID = "5368324170671202286"


def _first_button(item: ButtonItem):
    panel = Panel(PanelConfig(text="x", keyboard=[[item]]))
    return panel.build_keyboard(fallback="user")[0][0]


def test_callback_button_with_premium_emoji_and_style():
    button = _first_button(ButtonItem(text="Sponsorizzate", callback_key="user/sponsor",
                                      icon_custom_emoji_id=EMOJI_ID, style="success"))
    data = button.to_dict()
    assert data["icon_custom_emoji_id"] == EMOJI_ID
    assert data["style"] == "success"
    assert data["callback_data"] == "user/sponsor"


def test_url_button_with_premium_emoji():
    button = _first_button(ButtonItem(text="Contatta l'admin", url="https://t.me/admin",
                                      icon_custom_emoji_id=EMOJI_ID))
    assert button.to_dict()["icon_custom_emoji_id"] == EMOJI_ID


def test_plain_button_sends_no_extra_fields():
    data = _first_button(ButtonItem(text="Home", callback_key="user")).to_dict()
    assert "icon_custom_emoji_id" not in data
    assert "style" not in data
