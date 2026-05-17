from typing import Optional
from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import User, Assistant
from app.core.security import decode_token
from app.core.permissions import has_permission, Permission, get_assistant_permissions

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def require_permission(
    permission: Permission,
    user: User = Depends(get_current_user)
):
    if not has_permission(user.role, permission):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user


async def require_tenant_header(
    x_tenant_id: Optional[str] = Header(None),
    user: User = Depends(get_current_user)
) -> str:
    if x_tenant_id and x_tenant_id != str(user.tenant_id):
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    return str(user.tenant_id)


async def check_assistant_access(
    assistant_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Assistant:
    result = await db.execute(
        select(Assistant).where(Assistant.id == assistant_id)
    )
    assistant = result.scalar_one_or_none()

    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    if str(assistant.tenant_id) != str(user.tenant_id):
        raise HTTPException(status_code=403, detail="Assistant not in your tenant")

    return assistant