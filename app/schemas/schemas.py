from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class TenantBase(BaseModel):
    name: str


class TenantCreate(TenantBase):
    plan_tier: Optional[str] = "free"


class TenantResponse(TenantBase):
    id: UUID
    plan_tier: str
    stripe_customer_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str
    role: str = "user"


class UserResponse(UserBase):
    id: UUID
    tenant_id: UUID
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AssistantBase(BaseModel):
    name: str
    model_preferences: Optional[List[str]] = None
    system_prompt: Optional[str] = None


class AssistantCreate(AssistantBase):
    pass


class AssistantResponse(AssistantBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    role: str = "user"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model_override: Optional[str] = None


class ChatResponse(BaseModel):
    assistant_id: UUID
    model: str
    message: str
    input_tokens: int
    output_tokens: int
    cost_cents: float
    sources: Optional[List[Dict[str, Any]]] = None


class TrainRequest(BaseModel):
    documents: List[str] = Field(..., description="List of document texts to train on")
    chunk_size: int = 500
    chunk_overlap: int = 50


class TrainResponse(BaseModel):
    assistant_id: UUID
    chunks_created: int
    status: str


class TokenUsageResponse(BaseModel):
    assistant_id: Optional[UUID] = None
    model: str
    input_tokens: int
    output_tokens: int
    cost_cents: float
    created_at: datetime


class UsageSummary(BaseModel):
    tenant_id: UUID
    total_input_tokens: int
    total_output_tokens: int
    total_cost_cents: float
    usage_by_model: Dict[str, Dict[str, int]]


class WebhookEndpointCreate(BaseModel):
    url: str
    events: List[str]


class WebhookEndpointResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    url: str
    events: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class IntegrationCreate(BaseModel):
    type: str
    config: Dict[str, Any]


class IntegrationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    type: str
    config: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True