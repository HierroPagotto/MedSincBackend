"""Profissões de plantonistas e conselhos associados."""

from __future__ import annotations

PROFESSION_DOCTOR = "doctor"
PROFESSION_NURSE = "nurse"
PROFESSION_NURSING_TECHNICIAN = "nursing_technician"
PROFESSION_ORTHOPEDIC_TECHNICIAN = "orthopedic_technician"

ALLOWED_PROFESSIONS = frozenset(
    {
        PROFESSION_DOCTOR,
        PROFESSION_NURSE,
        PROFESSION_NURSING_TECHNICIAN,
        PROFESSION_ORTHOPEDIC_TECHNICIAN,
    }
)

COUNCIL_CRM = "CRM"
COUNCIL_COREN = "COREN"
COUNCIL_CREFITO = "CREFITO"

PROFESSION_DEFAULT_COUNCIL = {
    PROFESSION_DOCTOR: COUNCIL_CRM,
    PROFESSION_NURSE: COUNCIL_COREN,
    PROFESSION_NURSING_TECHNICIAN: COUNCIL_COREN,
    PROFESSION_ORTHOPEDIC_TECHNICIAN: COUNCIL_CREFITO,
}

PROFESSION_LABELS_PT = {
    PROFESSION_DOCTOR: "Médico",
    PROFESSION_NURSE: "Enfermeiro",
    PROFESSION_NURSING_TECHNICIAN: "Técnico de enfermagem",
    PROFESSION_ORTHOPEDIC_TECHNICIAN: "Técnico em ortopedia",
}

SPECIALTIES_BY_PROFESSION = {
    PROFESSION_DOCTOR: [
        "Clínica médica",
        "Pediatria",
        "PS adulto",
        "PS infantil",
        "UTI adulto",
        "UTI pediátrica",
        "UTI neonatal",
        "Anestesiologia",
        "Cardiologia",
        "Cirurgia geral",
        "Geriatria",
        "Ginecologia e obstetrícia",
        "Medicina de família",
        "Medicina intensiva",
        "Neurologia",
        "Ortopedia",
        "Psiquiatria",
        "Radiologia",
    ],
    PROFESSION_NURSE: [
        "Enfermagem geral",
        "UTI",
        "Pronto-socorro",
        "Centro cirúrgico",
        "Enfermaria",
        "Pediatria",
        "Neonatologia",
        "Obstetrícia",
        "Home care",
    ],
    PROFESSION_NURSING_TECHNICIAN: [
        "Enfermagem geral",
        "UTI",
        "Pronto-socorro",
        "Centro cirúrgico",
        "Enfermaria",
        "Pediatria",
        "Ambulatório",
    ],
    PROFESSION_ORTHOPEDIC_TECHNICIAN: [
        "Imobilizações ortopédicas",
        "Pronto-socorro",
        "Ambulatório ortopédico",
        "Centro cirúrgico",
    ],
}

PRACTICE_AREAS = [
    "UTI adulto",
    "UTI pediátrica",
    "UTI neonatal",
    "Pronto-socorro adulto",
    "Pronto-socorro infantil",
    "Enfermaria",
    "Centro cirúrgico",
    "Ambulatório",
    "Home care",
    "Internação",
    "Telemedicina",
]


def normalize_profession(value: str | None) -> str | None:
    if value is None:
        return None
    profession = str(value).strip().lower()
    if profession not in ALLOWED_PROFESSIONS:
        return None
    return profession


def default_council_for(profession: str | None) -> str | None:
    if not profession:
        return None
    return PROFESSION_DEFAULT_COUNCIL.get(profession)


def validate_profession_payload(
    profession: str | None,
    *,
    council_type: str | None = None,
    require_profession: bool = True,
) -> tuple[str | None, str | None]:
    """Retorna (erro, profession_normalizada)."""
    if not profession or not str(profession).strip():
        if require_profession:
            return "Profissão é obrigatória", None
        return None, None

    normalized = normalize_profession(profession)
    if not normalized:
        return (
            f"Profissão inválida. Use: {', '.join(sorted(ALLOWED_PROFESSIONS))}",
            None,
        )

    if council_type is not None and str(council_type).strip():
        expected = PROFESSION_DEFAULT_COUNCIL[normalized]
        if str(council_type).strip().upper() != expected:
            return (
                f"Conselho inválido para esta profissão. Esperado: {expected}",
                None,
            )

    return None, normalized


def sync_legacy_crm_fields(
    profession: str | None,
    council_type: str | None,
    council_number: str | None,
    council_state: str | None,
) -> dict:
    """Mantém crm/crm_state alinhados quando o conselho é CRM."""
    number = (council_number or "").strip() or None
    state = (council_state or "").strip().upper() or None
    ctype = (council_type or "").strip().upper() or default_council_for(profession)

    if ctype == COUNCIL_CRM:
        return {
            "council_type": COUNCIL_CRM,
            "council_number": number,
            "council_state": state,
            "crm": number,
            "crm_state": state,
        }

    return {
        "council_type": ctype,
        "council_number": number,
        "council_state": state,
        "crm": None,
        "crm_state": None,
    }
