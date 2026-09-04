from __future__ import annotations

from datetime import datetime, time

from pydantic import BaseModel, Field, model_validator

from aimods_bot.src.helpers.constants.constants import Recurrence

LAST_DAY_OF_MONTH = -1


class Reminder(BaseModel):
    """Un promemoria pianificato."""
    id: int | None = None

    title: str
    body: str

    chat_id: int
    thread_id: int | None = None

    recurrence: Recurrence
    # Orario locale (Europe/Rome) a cui il promemoria deve scattare.
    fire_time: time
    # Prossima esecuzione, sempre in UTC.
    next_fire: datetime

    # Solo per Recurrence.INTERVAL (o daily)
    interval_days: int | None = Field(default=None, ge=1, le=365)
    # Solo per Recurrence.WEEKLY (0 = lunedi, 6 = domenica)
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    # Solo per Recurrence.MONTHLY. 1-31 o LAST_DAY_OF_MONTH.
    day_of_month: int | None = None

    enabled: bool = True

    created_by: int
    created_at: datetime | None = None
    last_fired_at: datetime | None = None

    @model_validator(mode="after")
    def _check_recurrence_fields(self) -> Reminder:
        """Ogni ricorrenza richiede il proprio campo e vieta gli altri."""
        required = {
            Recurrence.ONCE: None,
            Recurrence.INTERVAL: "interval_days",
            Recurrence.WEEKLY: "day_of_week",
            Recurrence.MONTHLY: "day_of_month",
        }[self.recurrence]

        optional_fields = ("interval_days", "day_of_week", "day_of_month")

        if required is not None and getattr(self, required) is None:
            raise ValueError(f"recurrence={self.recurrence} richiede {required}")

        for field_name in optional_fields:
            if field_name != required and getattr(self, field_name) is not None:
                raise ValueError(f"recurrence={self.recurrence} non ammette {field_name}")

        if self.recurrence is Recurrence.MONTHLY:
            dom = self.day_of_month
            if dom != LAST_DAY_OF_MONTH and not (1 <= dom <= 31):
                raise ValueError("day_of_month deve essere 1-31 oppure -1 (ultimo giorno)")

        return self

    @property
    def is_recurring(self) -> bool:
        return self.recurrence is not Recurrence.ONCE
