"""
Config center service: feature-flag CRUD, cohort management, canary routing.

Canary routing: every user belongs to at most one cohort. A cohort can carry
`flag_overrides` that merge on top of the global feature-flag defaults to give
that cohort a different runtime behaviour (e.g. bargaining_enabled=true for
a pilot cohort while it is globally false).
"""
from __future__ import annotations

import hmac
import json
import uuid
from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..domain.enums import AuditEventType, UserRole
from ..persistence.repositories.config_repo import ConfigRepository
from ..schemas.config import (
    BootstrapConfigResponse,
    CohortDefinitionCreate,
    CohortDefinitionRead,
    FeatureFlagRead,
)
from ..security import audit as audit_mod
from ..security.errors import ForbiddenError, ResourceNotFoundError
from ..security.rbac import Actor


def _flag_to_schema(flag) -> FeatureFlagRead:
    return FeatureFlagRead(
        id=flag.id,
        key=flag.key,
        value=flag.value,
        value_type=flag.value_type,
        description=flag.description,
        updated_by=flag.updated_by,
        updated_at=flag.updated_at,
    )


def _cohort_to_schema(cohort) -> CohortDefinitionRead:
    return CohortDefinitionRead(
        id=cohort.id,
        cohort_key=cohort.cohort_key,
        name=cohort.name,
        description=cohort.description,
        flag_overrides=cohort.flag_overrides,
        is_active=cohort.is_active,
        created_at=cohort.created_at,
    )


class ConfigService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ConfigRepository(session)

    # ── Feature flags ────────────────────────────────────────────────────
    async def list_flags(self) -> list[FeatureFlagRead]:
        flags = await self.repo.list_flags()
        return [_flag_to_schema(f) for f in flags]

    async def get_flag(self, key: str) -> FeatureFlagRead:
        flag = await self.repo.get_flag(key)
        if flag is None:
            raise ResourceNotFoundError(f"Feature flag '{key}' not found.")
        return _flag_to_schema(flag)

    async def create_flag(
        self,
        *,
        key: str,
        value: str,
        value_type: str = "boolean",
        description: str | None = None,
        actor: Actor,
    ) -> FeatureFlagRead:
        _require_admin(actor)
        flag = await self.repo.create_flag(
            key=key,
            value=value,
            value_type=value_type,
            description=description,
            updated_by=uuid.UUID(actor.user_id),
        )
        await audit_mod.record_audit(
            self.session,
            event_type=AuditEventType.feature_flag_changed,
            actor_id=uuid.UUID(actor.user_id),
            actor_role=actor.role.value,
            resource_type="feature_flag",
            resource_id=key,
            outcome="created",
            detail={"value": value},
        )
        return _flag_to_schema(flag)

    async def set_flag(
        self,
        key: str,
        new_value: str,
        actor: Actor,
        change_reason: str | None = None,
    ) -> FeatureFlagRead:
        _require_admin(actor)
        flag = await self.repo.get_flag(key)
        if flag is None:
            raise ResourceNotFoundError(f"Feature flag '{key}' not found.")
        old_value = flag.value
        await self.repo.update_flag(
            flag,
            new_value=new_value,
            changed_by=uuid.UUID(actor.user_id),
            change_reason=change_reason,
        )
        await audit_mod.record_audit(
            self.session,
            event_type=AuditEventType.feature_flag_changed,
            actor_id=uuid.UUID(actor.user_id),
            actor_role=actor.role.value,
            resource_type="feature_flag",
            resource_id=key,
            outcome="updated",
            detail={"old_value": old_value, "new_value": new_value, "reason": change_reason},
        )
        return _flag_to_schema(flag)

    # ── Cohort management ─────────────────────────────────────────────────
    async def list_cohorts(self) -> list[CohortDefinitionRead]:
        cohorts = await self.repo.list_cohorts()
        return [_cohort_to_schema(c) for c in cohorts]

    async def create_cohort(self, actor: Actor, data: CohortDefinitionCreate) -> CohortDefinitionRead:
        _require_admin(actor)
        cohort = await self.repo.create_cohort(
            cohort_key=data.cohort_key,
            name=data.name,
            description=data.description,
            flag_overrides=data.flag_overrides,
            created_by=uuid.UUID(actor.user_id),
        )
        await audit_mod.record_audit(
            self.session,
            event_type=AuditEventType.cohort_assigned,
            actor_id=uuid.UUID(actor.user_id),
            actor_role=actor.role.value,
            resource_type="cohort",
            resource_id=cohort.cohort_key,
            outcome="created",
        )
        return _cohort_to_schema(cohort)

    async def assign_user_cohort(
        self, cohort_id: uuid.UUID, user_id: uuid.UUID, actor: Actor
    ) -> dict:
        _require_admin(actor)
        cohort = await self.repo.get_cohort(cohort_id)
        if cohort is None:
            raise ResourceNotFoundError("Cohort not found.")
        assignment = await self.repo.assign_user(
            user_id=user_id,
            cohort_id=cohort_id,
            assigned_by=uuid.UUID(actor.user_id),
        )
        await audit_mod.record_audit(
            self.session,
            event_type=AuditEventType.cohort_assigned,
            actor_id=uuid.UUID(actor.user_id),
            actor_role=actor.role.value,
            resource_type="user",
            resource_id=str(user_id),
            outcome="assigned",
            detail={"cohort_key": cohort.cohort_key},
        )
        return {"user_id": str(user_id), "cohort_id": str(cohort_id), "cohort_key": cohort.cohort_key}

    async def remove_user_cohort(self, cohort_id: uuid.UUID, user_id: uuid.UUID, actor: Actor) -> None:
        _require_admin(actor)
        assignment = await self.repo.get_user_assignment(user_id)
        if assignment is None or assignment.cohort_id != cohort_id:
            raise ResourceNotFoundError("User is not assigned to the specified cohort.")
        await self.repo.remove_user_assignment(user_id)

    # ── Canary routing / bootstrap config ────────────────────────────────
    async def resolve_flags_for_user(self, user_id: uuid.UUID) -> tuple[dict[str, str], str | None]:
        """Return (resolved_flags, cohort_key). Cohort overrides win over base flags."""
        base_flags = {f.key: f.value for f in await self.repo.list_flags()}
        assignment = await self.repo.get_user_assignment(user_id)
        cohort_key: str | None = None
        overrides: dict[str, str] = {}
        if assignment is not None:
            cohort = await self.repo.get_cohort(assignment.cohort_id)
            if cohort is not None and cohort.is_active:
                cohort_key = cohort.cohort_key
                overrides = {str(k): str(v) for k, v in (cohort.flag_overrides or {}).items()}
        resolved = {**base_flags, **overrides}
        return resolved, cohort_key

    async def bootstrap_config(self, user_id: uuid.UUID, user_role: str) -> BootstrapConfigResponse:
        base_flags = {f.key: f.value for f in await self.repo.list_flags()}
        assignment = await self.repo.get_user_assignment(user_id)
        cohort_key: str | None = None
        overrides: dict[str, str] = {}
        if assignment is not None:
            cohort = await self.repo.get_cohort(assignment.cohort_id)
            if cohort is not None and cohort.is_active:
                cohort_key = cohort.cohort_key
                overrides = {str(k): str(v) for k, v in (cohort.flag_overrides or {}).items()}
        resolved = {**base_flags, **overrides}
        issued_at = datetime.now(tz=timezone.utc)
        signature = _sign_bootstrap_payload(
            user_id=user_id,
            role=user_role,
            cohort_key=cohort_key,
            resolved=resolved,
            issued_at=issued_at,
        )
        return BootstrapConfigResponse(
            user_id=user_id,
            role=user_role,
            cohort_key=cohort_key,
            feature_flags=base_flags,
            flag_overrides=overrides,
            resolved_flags=resolved,
            issued_at=issued_at,
            signature=signature,
        )


