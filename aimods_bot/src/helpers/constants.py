from enum import IntEnum, auto
from dataclasses import dataclass
from aimods_bot.src.helpers.utils.file_utils import get_data_from_json

TOPICS = get_data_from_json("forum_topics")
pyro_instance = None


@dataclass(frozen=True)
class Permissions(IntEnum):
    can_send_messages = 0
    can_send_polls = 1
    can_send_other_messages = 2
    can_add_web_page_previews = 3
    can_invite_users = 4
    can_send_audios = 5
    can_send_documents = 6
    can_send_photos = 7
    can_send_videos = 8
    can_send_video_notes = 9
    can_send_voice_notes = 10


class ModerationSettingsStates(IntEnum):
    # - menu principale
    MAIN_MENU_CHOICE = auto()
    # -- menu.sicurezza_e_filtri
    SECURITY_FILTERS_CHOICE = auto()
    # --- menu.sicurezza_e_filtri.antispam
    ANTISPAM_MAIN_PANEL = auto()
    # ---- menu.sicurezza_e_filtri.antispam.blocco_link
    ANTISPAM_SET_LINK = auto()
    # ----- menu.sicurezza_e_filtri.antispam.blocco_link.allowafter
    ANTISPAM_SET_LINK_ALLOW_AFTER = auto()
    # ---- menu.sicurezza_e_filtri.antispam.blocco_link
    ANTISPAM_EDIT_LIST = auto()
    # ---- menu.sicurezza_e_filtri.antispam.blocco_link.white/black/greylist
    ANTISPAM_EDIT_LINK_LIST = auto()
    # ---- imposta punizione
    SET_PUNISHMENT = auto()
    # ----- durata punizione
    SET_PUNISHMENT_DURATION = auto()

    # -- menu.sicurezza_e_filtri.antiflood
    ANTIFLOOD_MAIN_PANEL = auto()
    # --- menu.sicurezza_e_filtri.antiflood.set_limits
    ANTIFLOOD_SET_LIMITS = auto()
