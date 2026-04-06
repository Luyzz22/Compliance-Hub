from __future__ import annotations

from app.compliance_calendar_models import ComplianceDeadlineResponse


def generate_ical(deadlines: list[ComplianceDeadlineResponse], tenant_id: str) -> str:
    """Generate an RFC 5545 compliant iCal calendar string."""
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ComplianceHub//Compliance Calendar//EN",
    ]
    for dl in deadlines:
        dt_str = dl.due_date.strftime("%Y%m%d")
        desc_parts: list[str] = [f"Category: {dl.category.value}"]
        if dl.regulation_reference:
            desc_parts.append(f"Ref: {dl.regulation_reference}")
        if dl.description:
            desc_parts.append(dl.description)
        description = "\\n".join(desc_parts)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"DTSTART;VALUE=DATE:{dt_str}",
                f"SUMMARY:{dl.title}",
                f"DESCRIPTION:{description}",
                f"UID:{dl.id}@compliancehub",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
