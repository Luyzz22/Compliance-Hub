"""Enterprise IAM services — IdP management, SCIM provisioning, Access Reviews, User Lifecycle."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import (
    AccessReviewDB,
    ExternalIdentityDB,
    IdentityProviderDB,
    SCIMSyncStateDB,
    UserDB,
    UserTenantRoleDB,
)
from app.rbac.roles import EnterpriseRole

logger = logging.getLogger(__name__)

# Privileged roles that require periodic access review / recertification.
PRIVILEGED_ROLES = frozenset({"super_admin", "tenant_admin", "compliance_admin", "auditor"})

# Default access review period (days).
ACCESS_REVIEW_PERIOD_DAYS = 90

# Sentinel value for SSO/SCIM users who have no local password.
# Downstream login logic (IdentityService.login) must reject local password authentication
# for users whose password_hash equals this sentinel.  bcrypt.checkpw will never match it
# because it is not a valid bcrypt hash, so local login attempts fail as expected.
_NO_LOCAL_PASSWORD = "!SSO_OR_SCIM_NO_LOCAL_PASSWORD"

# Valid role values for role mapping validation.
_VALID_ROLES = frozenset(r.value for r in EnterpriseRole)


# ── Identity Provider Service ────────────────────────────────────────────────


class IdentityProviderService:
    """CRUD for external Identity Provider configurations (SAML / OIDC)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_provider(
        self,
        tenant_id: str,
        slug: str,
        display_name: str,
        protocol: str,
        *,
        issuer_url: str | None = None,
        metadata_url: str | None = None,
        client_id: str | None = None,
        attribute_mapping: dict | None = None,
        default_role: str = "viewer",
    ) -> dict:
        if protocol not in ("saml", "oidc"):
            return {"error": "invalid_protocol", "detail": "protocol must be 'saml' or 'oidc'"}
        existing = self._session.execute(
            select(IdentityProviderDB).where(
                IdentityProviderDB.tenant_id == tenant_id,
                IdentityProviderDB.slug == slug,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return {"error": "slug_taken", "detail": f"IdP slug '{slug}' already in use"}
        now = datetime.now(UTC)
        idp = IdentityProviderDB(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            slug=slug,
            display_name=display_name,
            protocol=protocol,
            issuer_url=issuer_url,
            metadata_url=metadata_url,
            client_id=client_id,
            attribute_mapping=json.dumps(attribute_mapping) if attribute_mapping else None,
            default_role=default_role,
            enabled=True,
            created_at_utc=now,
            updated_at_utc=now,
        )
        self._session.add(idp)
        self._session.commit()
        self._session.refresh(idp)
        return self._to_dict(idp)

    def get_provider(self, tenant_id: str, provider_id: str) -> dict | None:
        idp = self._session.execute(
            select(IdentityProviderDB).where(
                IdentityProviderDB.id == provider_id,
                IdentityProviderDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if idp is None:
            return None
        return self._to_dict(idp)

    def list_providers(self, tenant_id: str) -> list[dict]:
        rows = (
            self._session.execute(
                select(IdentityProviderDB).where(IdentityProviderDB.tenant_id == tenant_id)
            )
            .scalars()
            .all()
        )
        return [self._to_dict(r) for r in rows]

    def update_provider(self, tenant_id: str, provider_id: str, **kwargs: object) -> dict | None:
        idp = self._session.execute(
            select(IdentityProviderDB).where(
                IdentityProviderDB.id == provider_id,
                IdentityProviderDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if idp is None:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(idp, key):
                if key == "attribute_mapping" and isinstance(value, dict):
                    setattr(idp, key, json.dumps(value))
                else:
                    setattr(idp, key, value)
        idp.updated_at_utc = datetime.now(UTC)
        self._session.commit()
        self._session.refresh(idp)
        return self._to_dict(idp)

    def delete_provider(self, tenant_id: str, provider_id: str) -> bool:
        idp = self._session.execute(
            select(IdentityProviderDB).where(
                IdentityProviderDB.id == provider_id,
                IdentityProviderDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if idp is None:
            return False
        self._session.delete(idp)
        self._session.commit()
        return True

    @staticmethod
    def _to_dict(idp: IdentityProviderDB) -> dict:
        return {
            "id": idp.id,
            "tenant_id": idp.tenant_id,
            "slug": idp.slug,
            "display_name": idp.display_name,
            "protocol": idp.protocol,
            "issuer_url": idp.issuer_url,
            "metadata_url": idp.metadata_url,
            "client_id": idp.client_id,
            "attribute_mapping": (
                json.loads(idp.attribute_mapping) if idp.attribute_mapping else None
            ),
            "default_role": idp.default_role,
            "enabled": idp.enabled,
            "created_at_utc": idp.created_at_utc.isoformat() if idp.created_at_utc else None,
        }


# ── SSO Callback (attribute mapping) ────────────────────────────────────────


class SSOCallbackService:
    """Handle SSO login callback — map IdP attributes to local user + role."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def process_sso_login(
        self,
        provider_id: str,
        tenant_id: str,
        external_subject: str,
        external_email: str,
        external_attributes: dict | None = None,
    ) -> dict:
        """Process SSO login callback. Creates or links user, assigns role from mapping."""
        idp = self._session.execute(
            select(IdentityProviderDB).where(
                IdentityProviderDB.id == provider_id,
                IdentityProviderDB.tenant_id == tenant_id,
                IdentityProviderDB.enabled.is_(True),
            )
        ).scalar_one_or_none()
        if idp is None:
            return {"error": "provider_not_found", "detail": "IdP not found or disabled"}

        # Look for existing external identity link
        ext_identity = self._session.execute(
            select(ExternalIdentityDB).where(
                ExternalIdentityDB.provider_id == provider_id,
                ExternalIdentityDB.external_subject == external_subject,
            )
        ).scalar_one_or_none()

        now = datetime.now(UTC)
        is_new_link = False

        if ext_identity is not None:
            # Existing linked user — update attributes
            user = self._session.execute(
                select(UserDB).where(UserDB.id == ext_identity.user_id)
            ).scalar_one_or_none()
            if user is None:
                return {"error": "user_not_found", "detail": "Linked user no longer exists"}
            if not user.is_active:
                return {"error": "account_disabled", "detail": "Account is disabled"}
            ext_identity.external_email = external_email
            ext_identity.external_attributes = (
                json.dumps(external_attributes) if external_attributes else None
            )
            ext_identity.updated_at_utc = now
            self._session.commit()
        else:
            is_new_link = True
            # Try to match by email, or create new user
            email_norm = external_email.strip().lower()
            user = self._session.execute(
                select(UserDB).where(UserDB.email == email_norm)
            ).scalar_one_or_none()
            if user is None:
                # Auto-provision user (SSO-only, no password)
                user = UserDB(
                    id=str(uuid.uuid4()),
                    email=email_norm,
                    password_hash=_NO_LOCAL_PASSWORD,  # SSO-only user, no local password
                    display_name=external_email.split("@")[0],
                    email_verified=True,
                    is_active=True,
                    sso_provider=idp.slug,
                    sso_subject=external_subject,
                    created_at_utc=now,
                    updated_at_utc=now,
                )
                self._session.add(user)
                self._session.flush()
            # Create external identity link
            ext_identity = ExternalIdentityDB(
                id=str(uuid.uuid4()),
                provider_id=provider_id,
                user_id=user.id,
                external_subject=external_subject,
                external_email=external_email,
                external_attributes=(
                    json.dumps(external_attributes) if external_attributes else None
                ),
                created_at_utc=now,
                updated_at_utc=now,
            )
            self._session.add(ext_identity)

        # Resolve role from attribute mapping
        role = idp.default_role
        if idp.attribute_mapping and external_attributes:
            mapping = json.loads(idp.attribute_mapping)
            role_attr = mapping.get("role")
            if role_attr and role_attr in external_attributes:
                mapped_role = external_attributes[role_attr]
                if isinstance(mapped_role, str) and mapped_role.strip():
                    candidate = mapped_role.strip().lower()
                    # Validate against known roles; fall back to default for invalid values
                    if candidate in _VALID_ROLES:
                        role = candidate
                    else:
                        logger.warning(
                            "SSO role mapping: unknown role %r from IdP %s, using default %s",
                            candidate,
                            idp.slug,
                            idp.default_role,
                        )

        # Assign/update tenant role
        existing_role = self._session.execute(
            select(UserTenantRoleDB).where(
                UserTenantRoleDB.user_id == user.id,
                UserTenantRoleDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if existing_role is None:
            role_assignment = UserTenantRoleDB(
                id=str(uuid.uuid4()),
                user_id=user.id,
                tenant_id=tenant_id,
                role=role,
                assigned_by="system:sso",
                created_at_utc=now,
                updated_at_utc=now,
            )
            self._session.add(role_assignment)
        else:
            existing_role.role = role
            existing_role.assigned_by = "system:sso"
            existing_role.updated_at_utc = now

        self._session.commit()

        return {
            "user_id": user.id,
            "email": user.email,
            "tenant_id": tenant_id,
            "role": role,
            "sso_provider": idp.slug,
            "is_new_user": is_new_link,
        }


# ── SCIM 2.0 Provisioning Service ───────────────────────────────────────────


class SCIMProvisioningService:
    """SCIM 2.0 user provisioning lifecycle (create/update/disable/deprovision)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def provision_user(
        self,
        tenant_id: str,
        email: str,
        display_name: str | None = None,
        scim_external_id: str | None = None,
        role: str = "viewer",
        sync_source: str | None = None,
    ) -> dict:
        """Create or re-activate a SCIM-provisioned user."""
        email_norm = email.strip().lower()
        now = datetime.now(UTC)
        user = self._session.execute(
            select(UserDB).where(UserDB.email == email_norm)
        ).scalar_one_or_none()

        if user is None:
            user = UserDB(
                id=str(uuid.uuid4()),
                email=email_norm,
                password_hash=_NO_LOCAL_PASSWORD,  # SCIM-provisioned, no local password
                display_name=display_name,
                email_verified=True,
                is_active=True,
                created_at_utc=now,
                updated_at_utc=now,
            )
            self._session.add(user)
            self._session.flush()
        else:
            # Re-activate if disabled
            if not user.is_active:
                user.is_active = True
                user.updated_at_utc = now

        # Assign tenant role
        existing_role = self._session.execute(
            select(UserTenantRoleDB).where(
                UserTenantRoleDB.user_id == user.id,
                UserTenantRoleDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if existing_role is None:
            self._session.add(
                UserTenantRoleDB(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    tenant_id=tenant_id,
                    role=role,
                    assigned_by="system:scim",
                    created_at_utc=now,
                    updated_at_utc=now,
                )
            )
        else:
            existing_role.role = role
            existing_role.assigned_by = "system:scim"
            existing_role.updated_at_utc = now

        # SCIM sync state
        sync = self._session.execute(
            select(SCIMSyncStateDB).where(
                SCIMSyncStateDB.tenant_id == tenant_id,
                SCIMSyncStateDB.user_id == user.id,
            )
        ).scalar_one_or_none()
        if sync is None:
            sync = SCIMSyncStateDB(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                user_id=user.id,
                scim_external_id=scim_external_id,
                provision_status="active",
                last_sync_at=now,
                sync_source=sync_source,
                created_at_utc=now,
                updated_at_utc=now,
            )
            self._session.add(sync)
        else:
            sync.provision_status = "active"
            sync.scim_external_id = scim_external_id
            sync.last_sync_at = now
            sync.sync_source = sync_source
            sync.updated_at_utc = now

        self._session.commit()
        return {
            "user_id": user.id,
            "email": user.email,
            "tenant_id": tenant_id,
            "role": role,
            "provision_status": "active",
        }

    def update_user(
        self,
        tenant_id: str,
        user_id: str,
        *,
        display_name: str | None = None,
        role: str | None = None,
        scim_external_id: str | None = None,
    ) -> dict | None:
        """Update SCIM-provisioned user attributes and/or role."""
        user = self._session.execute(
            select(UserDB).where(UserDB.id == user_id)
        ).scalar_one_or_none()
        if user is None:
            return None
        now = datetime.now(UTC)
        if display_name is not None:
            user.display_name = display_name
            user.updated_at_utc = now
        if role is not None:
            existing_role = self._session.execute(
                select(UserTenantRoleDB).where(
                    UserTenantRoleDB.user_id == user_id,
                    UserTenantRoleDB.tenant_id == tenant_id,
                )
            ).scalar_one_or_none()
            if existing_role:
                existing_role.role = role
                existing_role.assigned_by = "system:scim"
                existing_role.updated_at_utc = now
        # Update sync state
        sync = self._session.execute(
            select(SCIMSyncStateDB).where(
                SCIMSyncStateDB.tenant_id == tenant_id,
                SCIMSyncStateDB.user_id == user_id,
            )
        ).scalar_one_or_none()
        if sync:
            sync.last_sync_at = now
            if scim_external_id is not None:
                sync.scim_external_id = scim_external_id
            sync.updated_at_utc = now
        self._session.commit()
        return {
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "tenant_id": tenant_id,
        }

    def disable_user(self, tenant_id: str, user_id: str) -> dict | None:
        """Soft-disable a SCIM-provisioned user (does NOT delete)."""
        user = self._session.execute(
            select(UserDB).where(UserDB.id == user_id)
        ).scalar_one_or_none()
        if user is None:
            return None
        now = datetime.now(UTC)
        user.is_active = False
        user.updated_at_utc = now
        sync = self._session.execute(
            select(SCIMSyncStateDB).where(
                SCIMSyncStateDB.tenant_id == tenant_id,
                SCIMSyncStateDB.user_id == user_id,
            )
        ).scalar_one_or_none()
        if sync:
            sync.provision_status = "disabled"
            sync.last_sync_at = now
            sync.updated_at_utc = now
        self._session.commit()
        return {
            "user_id": user.id,
            "email": user.email,
            "tenant_id": tenant_id,
            "provision_status": "disabled",
        }

    def deprovision_user(self, tenant_id: str, user_id: str) -> dict | None:
        """Soft-deprovision: disable + mark as deprovisioned (no hard delete)."""
        user = self._session.execute(
            select(UserDB).where(UserDB.id == user_id)
        ).scalar_one_or_none()
        if user is None:
            return None
        now = datetime.now(UTC)
        user.is_active = False
        user.updated_at_utc = now
        sync = self._session.execute(
            select(SCIMSyncStateDB).where(
                SCIMSyncStateDB.tenant_id == tenant_id,
                SCIMSyncStateDB.user_id == user_id,
            )
        ).scalar_one_or_none()
        if sync:
            sync.provision_status = "deprovisioned"
            sync.last_sync_at = now
            sync.updated_at_utc = now
        self._session.commit()
        return {
            "user_id": user.id,
            "email": user.email,
            "tenant_id": tenant_id,
            "provision_status": "deprovisioned",
        }

    def get_sync_state(self, tenant_id: str, user_id: str) -> dict | None:
        sync = self._session.execute(
            select(SCIMSyncStateDB).where(
                SCIMSyncStateDB.tenant_id == tenant_id,
                SCIMSyncStateDB.user_id == user_id,
            )
        ).scalar_one_or_none()
        if sync is None:
            return None
        return {
            "user_id": sync.user_id,
            "tenant_id": sync.tenant_id,
            "scim_external_id": sync.scim_external_id,
            "provision_status": sync.provision_status,
            "last_sync_at": sync.last_sync_at.isoformat() if sync.last_sync_at else None,
            "sync_source": sync.sync_source,
        }


# ── Access Review Service ────────────────────────────────────────────────────


class AccessReviewService:
    """Create and manage access reviews / recertification for privileged roles."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_review(
        self,
        tenant_id: str,
        target_user_id: str,
        target_role: str,
        reviewer_user_id: str | None = None,
        deadline_days: int = ACCESS_REVIEW_PERIOD_DAYS,
    ) -> dict:
        now = datetime.now(UTC)
        review = AccessReviewDB(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            target_user_id=target_user_id,
            target_role=target_role,
            reviewer_user_id=reviewer_user_id,
            status="pending",
            deadline_utc=now + timedelta(days=deadline_days),
            created_at_utc=now,
            updated_at_utc=now,
        )
        self._session.add(review)
        self._session.commit()
        self._session.refresh(review)
        return self._to_dict(review)

    def decide_review(
        self,
        tenant_id: str,
        review_id: str,
        decision: str,
        reviewer_user_id: str,
        decision_note: str | None = None,
    ) -> dict | None:
        """Record a review decision (approved / revoked / escalated)."""
        if decision not in ("approved", "revoked", "escalated"):
            return {"error": "invalid_decision", "detail": "Must be approved/revoked/escalated"}
        review = self._session.execute(
            select(AccessReviewDB).where(
                AccessReviewDB.id == review_id,
                AccessReviewDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if review is None:
            return None
        now = datetime.now(UTC)
        review.status = decision
        review.reviewer_user_id = reviewer_user_id
        review.decision_note = decision_note
        review.decided_at_utc = now
        review.updated_at_utc = now

        # If revoked, remove the tenant role
        if decision == "revoked":
            role_assignment = self._session.execute(
                select(UserTenantRoleDB).where(
                    UserTenantRoleDB.user_id == review.target_user_id,
                    UserTenantRoleDB.tenant_id == tenant_id,
                )
            ).scalar_one_or_none()
            if role_assignment:
                role_assignment.role = "viewer"  # downgrade to least-privilege
                role_assignment.assigned_by = "system:access_review"
                role_assignment.updated_at_utc = now

        self._session.commit()
        self._session.refresh(review)
        return self._to_dict(review)

    def list_reviews(
        self,
        tenant_id: str,
        *,
        status_filter: str | None = None,
    ) -> list[dict]:
        stmt = select(AccessReviewDB).where(AccessReviewDB.tenant_id == tenant_id)
        if status_filter:
            stmt = stmt.where(AccessReviewDB.status == status_filter)
        stmt = stmt.order_by(AccessReviewDB.created_at_utc.desc())
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_dict(r) for r in rows]

    def get_review(self, tenant_id: str, review_id: str) -> dict | None:
        review = self._session.execute(
            select(AccessReviewDB).where(
                AccessReviewDB.id == review_id,
                AccessReviewDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if review is None:
            return None
        return self._to_dict(review)

    def list_overdue_reviews(self, tenant_id: str) -> list[dict]:
        """Return pending reviews past their deadline."""
        now = datetime.now(UTC)
        stmt = (
            select(AccessReviewDB)
            .where(
                AccessReviewDB.tenant_id == tenant_id,
                AccessReviewDB.status == "pending",
                AccessReviewDB.deadline_utc < now,
            )
            .order_by(AccessReviewDB.deadline_utc.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_dict(r) for r in rows]

    def create_reviews_for_privileged_roles(
        self,
        tenant_id: str,
        reviewer_user_id: str | None = None,
        deadline_days: int = ACCESS_REVIEW_PERIOD_DAYS,
    ) -> list[dict]:
        """Bulk-create reviews for all users with privileged roles in a tenant."""
        stmt = select(UserTenantRoleDB).where(
            UserTenantRoleDB.tenant_id == tenant_id,
            UserTenantRoleDB.role.in_(list(PRIVILEGED_ROLES)),
        )
        role_assignments = self._session.execute(stmt).scalars().all()
        results = []
        for ra in role_assignments:
            # Skip if a pending review already exists for this user+role
            existing = self._session.execute(
                select(AccessReviewDB).where(
                    AccessReviewDB.tenant_id == tenant_id,
                    AccessReviewDB.target_user_id == ra.user_id,
                    AccessReviewDB.target_role == ra.role,
                    AccessReviewDB.status == "pending",
                )
            ).scalar_one_or_none()
            if existing is not None:
                continue
            review = self.create_review(
                tenant_id=tenant_id,
                target_user_id=ra.user_id,
                target_role=ra.role,
                reviewer_user_id=reviewer_user_id,
                deadline_days=deadline_days,
            )
            results.append(review)
        return results

    @staticmethod
    def _to_dict(review: AccessReviewDB) -> dict:
        return {
            "id": review.id,
            "tenant_id": review.tenant_id,
            "target_user_id": review.target_user_id,
            "target_role": review.target_role,
            "reviewer_user_id": review.reviewer_user_id,
            "status": review.status,
            "decision_note": review.decision_note,
            "deadline_utc": review.deadline_utc.isoformat() if review.deadline_utc else None,
            "decided_at_utc": (
                review.decided_at_utc.isoformat() if review.decided_at_utc else None
            ),
            "created_at_utc": (
                review.created_at_utc.isoformat() if review.created_at_utc else None
            ),
        }


# ── User Lifecycle Management Service ────────────────────────────────────────


class UserLifecycleService:
    """Joiner / Mover / Leaver lifecycle management."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def joiner(
        self,
        tenant_id: str,
        user_id: str,
        role: str = "viewer",
        assigned_by: str | None = None,
    ) -> dict | None:
        """Activate user in tenant with initial role (Joiner flow)."""
        user = self._session.execute(
            select(UserDB).where(UserDB.id == user_id)
        ).scalar_one_or_none()
        if user is None:
            return None
        now = datetime.now(UTC)
        user.is_active = True
        user.updated_at_utc = now
        existing_role = self._session.execute(
            select(UserTenantRoleDB).where(
                UserTenantRoleDB.user_id == user_id,
                UserTenantRoleDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if existing_role is None:
            self._session.add(
                UserTenantRoleDB(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    tenant_id=tenant_id,
                    role=role,
                    assigned_by=assigned_by or "system:lifecycle",
                    created_at_utc=now,
                    updated_at_utc=now,
                )
            )
        else:
            existing_role.role = role
            existing_role.assigned_by = assigned_by or "system:lifecycle"
            existing_role.updated_at_utc = now
        self._session.commit()
        return {
            "user_id": user.id,
            "email": user.email,
            "tenant_id": tenant_id,
            "role": role,
            "lifecycle_event": "joiner",
        }

    def mover(
        self,
        tenant_id: str,
        user_id: str,
        new_role: str,
        assigned_by: str | None = None,
    ) -> dict | None:
        """Update user role on department/role change (Mover flow).

        Replaces existing role to prevent privilege accumulation.
        """
        user = self._session.execute(
            select(UserDB).where(UserDB.id == user_id)
        ).scalar_one_or_none()
        if user is None:
            return None
        now = datetime.now(UTC)
        existing_role = self._session.execute(
            select(UserTenantRoleDB).where(
                UserTenantRoleDB.user_id == user_id,
                UserTenantRoleDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        old_role = existing_role.role if existing_role else None
        if existing_role is None:
            self._session.add(
                UserTenantRoleDB(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    tenant_id=tenant_id,
                    role=new_role,
                    assigned_by=assigned_by or "system:lifecycle",
                    created_at_utc=now,
                    updated_at_utc=now,
                )
            )
        else:
            existing_role.role = new_role
            existing_role.assigned_by = assigned_by or "system:lifecycle"
            existing_role.updated_at_utc = now
        self._session.commit()
        return {
            "user_id": user.id,
            "email": user.email,
            "tenant_id": tenant_id,
            "old_role": old_role,
            "new_role": new_role,
            "lifecycle_event": "mover",
        }

    def leaver(self, tenant_id: str, user_id: str) -> dict | None:
        """Disable user and downgrade role (Leaver flow)."""
        user = self._session.execute(
            select(UserDB).where(UserDB.id == user_id)
        ).scalar_one_or_none()
        if user is None:
            return None
        now = datetime.now(UTC)
        user.is_active = False
        user.updated_at_utc = now
        # Downgrade role to viewer (least privilege)
        existing_role = self._session.execute(
            select(UserTenantRoleDB).where(
                UserTenantRoleDB.user_id == user_id,
                UserTenantRoleDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        old_role = None
        if existing_role:
            old_role = existing_role.role
            existing_role.role = "viewer"
            existing_role.assigned_by = "system:lifecycle"
            existing_role.updated_at_utc = now
        self._session.commit()
        return {
            "user_id": user.id,
            "email": user.email,
            "tenant_id": tenant_id,
            "old_role": old_role,
            "is_active": False,
            "lifecycle_event": "leaver",
        }

    def get_user_status(self, tenant_id: str, user_id: str) -> dict | None:
        """Return user lifecycle status for a specific tenant."""
        user = self._session.execute(
            select(UserDB).where(UserDB.id == user_id)
        ).scalar_one_or_none()
        if user is None:
            return None
        role_assignment = self._session.execute(
            select(UserTenantRoleDB).where(
                UserTenantRoleDB.user_id == user_id,
                UserTenantRoleDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        scim_sync = self._session.execute(
            select(SCIMSyncStateDB).where(
                SCIMSyncStateDB.user_id == user_id,
                SCIMSyncStateDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        return {
            "user_id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "role": role_assignment.role if role_assignment else None,
            "tenant_id": tenant_id,
            "provision_status": scim_sync.provision_status if scim_sync else None,
            "sso_provider": user.sso_provider,
        }
