from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DoctorCreate:
    name: str
    email: str
    password: str
    main_specialty: str
    profession: str = "doctor"
    photo_url: Optional[str] = None
    council_type: Optional[str] = None
    council_number: Optional[str] = None
    council_state: Optional[str] = None
    crm: Optional[str] = None
    crm_state: Optional[str] = None
    graduation_year: Optional[int] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    procedures: Optional[List[str]] = None
    shift_types: Optional[List[str]] = None
    preferred_periods: Optional[List[str]] = None
    preferred_days: Optional[List[str]] = None
    accepts_fixed_shifts: Optional[bool] = None
    accepts_temporary_shifts: Optional[bool] = None
    max_distance_km: Optional[int] = None
    state: Optional[str] = None
    cities_of_work: Optional[str] = None
    acls: Optional[bool] = None
    bls: Optional[bool] = None
    atls: Optional[bool] = None
    pals: Optional[bool] = None
    other_certifications: Optional[str] = None
    main_hospitals: Optional[str] = None
    years_of_experience: Optional[str] = None
    has_driver_license: Optional[bool] = None
    has_ehr_experience: Optional[bool] = None
    provides_invoice: Optional[bool] = None
    languages: Optional[str] = None
    specialties: Optional[List[str]] = None
    practice_areas: Optional[List[str]] = None


@dataclass
class DoctorUpdate:
    name: Optional[str] = None
    password: Optional[str] = None
    photo_url: Optional[str] = None
    email: Optional[str] = None
    profession: Optional[str] = None
    council_type: Optional[str] = None
    council_number: Optional[str] = None
    council_state: Optional[str] = None
    crm: Optional[str] = None
    crm_state: Optional[str] = None
    graduation_year: Optional[int] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    main_specialty: Optional[str] = None
    procedures: Optional[List[str]] = None
    shift_types: Optional[List[str]] = None
    preferred_periods: Optional[List[str]] = None
    preferred_days: Optional[List[str]] = None
    accepts_fixed_shifts: Optional[bool] = None
    accepts_temporary_shifts: Optional[bool] = None
    max_distance_km: Optional[int] = None
    state: Optional[str] = None
    cities_of_work: Optional[str] = None
    acls: Optional[bool] = None
    bls: Optional[bool] = None
    atls: Optional[bool] = None
    pals: Optional[bool] = None
    other_certifications: Optional[str] = None
    main_hospitals: Optional[str] = None
    years_of_experience: Optional[str] = None
    has_driver_license: Optional[bool] = None
    has_ehr_experience: Optional[bool] = None
    provides_invoice: Optional[bool] = None
    languages: Optional[str] = None
    specialties: Optional[List[str]] = field(default=None)
    practice_areas: Optional[List[str]] = field(default=None)
