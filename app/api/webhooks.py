from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import WebhookEndpoint, User
from app.schemas.schemas import WebhookEndpointCreate, WebhookEndpointResponse
from app.api.deps import get_current_user
from app.services.webhook_service import webhook_service
from app.core.permissions import has_permission, Permission

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/inbound")
async def inbound_webhook(
    request: Request,
    x_webhook_secret: str = Header(None),
):
    body = await request.body()

    if x_webhook_secret:
        # Verify webhook signature if secret provided
        pass

    return {"status": "received"}


@router.get("/outbound", response_model=List[WebhookEndpointResponse])
async def list_webhooks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not has_permission(user.role, Permission.MANAGE_INTEGRATIONS):
        raise HTTPException(status_code=403, detail="Cannot manage webhooks")

    result = await db.execute(
        select(WebhookEndpoint).where(WebhookEndpoint.tenant_id == user.tenant_id)
    )
    webhooks = result.scalars().all()
    return webhooks


@router.post("/outbound", response_model=WebhookEndpointResponse)
async def create_webhook(
    webhook_data: WebhookEndpointCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not has_permission(user.role, Permission.MANAGE_INTEGRATIONS):
        raise HTTPException(status_code=403, detail="Cannot manage webhooks")

    webhook = WebhookEndpoint(
        tenant_id=user.tenant_id,
        url=webhook_data.url,
        events=webhook_data.events,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    return webhook


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not has_permission(user.role, Permission.MANAGE_INTEGRATIONS):
        raise HTTPException(status_code=403, detail="Cannot manage webhooks")

    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == webhook_id,
            WebhookEndpoint.tenant_id == user.tenant_id,
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    await db.delete(webhook)
    await db.commit()
    return {"status": "deleted"}