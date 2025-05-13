from dataclasses import dataclass

@dataclass
class HospitalCreate:
    name: str
    address: str
    latitude: float
    longitude: float