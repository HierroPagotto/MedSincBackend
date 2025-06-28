from dataclasses import dataclass
from datetime import date, time
from typing import Optional, List, Union

@dataclass
class ShiftCreate:
    hospital_id: int
    date: date
    start_time: time
    end_time: time
    value: float
    specialty: str
    payment_date: Optional[date]
    end_date: Optional[date] = None
    week_days: Optional[List[str]] = None

@dataclass
class ShiftUpdate:
    hospital_id: Optional[int] = None
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    value: Optional[float] = None
    specialty: Optional[str] = None
    payment_date: Optional[date] = None
    end_date: Optional[date] = None
    week_days: Optional[List[str]] = None
    status: Optional[str] = None
