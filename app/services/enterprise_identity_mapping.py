from __future__ import annotations

from app.enterprise_onboarding_models import RoleMappingRule
from app.rbac.roles import EnterpriseRole

_HIGH_PRIV_ROLES = {
    EnterpriseRole.TENANT_ADMIN,
    EnterpriseRole.SUPER_ADMIN,
}


def validate_role_mapping_rules(rules: list[RoleMappingRule]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    high_priv_count = 0
    for r in rules:
        key = r.external_group_or_claim.strip().lower()
        if key in seen:
            errors.append(f"Duplicate mapping key: {r.external_group_or_claim}")
        seen.add(key)
        if r.mapped_role in _HIGH_PRIV_ROLES:
            high_priv_count += 1
    if high_priv_count > 2:
        errors.append("Too many high-privilege role mappings; review least-privilege alignment.")
    return errors
