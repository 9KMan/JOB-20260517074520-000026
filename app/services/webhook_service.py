import hmac
import hashlib
import httpx
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential


class WebhookService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    def verify_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        expected_sig = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected_sig}", signature)

    def create_signature(self, payload: bytes, secret: str) -> str:
        return f"sha256={hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()}"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def send_webhook(
        self,
        url: str,
        event: str,
        data: Dict[str, Any],
        secret: Optional[str] = None
    ) -> bool:
        payload = str(data).encode()
        headers = {"Content-Type": "application/json"}

        if secret:
            headers["X-Webhook-Signature"] = self.create_signature(payload, secret)

        response = await self.client.post(url, content=payload, headers=headers)
        return response.status_code in [200, 201, 202, 204]

    async def dispatch_event(
        self,
        tenant_id: str,
        webhooks: List[Dict[str, Any]],
        event: str,
        data: Dict[str, Any]
    ):
        for webhook in webhooks:
            if event in webhook.get("events", []):
                await self.send_webhook(
                    webhook["url"],
                    event,
                    {**data, "tenant_id": tenant_id},
                    webhook.get("secret_hash")
                )

    async def close(self):
        await self.client.aclose()


webhook_service = WebhookService()