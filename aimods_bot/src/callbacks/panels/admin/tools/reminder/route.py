import os

from telegram import Update

from aimods_bot.src.callbacks.panels.admin.tools.reminder.handle import move_cursor_after_answer
from aimods_bot.src.callbacks.panels.admin.tools.reminder.render import render_admin_reminder_tool_panel, \
    render_reminder_wizard_step
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import ReminderField
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction
from aimods_bot.src.helpers.constants.path_navigation.admin import ReminderRoute
from aimods_bot.src.helpers.loggers import logger
from aimods_bot.src.helpers.models.routing import PathBuilder

log = logger.getChild(__name__)


async def admin_reminder_tool_route(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    match relative_path.segments:
        case []:
            await render_admin_reminder_tool_panel(
                update=update,
                context=context,
                base_path=root
            )
        case [ReminderRoute.ADD_REMINDER]:
            context.clear_reminder_wizard()
            wizard = context.get_or_create_reminder_wizard()
            wizard.advance_or_finish_wizard()

            await render_reminder_wizard_step(
                update=update,
                context=context,
                base_path=root.add(ReminderRoute.DRAFT),
                wizard=wizard
            )

        case [ReminderRoute.DRAFT, *rest]:
            await _route_reminder_draft(
                update=update,
                context=context,
                root=root.add(ReminderRoute.DRAFT),
                relative_path=PathBuilder(*rest)
            )

        case [ReminderRoute.MANAGE_REMINDERS, *_rest]:
            # TODO: elenco promemoria, scheda singola, toggle, elimina.
            pass
        case _:
            log.warning(f"Unhandled path in {os.path.realpath(__file__)}: {relative_path.build()}")

    return PCS.ADMIN_CONVERSATION


async def _route_reminder_draft(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
):
    wizard = context.pydc.persistent.active_reminder_wizard

    if wizard is None:
        # Bottone vecchio su una bozza non più esistente.
        await render_admin_reminder_tool_panel(update=update, context=context, base_path=root.back())
        return PCS.ADMIN_CONVERSATION

    match relative_path.segments:
        case []:
            return await render_reminder_wizard_step(
                update=update,
                context=context,
                base_path=root,
                wizard=wizard
            )

        case [field_segment, *rest] if field_segment in ReminderField:
            field = ReminderField(field_segment)
            if field not in wizard.flow:
                log.warning(f"Reminder field {field} is not in the reminder wizard flow ({wizard.flow})")
                return PCS.ADMIN_CONVERSATION

            match PathBuilder(*rest).segments:
                case []:
                    # Salto in modifica dal riepilogo: il cursore lo muove il router, non il modello.
                    wizard.requesting = field
                    wizard.editing = getattr(wizard, field.value) is not None

                    await render_reminder_wizard_step(
                        update=update,
                        context=context,
                        base_path=root,
                        wizard=wizard
                    )

                case [raw_value]:
                    # TODO: handle.py — converte `raw_value` e scrive sul wizard.
                    #       Gestisce anche ReminderRoute.DAILY (INTERVAL + interval_days=1).
                    # if not handle_reminder_field_value(wizard=wizard, field=field, raw_value=raw_value):
                    #     log.warning(f"Invalid value for {field}: {raw_value}")
                    #     return PCS.ADMIN_CONVERSATION

                    move_cursor_after_answer(wizard=wizard, field=field)

                    await render_reminder_wizard_step(
                        update=update,
                        context=context,
                        base_path=root,
                        wizard=wizard
                    )

        case [ReminderRoute.CANCEL_DRAFT]:
            context.clear_reminder_wizard()
            await render_admin_reminder_tool_panel(update=update, context=context, base_path=root.back())

        case [GlobalAction.CONFIRM]:
            # TODO: handle.py — to_reminder() → create_reminder() → schedule_unique_job()
            #       → clear_reminder_wizard(), poi pannello di conferma.
            pass

        case _:
            log.warning(f"Unhandled draft path in {os.path.realpath(__file__)}: {relative_path.build()}")

    return PCS.ADMIN_CONVERSATION
