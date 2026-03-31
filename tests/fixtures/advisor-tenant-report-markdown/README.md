# Advisor Tenant Report – Markdown-Goldens (Brief-Abschnitt)

Diese Dateien enthalten **nur** den Abschnitt **„Governance-Reife – Kurzüberblick“**, wie er von `render_advisor_governance_maturity_brief_markdown_section` erzeugt wird.

- **Quelle:** `tests/fixtures/advisor-governance-maturity-brief/scenario_*_llm.json` (Fake-LLM-JSON) + passender Snapshot aus `tests/advisor_brief_scenario_snapshots.py`, danach `parse_advisor_governance_maturity_brief` → `render_…`.
- **Regeneration** (bei bewusster Anpassung von Parse/Render):

```bash
cd /path/to/Compliance-Hub
PYTHONPATH=app:tests:. python -c "
from pathlib import Path
from advisor_brief_scenario_snapshots import SCENARIO_SNAPSHOTS
from app.services.advisor_governance_maturity_brief_parse import parse_advisor_governance_maturity_brief
from app.services.advisor_governance_maturity_brief_markdown import render_advisor_governance_maturity_brief_markdown_section
ROOT = Path('tests/fixtures')
for sid in 'abcd':
    snap = SCENARIO_SNAPSHOTS[sid]
    raw = (ROOT / 'advisor-governance-maturity-brief' / f'scenario_{sid}_llm.json').read_text(encoding='utf-8')
    out = parse_advisor_governance_maturity_brief(raw, snap)
    md = render_advisor_governance_maturity_brief_markdown_section(out.brief)
    (ROOT / 'advisor-tenant-report-markdown' / f'scenario_{sid}_brief_section.md').write_text(md, encoding='utf-8')
"
```

Tests vergleichen normalisierte Zeilenenden (trailing whitespace entfernt).
