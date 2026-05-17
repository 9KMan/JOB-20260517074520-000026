from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import Assistant, KnowledgeEmbedding
from app.schemas.schemas import (
    AssistantCreate,
    AssistantResponse,
    ChatRequest,
    ChatResponse,
    TrainRequest,
    TrainResponse,
)
from app.api.deps import get_current_user, check_assistant_access
from app.models.models import User
from app.services.router import router as ai_router
from app.services.vector_service import rag_service
from app.services.billing_service import billing_service
from app.core.permissions import has_permission, Permission

router = APIRouter(prefix="/assistants", tags=["assistants"])


@router.get("/", response_model=List[AssistantResponse])
async def list_assistants(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Assistant).where(Assistant.tenant_id == user.tenant_id)
    )
    assistants = result.scalars().all()
    return assistants


@router.post("/", response_model=AssistantResponse)
async def create_assistant(
    assistant_data: AssistantCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not has_permission(user.role, Permission.MANAGE_ASSISTANTS):
        raise HTTPException(status_code=403, detail="Cannot create assistants")

    assistant = Assistant(
        tenant_id=user.tenant_id,
        name=assistant_data.name,
        model_preferences=assistant_data.model_preferences,
        system_prompt=assistant_data.system_prompt,
    )
    db.add(assistant)
    await db.commit()
    await db.refresh(assistant)
    return assistant


@router.get("/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(
    assistant_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    assistant = await check_assistant_access(str(assistant_id), user, db)
    return assistant


@router.delete("/{assistant_id}")
async def delete_assistant(
    assistant_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not has_permission(user.role, Permission.DELETE_ASSISTANTS):
        raise HTTPException(status_code=403, detail="Cannot delete assistants")

    assistant = await check_assistant_access(str(assistant_id), user, db)

    await db.execute(
        select(KnowledgeEmbedding).where(KnowledgeEmbedding.assistant_id == assistant_id)
    )
    embeddings_result = await db.execute(
        select(KnowledgeEmbedding).where(KnowledgeEmbedding.assistant_id == assistant_id)
    )
    embeddings = embeddings_result.scalars().all()
    for emb in embeddings:
        await db.delete(emb)

    await db.delete(assistant)
    await db.commit()

    return {"status": "deleted"}


@router.post("/{assistant_id}/chat", response_model=ChatResponse)
async def chat_with_assistant(
    assistant_id: UUID,
    chat_request: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not has_permission(user.role, Permission.CHAT):
        raise HTTPException(status_code=403, detail="Cannot chat")

    assistant = await check_assistant_access(str(assistant_id), user, db)

    conversation_text = "\n".join([f"{m.role}: {m.content}" for m in chat_request.messages])
    model = ai_router.select_model(
        conversation_text,
        preferences=assistant.model_preferences or [],
    )

    input_tokens = len(conversation_text) // 4
    output_tokens = len(conversation_text) // 2

    await billing_service.record_usage(
        db=db,
        tenant_id=user.tenant_id,
        assistant_id=assistant.id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    return ChatResponse(
        assistant_id=assistant.id,
        model=model,
        message="AI response would be generated here. Integrate with actual AI provider.",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_cents=billing_service.calculate_cost(model, input_tokens, output_tokens) * 100,
        sources=None,
    )


@router.post("/{assistant_id}/train", response_model=TrainResponse)
async def train_assistant(
    assistant_id: UUID,
    train_request: TrainRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not has_permission(user.role, Permission.TRAIN_ASSISTANT):
        raise HTTPException(status_code=403, detail="Cannot train assistants")

    assistant = await check_assistant_access(str(assistant_id), user, db)

    chunks = rag_service.prepare_documents(
        train_request.documents,
        chunk_size=train_request.chunk_size,
        chunk_overlap=train_request.chunk_overlap,
    )

    embeddings = await rag_service.create_embeddings(chunks)

    for chunk_text, embedding in zip(chunks, embeddings):
        knowledge_emb = KnowledgeEmbedding(
            tenant_id=user.tenant_id,
            assistant_id=assistant.id,
            chunk_text=chunk_text,
            embedding=embedding,
        )
        db.add(knowledge_emb)

    await db.commit()

    return TrainResponse(
        assistant_id=assistant.id,
        chunks_created=len(chunks),
        status="completed",
    )