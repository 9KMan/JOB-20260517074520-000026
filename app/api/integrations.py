from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.models import User
from app.core.permissions import has_permission, Permission

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/{tenant_id}")
async def list_integrations(
    tenant_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if str(user.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Not your tenant")
    if not has_permission(user.role, Permission.MANAGE_INTEGRATIONS):
        raise HTTPException(status_code=403, detail="Cannot view integrations")

    return {"integrations": []}


@router.post("/{tenant_id}")
async def create_integration(
    tenant_id: UUID,
    integration_data: Dict[str, Any],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if str(user.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=403, detail="Not your tenant")
    if not has_permission(user.role, Permission.MANAGE_INTEGRATIONS):
        raise HTTPException(status_code=403, detail="Cannot manage integrations")

    return {"status": "created", "integration": integration_data}