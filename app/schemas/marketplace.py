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
    payment_date: date
    city: Optional[str] = None
    slots_total: int = 1
    notes: Optional[str] = None
    requires_acls: bool = False
    requires_bls: bool = False
    requires_atls: bool = False
    requires_pals: bool = False


@dataclass
class OpportunityUpdate:
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    specialty: Optional[str] = None
    value: Optional[float] = None
    payment_date: Optional[date] = None
    city: Optional[str] = None
    slots_total: Optional[int] = None
    notes: Optional[str] = None
    requires_acls: Optional[bool] = None
    requires_bls: Optional[bool] = None
    requires_atls: Optional[bool] = None
    requires_pals: Optional[bool] = None
