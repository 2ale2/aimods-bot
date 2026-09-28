import os

from telegram import Update

from aimods_bot.src.callbacks.panels.admin.tools.reminder.handle import move_cursor_after_answer, \
    handle_reminder_field_value, handle_reminder_confirm, handle_reminder_toggle, handle_reminder_delete, \
    handle_reminder_edit_start
from aimods_bot.src.callbacks.panels.admin.tools.reminder.render import render_admin_reminder_tool_panel, \
    render_reminder_wizard_step, render_manage_reminders_list_panel, render_reminder_card_panel, \
    render_reminder_delete_panel
from aimods_bot.src.core.customcontext import CustomContext
from aimods_bot.src.helpers.constants.constants import ReminderField
from aimods_bot.src.helpers.constants.conversation_states import PrivateConversationState as PCS
from aimods_bot.src.helpers.constants.path_navigation import GlobalAction
from aimods_bot.src.helpers.constants.path_navigation.admin import ReminderRoute
from aimods_bot.src.infra.log import logger
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

            return await render_reminder_wizard_step(
                update=update,
                context=context,
                base_path=root.add(ReminderRoute.DRAFT),
                wizard=wizard
            )

        case [ReminderRoute.DRAFT, *rest]:
            return await _route_reminder_draft(
                update=update,
                context=context,
                root=root.add(ReminderRoute.DRAFT),
                relative_path=PathBuilder(*rest)
            )

        case [ReminderRoute.MANAGE_REMINDERS, *rest]:
            return await _route_manage_reminders(
                update=update,
                context=context,
                root=root,
                relative_path=PathBuilder(*rest)
            )

        case _:
            log.warning(f"Unhandled path in {os.path.realpath(__file__)}: {relative_path.build()}")

    return PCS.ADMIN_CONVERSATION


async def _route_manage_reminders(
        update: Update,
        context: CustomContext,
        root: PathBuilder,
        relative_path: PathBuilder
) -> int:
    """Sotto-albero `admin/tools/reminder/manage_reminders/...`."""
    manage_path = root.add(ReminderRoute.MANAGE_REMINDERS)

    match relative_path.segments:
        case []:
            await render_manage_reminders_list_panel(
                update=update,
                context=context,
                base_path=manage_path,
                page=0
            )
            return PCS.ADMIN_CONVERSATION

        case [ReminderRoute.PAGE, raw_page] if raw_page.isdigit():
            await render_manage_reminders_list_panel(
                update=update,
                context=context,
                base_path=manage_path,
                page=int(raw_page)
            )
            return PCS.ADMIN_CONVERSATION

        case [raw_id, *rest] if raw_id.isdigit():
            reminder_id = int(raw_id)

            match PathBuilder(*rest).segments:
                case []:
                    await render_reminder_card_panel(
                        update=update,
                        context=context,
                        base_path=manage_path,
                        reminder_id=reminder_id
                    )
                    return PCS.ADMIN_CONVERSATION

                case [ReminderRoute.TOGGLE]:
                    await handle_reminder_toggle(
                        update=update,
                        context=context,
                        base_path=manage_path,
                        reminder_id=reminder_id
                    )
                    return PCS.ADMIN_CONVERSATION

                case [ReminderRoute.DELETE]:
                    await render_reminder_delete_panel(
                        update=update,
                        context=context,
                        base_path=manage_path,
                        reminder_id=reminder_id
                    )
                    return PCS.ADMIN_CONVERSATION

                case [ReminderRoute.DELETE, GlobalAction.CONFIRM]:
                    return await handle_reminder_delete(
                        update=update,
                        context=context,
                        base_path=manage_path,
                        reminder_id=reminder_id
                    )

                case [ReminderRoute.EDIT]:
                    return await handle_reminder_edit_start(
                        update=update,
                        context=context,
                        draft_path=root.add(ReminderRoute.DRAFT),
                        manage_path=manage_path,
                        reminder_id=reminder_id
                    )

                case _:
                    log.warning(f"Unhandled manage path in {os.path.realpath(__file__)}: {relative_path.build()}")

        case _:
            log.warning(f"Unhandled manage path in {os.path.realpath(__file__)}: {relative_path.build()}")

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

                    return await render_reminder_wizard_step(
                        update=update,
                        context=context,
                        base_path=root,
                        wizard=wizard
                    )

                case [raw_value]:
                    if not handle_reminder_field_value(wizard=wizard, field=field, raw_value=raw_value):
                        log.warning(f"Invalid value for {field}: {raw_value}")
                        return PCS.ADMIN_CONVERSATION

                    move_cursor_after_answer(wizard=wizard, field=field)

                    return await render_reminder_wizard_step(
                        update=update,
                        context=context,
                        base_path=root,
                        wizard=wizard
                    )

                case _:
                    log.warning(f"Unhandled draft path in {os.path.realpath(__file__)}: {relative_path.build()}")

        case [ReminderRoute.BACK_TO_SUMMARY]:
            # Annulla la modifica
            wizard.requesting = None
            wizard.editing = False

            return await render_reminder_wizard_step(
                update=update,
                context=context,
                base_path=root,
                wizard=wizard
            )

        case [ReminderRoute.CANCEL_DRAFT]:
            context.clear_reminder_wizard()
            context.clear_saved_path()
            context.pydc.persistent.bot_message_id = None
            await render_admin_reminder_tool_panel(
                update=update,
                context=context,
                base_path=root.back()
            )

        case [GlobalAction.CONFIRM]:
            return await handle_reminder_confirm(
                update=update,
                context=context,
                base_path=root
            )

        case _:
            log.warning(f"Unhandled draft path in {os.path.realpath(__file__)}: {relative_path.build()}")

    return PCS.ADMIN_CONVERSATION
