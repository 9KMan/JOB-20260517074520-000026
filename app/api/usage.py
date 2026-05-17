from typing import List
from datetime import datetime, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.api.deps import get_current_user, require_permission
from app.models.models import User, TokenUsage
from app.schemas.schemas import TokenUsageResponse, UsageSummary
from app.services.billing_service import billing_service
from app.core.permissions import Permission

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/{tenant_id}", response_model=UsageSummary)
async def get_usage(
    tenant_id: UUID,
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if str(user.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Not your tenant")
    if not has_permission(user.role, Permission.VIEW_USAGE):
        raise HTTPException(status_code=403, detail="Cannot view usage")

    summary = await billing_service.get_usage_summary(db, tenant_id, start_date, end_date)
    return summary