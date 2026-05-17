from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import stripe
from app.models.models import TokenUsage, Tenant
from app.services.router import MODEL_COSTS
from app.core.config import get_settings

settings = get_settings()
stripe.api_key = settings.stripe_api_key


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

    async def create_stripe_invoice(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        usage_amount_cents: float
    ) -> Optional[str]:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        
        if not tenant or not tenant.stripe_customer_id:
            return None
        
        try:
            invoice = stripe.Invoice.create(
                customer=tenant.stripe_customer_id,
                auto_advance=True,
                collection_method='send_invoice',
                days_until_due=30,
            )
            
            stripe.InvoiceItem.create(
                customer=tenant.stripe_customer_id,
                amount=int(usage_amount_cents),
                currency='usd',
                description='AI Assistant Usage',
                invoice=invoice.id,
            )
            
            return invoice.id
        except Exception:
            return None

    async def charge_stored_payment(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        amount_cents: int
    ) -> bool:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        
        if not tenant or not tenant.stripe_customer_id:
            return False
        
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='usd',
                customer=tenant.stripe_customer_id,
                automatic_payment_methods={'enabled': True},
            )
            return payment_intent.status == 'requires_payment_method'
        except Exception:
            return False


billing_service = BillingService()