from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import TokenUsage
from app.services.router import MODEL_COSTS


class BillingService:
    @staticmethod
    def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        costs = MODEL_COSTS.get(model, {"input": 0, "output": 0})
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]
        return round(input_cost + output_cost, 4)

    async def record_usage(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        assistant_id: Optional[UUID],
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> TokenUsage:
        cost_cents = self.calculate_cost(model, input_tokens, output_tokens) * 100

        usage = TokenUsage(
            tenant_id=tenant_id,
            assistant_id=assistant_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_cents=cost_cents,
        )
        db.add(usage)
        await db.commit()
        await db.refresh(usage)
        return usage

    async def get_usage_summary(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        query = select(
            TokenUsage.model,
            func.sum(TokenUsage.input_tokens).label("total_input"),
            func.sum(TokenUsage.output_tokens).label("total_output"),
            func.sum(TokenUsage.cost_cents).label("total_cost"),
        ).where(TokenUsage.tenant_id == tenant_id)

        if start_date:
            query = query.where(TokenUsage.created_at >= start_date)
        if end_date:
            query = query.where(TokenUsage.created_at <= end_date)

        query = query.group_by(TokenUsage.model)
        result = await db.execute(query)
        rows = result.all()

        usage_by_model = {}
        total_input = 0
        total_output = 0
        total_cost = 0

        for row in rows:
            usage_by_model[row.model] = {
                "input_tokens": row.total_input or 0,
                "output_tokens": row.total_output or 0,
                "cost_cents": float(row.total_cost or 0),
            }
            total_input += row.total_input or 0
            total_output += row.total_output or 0
            total_cost += float(row.total_cost or 0)

        return {
            "tenant_id": str(tenant_id),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost_cents": round(total_cost, 2),
            "usage_by_model": usage_by_model,
        }

    async def check_spend_threshold(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        monthly_limit_cents: float = 10000
    ) -> bool:
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        query = select(func.sum(TokenUsage.cost_cents)).where(
            TokenUsage.tenant_id == tenant_id,
            TokenUsage.created_at >= start_of_month
        )
        result = await db.execute(query)
        total_spent = float(result.scalar() or 0)

        return total_spent >= monthly_limit_cents


billing_service = BillingService()