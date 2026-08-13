"""Helpers de horário e conflito para marketplace."""

from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.models.shift import Shift


def _combine(d: date, t: time) -> datetime:
    return datetime.combine(d, t)


def shift_intervals(d: date, start: time, end: time) -> list[tuple[datetime, datetime]]:
    """Retorna intervalos [start, end) cobrindo overnight (ex.: 19:00–07:00)."""
    start_dt = _combine(d, start)
    end_dt = _combine(d, end)
    if end <= start:
        end_dt = end_dt + timedelta(days=1)
    return [(start_dt, end_dt)]


def intervals_overlap(
    a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime
) -> bool:
    return a_start < b_end and b_start < a_end


def doctor_has_conflicting_shift(
    db: Session,
    *,
    doctor_id: int,
    opportunity_date: date,
    start_time: time,
    end_time: time,
) -> Shift | None:
    """Conflito simples: mesmo dia (ou dia seguinte se overnight) com overlap de horário."""
    opp_intervals = shift_intervals(opportunity_date, start_time, end_time)

    day_after = opportunity_date + timedelta(days=1)
    candidates = (
        db.query(Shift)
        .filter(
            Shift.doctor_id == doctor_id,
            Shift.status.in_(["scheduled", "completed", "paid"]),
            Shift.date.in_([opportunity_date, day_after]),
        )
        .all()
    )

    for shift in candidates:
        for s_start, s_end in shift_intervals(
            shift.date, shift.start_time, shift.end_time
        ):
            for o_start, o_end in opp_intervals:
                if intervals_overlap(s_start, s_end, o_start, o_end):
                    return shift
    return None
