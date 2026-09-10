"""Compatibilidade profissional x requisitos da vaga (profissão + certificações)."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Query

from app.models.doctor import Doctor
from app.models.shift_opportunity import ShiftOpportunity
from app.utils.professions import (
    PROFESSION_DOCTOR,
    PROFESSION_LABELS_PT,
    normalize_profession,
)

REQUIREMENT_FIELDS = (
    ("requires_acls", "acls", "ACLS"),
    ("requires_bls", "bls", "BLS"),
    ("requires_atls", "atls", "ATLS"),
    ("requires_pals", "pals", "PALS"),
)


def _doctor_profession(doctor: Doctor | None) -> str:
    if not doctor:
        return PROFESSION_DOCTOR
    return normalize_profession(getattr(doctor, "profession", None)) or PROFESSION_DOCTOR


def _opportunity_profession(opportunity: ShiftOpportunity) -> str:
    return (
        normalize_profession(getattr(opportunity, "required_profession", None))
        or PROFESSION_DOCTOR
    )


def doctor_meets_requirements(
    doctor: Doctor, opportunity: ShiftOpportunity
) -> tuple[bool, str | None]:
    doc_prof = _doctor_profession(doctor)
    opp_prof = _opportunity_profession(opportunity)
    if doc_prof != opp_prof:
        label = PROFESSION_LABELS_PT.get(opp_prof, opp_prof)
        return False, f"Esta vaga é exclusiva para: {label}"

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
    """Oculta vagas de outra profissão ou com certificação que o profissional não atende."""
    if not doctor:
        return query

    profession = _doctor_profession(doctor)
    query = query.filter(ShiftOpportunity.required_profession == profession)

    for req_attr, doctor_attr, _ in REQUIREMENT_FIELDS:
        if not getattr(doctor, doctor_attr, False):
            req_col = getattr(ShiftOpportunity, req_attr)
            query = query.filter(or_(req_col.is_(False), req_col.is_(None)))
    return query
