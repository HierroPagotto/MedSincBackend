from dataclasses import dataclass
from datetime import date, time
from typing import Optional


@dataclass
class OpportunityCreate:
    date: date
    start_time: time
    end_time: time
    specialty: str
    value: float
    city: Optional[str] = None
    slots_total: int = 1
    notes: Optional[str] = None


@dataclass
class OpportunityUpdate:
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    specialty: Optional[str] = None
    value: Optional[float] = None
    city: Optional[str] = None
    slots_total: Optional[int] = None
    notes: Optional[str] = None
