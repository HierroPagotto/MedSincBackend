from dataclasses import dataclass
from datetime import date, time

@dataclass
class ShiftCreate:
    hospital_id: int
    date: date
    start_time: time
    end_time: time
    value: float
    specialty: str
    payment_date: date