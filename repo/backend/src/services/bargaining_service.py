from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..domain.bargaining import (
    BargainingWindowClosedError,
    CounterAlreadyMadeError,
    OffersExhaustedError,
    can_counter,
    can_submit_offer,
    window_expires_at,
)
from ..domain.enums import AuditEventType, BargainingOfferOutcome, BargainingStatus, OrderStatus, PricingMode, UserRole
from ..persistence.models.order import BargainingThread, BargainingOffer
from ..persistence.repositories.candidate_repo import CandidateRepository
from ..persistence.repositories.order_repo import OrderRepository
from ..schemas.bargaining import BargainingThreadRead, OfferRead
from ..security import audit as audit_mod
from ..security.errors import BusinessRuleError, ResourceNotFoundError
from ..security.rbac import Actor, assert_roles_or_owner
from .order_service import OrderService


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


# Thread statuses that are terminal/resolved and must not accept further mutations
_TERMINAL_THREAD_STATES = {
    BargainingStatus.accepted.value,
    BargainingStatus.counter_accepted.value,
    BargainingStatus.expired.value,
    BargainingStatus.rejected.value,
}


class BargainingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = OrderRepository(session)
        self._order_svc = OrderService(session)

    async def get_or_create_thread(
        self, order_id: uuid.UUID, now: datetime
    ) -> BargainingThread:
        thread = await self._repo.get_thread(order_id)
        if thread is None:
            expires = window_expires_at(now)
            thread = await self._repo.create_thread(
                order_id=order_id,
                window_starts_at=now,
                window_expires_at=expires,
            )
        return thread

    async def submit_offer(
        self,
        order_id: uuid.UUID,
        candidate_actor: Actor,
        amount: Decimal,
        now: datetime | None = None,
    ) -> OfferRead:
        now = now or _now()
        settings = get_settings()

        order = await self._repo.get_order(order_id)
        if order is None:
            raise ResourceNotFoundError("Order not found.")
        profile = await CandidateRepository(self._session).get_by_id(order.candidate_id)
        owner_user_id = str(profile.user_id) if profile else ""
        assert_roles_or_owner(candidate_actor, [], owner_user_id)
        if order.status != OrderStatus.pending_payment.value:
            raise BusinessRuleError("Offers can only be submitted on pending_payment orders.")

        # Enforce that the order is in bargaining pricing mode and the item permits it.
        # Without these guards a fixed-price order could be pulled into the bargaining flow.
        if order.pricing_mode != PricingMode.bargaining.value:
            raise BusinessRuleError(
                "Bargaining offers are not allowed on fixed-price orders."
            )
        item = await self._repo.get_service_item(order.item_id)
        if item is None or not item.bargaining_enabled:
            raise BusinessRuleError(
                "Bargaining is not enabled for this service item."
            )

        thread = await self.get_or_create_thread(order_id, now)
        # Guard against mutating a resolved/expired thread.
        if thread.status in _TERMINAL_THREAD_STATES:
            raise BusinessRuleError(
                "Bargaining thread is already resolved; no further offers allowed."
            )
        existing_offer_count = await self._repo.count_offers(thread.id)

        try:
            can_submit_offer(
                current_offer_count=existing_offer_count,
                window_start=thread.window_starts_at,
                now=now,
                max_offers=settings.max_bargaining_offers,
                window_hours=settings.bargaining_window_hours,
            )
        except OffersExhaustedError as exc:
            raise BusinessRuleError(str(exc)) from exc
        except BargainingWindowClosedError as exc:
            raise BusinessRuleError(str(exc)) from exc

        offer = await self._repo.add_offer(
            thread=thread,
            offer_number=existing_offer_count + 1,
            amount=amount,
            submitted_by=uuid.UUID(candidate_actor.user_id),
        )

        await audit_mod.record_audit(
            self._session,
            event_type=AuditEventType.bargaining_offer_submitted,
            actor_id=uuid.UUID(candidate_actor.user_id),
            actor_role=candidate_actor.role.value,
            resource_type="bargaining_thread",
            resource_id=str(thread.id),
            outcome="offer_submitted",
            detail={"offer_number": offer.offer_number, "amount": str(amount)},
        )

        return OfferRead(
            id=offer.id,
            thread_id=offer.thread_id,
            offer_number=offer.offer_number,
            amount=offer.amount,
            submitted_by=offer.submitted_by,
            submitted_at=offer.submitted_at,
            outcome=None,
        )

    async def get_thread(self, order_id: uuid.UUID, actor: Actor) -> BargainingThreadRead:
        thread = await self._repo.get_thread(order_id)
        if thread is None:
            raise ResourceNotFoundError("Bargaining thread not found.")
        order = await self._repo.get_order(order_id)
        if order:
            profile = await CandidateRepository(self._session).get_by_id(order.candidate_id)
            owner_user_id = str(profile.user_id) if profile else ""
            assert_roles_or_owner(actor, [UserRole.reviewer, UserRole.admin], owner_user_id)
        return _thread_to_read(thread)

    async def accept_offer(
        self,
        order_id: uuid.UUID,
        reviewer_actor: Actor,
        offer_id: uuid.UUID,
        now: datetime | None = None,
    ) -> BargainingThreadRead:
        now = now or _now()
        thread = await self._repo.get_thread(order_id)
        if thread is None:
            raise ResourceNotFoundError("Bargaining thread not found.")

        order = await self._repo.get_order(order_id)
        if order is None:
            raise ResourceNotFoundError("Order not found.")
        if order.pricing_mode != PricingMode.bargaining.value:
            raise BusinessRuleError(
                "Bargaining accept is not allowed on fixed-price orders."
            )
        if thread.status in _TERMINAL_THREAD_STATES:
            raise BusinessRuleError(
                "Bargaining thread is already resolved; cannot accept further offers."
            )

        offer = await self._repo.get_offer(offer_id)
        if offer is None or offer.thread_id != thread.id:
            raise ResourceNotFoundError("Offer not found in this thread.")
        if offer.outcome is not None:
            raise BusinessRuleError(
                "Offer has already been resolved and cannot be accepted."
            )

        # Mark accepted offer and expire others
        for o in (thread.offers or []):
            if o.id == offer_id:
                await self._repo.update_offer_outcome(o, BargainingOfferOutcome.accepted.value)
            elif o.outcome is None:
                await self._repo.update_offer_outcome(o, BargainingOfferOutcome.expired.value)

        await self._repo.update_thread(
            thread,
            status=BargainingStatus.accepted.value,
            resolved_offer_id=offer_id,
            resolved_at=now,
        )

        # Set agreed price; order remains in pending_payment awaiting payment proof
        order.agreed_price = offer.amount
        await self._session.flush()

        await audit_mod.record_audit(
            self._session,
            event_type=AuditEventType.bargaining_resolved,
            actor_id=uuid.UUID(reviewer_actor.user_id),
            actor_role=reviewer_actor.role.value,
            resource_type="bargaining_thread",
            resource_id=str(thread.id),
            outcome="accepted",
            detail={"offer_id": str(offer_id), "amount": str(offer.amount)},
        )

        thread = await self._repo.get_thread(order_id)
        return _thread_to_read(thread)

    async def counter_offer(
        self,
        order_id: uuid.UUID,
        reviewer_actor: Actor,
        amount: Decimal,
        now: datetime | None = None,
    ) -> BargainingThreadRead:
        now = now or _now()
        thread = await self._repo.get_thread(order_id)
        if thread is None:
            raise ResourceNotFoundError("Bargaining thread not found.")

        order = await self._repo.get_order(order_id)
        if order is None:
            raise ResourceNotFoundError("Order not found.")
        if order.pricing_mode != PricingMode.bargaining.value:
            raise BusinessRuleError(
                "Counter-offers are not allowed on fixed-price orders."
            )
        if thread.status in _TERMINAL_THREAD_STATES:
            raise BusinessRuleError(
                "Bargaining thread is already resolved; cannot issue a counter-offer."
            )

        try:
            can_counter(thread.counter_count)
        except CounterAlreadyMadeError as exc:
            raise BusinessRuleError(str(exc)) from exc

        await self._repo.update_thread(
            thread,
            status=BargainingStatus.countered.value,
            counter_amount=amount,
            counter_count=thread.counter_count + 1,
            counter_by=uuid.UUID(reviewer_actor.user_id),
            counter_at=now,
        )

        await audit_mod.record_audit(
            self._session,
            event_type=AuditEventType.bargaining_offer_submitted,
            actor_id=uuid.UUID(reviewer_actor.user_id),
            actor_role=reviewer_actor.role.value,
            resource_type="bargaining_thread",
            resource_id=str(thread.id),
            outcome="counter_offered",
            detail={"counter_amount": str(amount)},
        )

        thread = await self._repo.get_thread(order_id)
        return _thread_to_read(thread)

    async def accept_counter(
        self,
        order_id: uuid.UUID,
        candidate_actor: Actor,
        now: datetime | None = None,
    ) -> BargainingThreadRead:
        now = now or _now()
        thread = await self._repo.get_thread(order_id)
        if thread is None:
            raise ResourceNotFoundError("Bargaining thread not found.")
        order = await self._repo.get_order(order_id)
        if order is None:
            raise ResourceNotFoundError("Order not found.")
        profile = await CandidateRepository(self._session).get_by_id(order.candidate_id)
        owner_user_id = str(profile.user_id) if profile else ""
        assert_roles_or_owner(candidate_actor, [], owner_user_id)
        if thread.status != BargainingStatus.countered.value:
            raise BusinessRuleError("No pending counter-offer to accept.")

        await self._repo.update_thread(
            thread,
            status=BargainingStatus.counter_accepted.value,
            resolved_at=now,
        )

        # Set agreed price; order remains in pending_payment awaiting payment proof
        order = await self._repo.get_order(order_id)
        if order and thread.counter_amount is not None:
            order.agreed_price = thread.counter_amount
            await self._session.flush()

        await audit_mod.record_audit(
            self._session,
            event_type=AuditEventType.bargaining_resolved,
            actor_id=uuid.UUID(candidate_actor.user_id),
            actor_role=candidate_actor.role.value,
            resource_type="bargaining_thread",
            resource_id=str(thread.id),
            outcome="counter_accepted",
        )

        thread = await self._repo.get_thread(order_id)
        return _thread_to_read(thread)

    async def expire_thread(
        self, thread: BargainingThread, now: datetime | None = None
    ) -> None:
        now = now or _now()
        for offer in (thread.offers or []):
            if offer.outcome is None:
                await self._repo.update_offer_outcome(offer, BargainingOfferOutcome.expired.value)

        await self._repo.update_thread(
            thread,
            status=BargainingStatus.expired.value,
            resolved_at=now,
        )

        order = await self._repo.get_order(thread.order_id)
        if order is None:
            return

        # If fixed_price is available, set it; otherwise cancel the order
        from ..domain.enums import UserRole as _UserRole
        from ..security.rbac import Actor as _Actor
        system_actor = _Actor(
            user_id="00000000-0000-0000-0000-000000000000",
            role=_UserRole.admin,
            username="system",
        )

        item = await self._repo.get_service_item(order.item_id)
        if item and item.fixed_price is not None:
            order.agreed_price = item.fixed_price
            await self._session.flush()
        else:
            await self._order_svc.cancel(
                thread.order_id, system_actor, "bargaining_expired"
            )

        await audit_mod.record_audit(
            self._session,
            event_type=AuditEventType.bargaining_resolved,
            actor_id=None,
            actor_role="system",
            resource_type="bargaining_thread",
            resource_id=str(thread.id),
            outcome="expired",
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _thread_to_read(thread: BargainingThread) -> BargainingThreadRead:
    offers = []
    for o in sorted(thread.offers or [], key=lambda x: x.offer_number):
        offers.append(
            OfferRead(
                id=o.id,
                thread_id=o.thread_id,
                offer_number=o.offer_number,
                amount=o.amount,
                submitted_by=o.submitted_by,
                submitted_at=o.submitted_at,
                outcome=BargainingOfferOutcome(o.outcome) if o.outcome else None,
            )
        )
    return BargainingThreadRead(
        id=thread.id,
        order_id=thread.order_id,
        status=BargainingStatus(thread.status),
        window_starts_at=thread.window_starts_at,
        window_expires_at=thread.window_expires_at,
        counter_count=thread.counter_count,
        counter_amount=thread.counter_amount,
        counter_at=thread.counter_at,
        resolved_at=thread.resolved_at,
        offers=offers,
    )
