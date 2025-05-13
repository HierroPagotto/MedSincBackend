from dataclasses import dataclass

@dataclass
class PaymentCreate:
    shift_id: int
    amount: float