"""DATEV EXTF (ASCII) export module — GoBD-compliant booking export.

Supports:
- Bußgelder (fines), GRC-Beraterhonorare (consulting), Zertifizierungskosten, Versicherungsprämien
- SKR03/SKR04 account mapping
- EXTF header + booking lines
- Checksum validation
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# DATEV EXTF header format version
EXTF_FORMAT_VERSION = "510"
EXTF_FORMAT_CATEGORY = 21  # Buchungsstapel
EXTF_FORMAT_NAME = "Buchungsstapel"


class DatevBookingRecord(BaseModel):
    """Single DATEV booking record (Buchungssatz)."""

    umsatz: float = Field(..., description="Betrag in EUR (positiv)")
    soll_haben: str = Field(..., pattern=r"^[SH]$", description="S=Soll, H=Haben")
    konto: int = Field(..., ge=1, le=99999, description="Konto (SKR03/SKR04)")
    gegenkonto: int = Field(..., ge=1, le=99999, description="Gegenkonto")
    belegdatum: str = Field(..., pattern=r"^\d{4}$", description="DDMM format")
    buchungstext: str = Field(..., max_length=60)
    beleg1: str = Field(default="", max_length=36)
    beleg2: str = Field(default="", max_length=36)
    kostenstelle: str = Field(default="", max_length=36)
    booking_type: str = Field(
        default="bussgeld",
        description="bussgeld|beratung|zertifizierung|versicherung",
    )

    @field_validator("buchungstext")
    @classmethod
    def truncate_buchungstext(cls, v: str) -> str:
        return v[:60]


# SKR03 default account mappings for GRC-relevant booking types
SKR03_ACCOUNTS: dict[str, dict[str, int]] = {
    "bussgeld": {"konto": 6880, "gegenkonto": 1200},
    "beratung": {"konto": 6825, "gegenkonto": 1200},
    "zertifizierung": {"konto": 6827, "gegenkonto": 1200},
    "versicherung": {"konto": 6400, "gegenkonto": 1200},
}

SKR04_ACCOUNTS: dict[str, dict[str, int]] = {
    "bussgeld": {"konto": 7680, "gegenkonto": 1800},
    "beratung": {"konto": 7625, "gegenkonto": 1800},
    "zertifizierung": {"konto": 7627, "gegenkonto": 1800},
    "versicherung": {"konto": 7400, "gegenkonto": 1800},
}


def get_default_accounts(booking_type: str, skr: str = "SKR03") -> dict[str, int]:
    """Return default Konto/Gegenkonto for a booking type."""
    mapping = SKR03_ACCOUNTS if skr == "SKR03" else SKR04_ACCOUNTS
    return mapping.get(booking_type, {"konto": 9999, "gegenkonto": 1200})


def validate_records(records: list[DatevBookingRecord]) -> list[str]:
    """Validate a batch of booking records. Returns list of error messages."""
    errors: list[str] = []
    for i, rec in enumerate(records):
        if rec.umsatz <= 0:
            errors.append(f"Record {i}: umsatz must be positive")
        if not rec.buchungstext.strip():
            errors.append(f"Record {i}: buchungstext is required")
        if len(rec.belegdatum) != 4:
            errors.append(f"Record {i}: belegdatum must be DDMM (4 digits)")
    return errors


def render_extf_header(
    *,
    berater_nr: str = "0",
    mandanten_nr: str = "0",
    wj_beginn: str = "",
    datum_von: str = "",
    datum_bis: str = "",
    bezeichnung: str = "ComplianceHub GRC Export",
) -> str:
    """Render DATEV EXTF header line."""
    wj = wj_beginn or datetime.now(UTC).strftime("%Y") + "0101"
    von = datum_von or datetime.now(UTC).strftime("%Y%m%d")
    bis = datum_bis or datetime.now(UTC).strftime("%Y%m%d")
    created = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")[:17]
    parts = [
        '"EXTF"',
        EXTF_FORMAT_VERSION,
        str(EXTF_FORMAT_CATEGORY),
        f'"{EXTF_FORMAT_NAME}"',
        "13",  # Format-Version
        created,
        "",  # reserved
        "",  # reserved
        '"CH"',  # Herkunft
        '"ComplianceHub"',
        "",
        "",
        f'"{berater_nr}"',
        f'"{mandanten_nr}"',
        f"{wj}",
        "4",  # Sachkontenlänge
        f"{von}",
        f"{bis}",
        f'"{bezeichnung}"',
        "",
        "1",  # Festschreibung
        "EUR",
    ]
    return ";".join(parts)


def render_extf_booking_line(rec: DatevBookingRecord) -> str:
    """Render single EXTF booking line."""
    umsatz_str = f"{rec.umsatz:.2f}".replace(".", ",")
    parts = [
        umsatz_str,
        f'"{rec.soll_haben}"',
        "",  # WKZ
        "",  # Kurs
        "",  # Basis-Umsatz
        str(rec.konto),
        str(rec.gegenkonto),
        "",  # BU-Schlüssel
        rec.belegdatum,
        f'"{rec.beleg1}"',
        "",  # Belegfeld 2
        "",  # Skonto
        f'"{rec.buchungstext}"',
        "",  # Postensperre
        "",  # Diverse Adressnr.
        "",  # Geschäftspartnerbank
        "",  # Sachverhalt
        "",  # Zinssperre
        "",  # Beleglink
        "",  # Beleginfo
        f'"{rec.kostenstelle}"',
    ]
    return ";".join(parts)


def render_extf_export(
    records: list[DatevBookingRecord],
    *,
    berater_nr: str = "0",
    mandanten_nr: str = "0",
    datum_von: str = "",
    datum_bis: str = "",
) -> str:
    """Render complete DATEV EXTF ASCII export."""
    lines: list[str] = []
    lines.append(
        render_extf_header(
            berater_nr=berater_nr,
            mandanten_nr=mandanten_nr,
            datum_von=datum_von,
            datum_bis=datum_bis,
        )
    )
    # Column header line
    lines.append(
        "Umsatz;Soll/Haben;WKZ;Kurs;Basis-Umsatz;Konto;Gegenkonto;"
        "BU-Schluessel;Belegdatum;Belegfeld1;Belegfeld2;Skonto;"
        "Buchungstext;Postensperre;Diverse_Adressnr;Geschaeftspartnerbank;"
        "Sachverhalt;Zinssperre;Beleglink;Beleginfo;Kostenstelle"
    )
    for rec in records:
        lines.append(render_extf_booking_line(rec))
    return "\r\n".join(lines) + "\r\n"


def compute_checksum(content: str) -> str:
    """Compute SHA-256 checksum of EXTF content."""
    return hashlib.sha256(content.encode("cp1252", errors="replace")).hexdigest()
