"""Compatibilidade médico x requisitos de certificação da vaga."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Query

from app.models.doctor import Doctor
from app.models.shift_opportunity import ShiftOpportunity

REQUIREMENT_FIELDS = (
    ("requires_acls", "acls", "ACLS"),
    ("requires_bls", "bls", "BLS"),
    ("requires_atls", "atls", "ATLS"),
    ("requires_pals", "pals", "PALS"),
)


def doctor_meets_requirements(
    doctor: Doctor, opportunity: ShiftOpportunity
) -> tuple[bool, str | None]:
    missing: list[str] = []
    for req_attr, doctor_attr, label in REQUIREMENT_FIELDS:
        if getattr(opportunity, req_attr, False) and not getattr(
            doctor, doctor_attr, False
        ):
            missing.append(label)
    if missing:
        return False, f"Esta vaga exige: {', '.join(missing)}"
    return True, None


def apply_requirements_filter(query: Query, doctor: Doctor | None) -> Query:
    """Oculta vagas cujo requisito o médico não atende."""
    if not doctor:
        return query

    for req_attr, doctor_attr, _ in REQUIREMENT_FIELDS:
        if not getattr(doctor, doctor_attr, False):
            req_col = getattr(ShiftOpportunity, req_attr)
            query = query.filter(or_(req_col.is_(False), req_col.is_(None)))
    return query