def _require_admin(actor: Actor) -> None:
    if actor.role != UserRole.admin:
        raise ForbiddenError("Admin role required.")


def _canonical_bootstrap_payload(
    *,
    user_id: uuid.UUID,
    role: str,
    cohort_key: str | None,
    resolved: dict[str, str],
    issued_at: datetime,
) -> bytes:
    # Canonicalise via JSON with sorted keys so both signer and verifier agree
    # on byte ordering regardless of dict iteration order.
    doc = {
        "user_id": str(user_id),
        "role": role,
        "cohort_key": cohort_key,
        "resolved_flags": {k: str(v) for k, v in sorted(resolved.items())},
        "issued_at": issued_at.isoformat(),
    }
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sign_bootstrap_payload(
    *,
    user_id: uuid.UUID,
    role: str,
    cohort_key: str | None,
    resolved: dict[str, str],
    issued_at: datetime,
) -> str:
    """HMAC-SHA256 signature of the canonical bootstrap payload using
    Settings.secret_key as the shared key. Replaces the prior keyless sha256
    hash so tampering requires the server secret, not just canonical inputs.
    """
    key = get_settings().secret_key.encode("utf-8")
    body = _canonical_bootstrap_payload(
        user_id=user_id,
        role=role,
        cohort_key=cohort_key,
        resolved=resolved,
        issued_at=issued_at,
    )
    return hmac.new(key, body, sha256).hexdigest()


def verify_bootstrap_signature(
    *,
    user_id: uuid.UUID,
    role: str,
    cohort_key: str | None,
    resolved: dict[str, str],
    issued_at: datetime,
    signature: str,
) -> bool:
    expected = _sign_bootstrap_payload(
        user_id=user_id,
        role=role,
        cohort_key=cohort_key,
        resolved=resolved,
        issued_at=issued_at,
    )
    return hmac.compare_digest(expected, signature)
