from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from ...domain.enums import UserRole
from ...schemas.common import PaginatedResponse, PaginationMeta, ApiMeta
from ...schemas.queue import (
    AfterSalesQueueItem,
    DocumentQueueItem,
    ExceptionQueueItem,
    OrderQueueItem,
    PaymentQueueItem,
)
from ...services.queue_service import QueueService
from ..dependencies import CurrentActor, DbSession, require_role

router = APIRouter(
    prefix="/queue",
    tags=["queue"],
)

# Queue endpoints are role-gated per-route. Documents, payments, orders,
# and after-sales queues are reviewer/admin only (reviewer owns those
# adjudication flows). The attendance exceptions queue additionally
# admits proctor, because proctor is the frontline owner of attendance
# anomaly adjudication per the product requirements. Keeping the role
# policy per-route makes the FE↔BE contract explicit.
_REVIEWER_ADMIN = Depends(require_role(UserRole.reviewer, UserRole.admin))
_PROCTOR_REVIEWER_ADMIN = Depends(
    require_role(UserRole.proctor, UserRole.reviewer, UserRole.admin)
)


# 46. GET /queue/documents — pending review
@router.get(
    "/documents",
    response_model=PaginatedResponse[DocumentQueueItem],
    dependencies=[_REVIEWER_ADMIN],
)
async def pending_documents(
    session: DbSession,
    actor: CurrentActor,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[DocumentQueueItem]:
    svc = QueueService(session)
    items, total = await svc.pending_documents(page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
        meta=ApiMeta.now(),
    )


# 47. GET /queue/payments — pending payment confirmation
@router.get(
    "/payments",
    response_model=PaginatedResponse[PaymentQueueItem],
    dependencies=[_REVIEWER_ADMIN],
)
async def pending_payments(
    session: DbSession,
    actor: CurrentActor,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[PaymentQueueItem]:
    svc = QueueService(session)
    items, total = await svc.pending_payments(page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
        meta=ApiMeta.now(),
    )


# 48. GET /queue/orders — pending fulfillment
@router.get(
    "/orders",
    response_model=PaginatedResponse[OrderQueueItem],
    dependencies=[_REVIEWER_ADMIN],
)
async def pending_orders(
    session: DbSession,
    actor: CurrentActor,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[OrderQueueItem]:
    svc = QueueService(session)
    items, total = await svc.pending_orders(page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
        meta=ApiMeta.now(),
    )


# 49. GET /queue/exceptions — pending exception review (proctor, reviewer, admin)
@router.get(
    "/exceptions",
    response_model=PaginatedResponse[ExceptionQueueItem],
    dependencies=[_PROCTOR_REVIEWER_ADMIN],
)
async def pending_exceptions(
    session: DbSession,
    actor: CurrentActor,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[ExceptionQueueItem]:
    svc = QueueService(session)
    items, total = await svc.pending_exceptions(page=page, page_size=page_size, status=status)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
        meta=ApiMeta.now(),
    )


# 50. GET /queue/after-sales — pending after-sales resolve
@router.get(
    "/after-sales",
    response_model=PaginatedResponse[AfterSalesQueueItem],
    dependencies=[_REVIEWER_ADMIN],
)
async def pending_after_sales(
    session: DbSession,
    actor: CurrentActor,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[AfterSalesQueueItem]:
    svc = QueueService(session)
    items, total = await svc.pending_after_sales(page=page, page_size=page_size)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
        meta=ApiMeta.now(),
    )
