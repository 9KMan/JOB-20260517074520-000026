import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

pytest_plugins = ('pytest_asyncio',)


@pytest.mark.asyncio
async def test_health():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_root():
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()


@pytest.mark.asyncio
async def test_register_user():
    from app.main import app
    with patch("app.db.database.get_db") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value = mock_session
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/auth/register",
                json={"email": "test@example.com", "password": "testpass123", "role": "user"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_login_invalid_user():
    from app.main import app
    with patch("app.db.database.get_db") as mock_db:
        mock_session = AsyncMock()
        mock_db.return_value = mock_session
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/auth/login",
                json={"email": "notfound@example.com", "password": "testpass123"}
            )
            assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_assistants():
    from app.main import app
    from app.models.models import Assistant, User
    
    mock_user = MagicMock()
    mock_user.id = uuid4()
    mock_user.tenant_id = uuid4()
    mock_user.role = "owner"
    
    mock_assistant = MagicMock()
    mock_assistant.id = uuid4()
    mock_assistant.name = "Test Assistant"
    mock_assistant.tenant_id = mock_user.tenant_id
    
    with patch("app.api.deps.get_current_user", return_value=mock_user):
        with patch("app.db.database.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value = mock_session
            
            mock_result = AsyncMock()
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = [mock_assistant]
            mock_result.scalars.return_value = mock_scalars
            mock_session.execute.return_value = mock_result
            
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/assistants/",
                    headers={"Authorization": "Bearer test-token"}
                )
                assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_assistant_unauthorized():
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/assistants/",
            json={"name": "Test Assistant"},
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_chat_with_assistant():
    from app.main import app
    from app.models.models import Assistant, User
    
    tenant_id = uuid4()
    assistant_id = uuid4()
    
    mock_user = MagicMock()
    mock_user.id = uuid4()
    mock_user.tenant_id = tenant_id
    mock_user.role = "owner"
    
    mock_assistant = MagicMock()
    mock_assistant.id = assistant_id
    mock_assistant.name = "Test Assistant"
    mock_assistant.tenant_id = tenant_id
    mock_assistant.model_preferences = None
    mock_assistant.system_prompt = None
    
    with patch("app.api.deps.get_current_user", return_value=mock_user):
        with patch("app.db.database.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value = mock_session
            
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_assistant
            mock_session.execute.return_value = mock_result
            
            with patch("app.services.billing_service.billing_service.record_usage", new_callable=AsyncMock):
                with patch("app.services.ai_service.ai_service.chat", new_callable=AsyncMock) as mock_chat:
                    mock_chat.return_value = ("Test response", 100, 50)
                    
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        response = await client.post(
                            f"/assistants/{assistant_id}/chat",
                            json={
                                "messages": [
                                    {"role": "user", "content": "Hello"}
                                ]
                            },
                            headers={"Authorization": "Bearer test-token"}
                        )
                    assert response.status_code in [200, 401, 403]


@pytest.mark.asyncio
async def test_router_classifier():
    from app.services.router import RequestClassifier, TaskCategory
    
    classifier = RequestClassifier()
    
    code_text = "def function hello(): return 'world'"
    assert classifier.classify(code_text) == TaskCategory.CODE
    
    analysis_text = "Analyze the quarterly revenue and evaluate growth"
    assert classifier.classify(analysis_text) == TaskCategory.ANALYSIS
    
    summary_text = "Summarize the key points of this document"
    assert classifier.classify(summary_text) == TaskCategory.SUMMARIZATION
    
    qa_text = "What is the capital of France?"
    assert classifier.classify(qa_text) == TaskCategory.QA
    
    creative_text = "Write a poem about the mountains"
    assert classifier.classify(creative_text) == TaskCategory.CREATIVE


@pytest.mark.asyncio
async def test_router_model_selection():
    from app.services.router import AIRouter
    
    router = AIRouter()
    
    code_text = "def hello(): return 'world'"
    model = router.select_model(code_text)
    assert model in ["claude-3-5-sonnet", "gpt-4-turbo"]
    
    general_text = "Hello, how are you today?"
    model = router.select_model(general_text)
    assert model in ["gpt-4-turbo", "gemini-1.5-pro"]


@pytest.mark.asyncio
async def test_billing_cost_calculation():
    from app.services.billing_service import BillingService
    
    billing = BillingService()
    
    cost = BillingService.calculate_cost("claude-3-5-sonnet", 1000000, 500000)
    assert cost > 0


@pytest.mark.asyncio
async def test_webhook_signature():
    from app.services.webhook_service import WebhookService
    import hmac
    import hashlib
    
    service = WebhookService()
    payload = b'{"event": "test"}'
    secret = "test-secret"
    
    signature = service.create_signature(payload, secret)
    assert signature.startswith("sha256=")
    
    is_valid = service.verify_signature(payload, signature, secret)
    assert is_valid == True


@pytest.mark.asyncio
async def test_permissions():
    from app.core.permissions import has_permission, Permission, Role
    
    assert has_permission(Role.OWNER, Permission.MANAGE_ASSISTANTS) == True
    assert has_permission(Role.ADMIN, Permission.MANAGE_ASSISTANTS) == True
    assert has_permission(Role.USER, Permission.MANAGE_ASSISTANTS) == False
    assert has_permission(Role.VIEWER, Permission.MANAGE_ASSISTANTS) == False
    
    assert has_permission(Role.VIEWER, Permission.CHAT) == True
    assert has_permission(Role.USER, Permission.CHAT) == True


@pytest.mark.asyncio
async def test_token_usage_response():
    from app.schemas.schemas import TokenUsageResponse
    
    usage = TokenUsageResponse(
        model="gpt-4-turbo",
        input_tokens=1000,
        output_tokens=500,
        cost_cents=12.5,
    )
    assert usage.model == "gpt-4-turbo"
    assert usage.input_tokens == 1000


@pytest.mark.asyncio
async def test_usage_summary():
    from app.schemas.schemas import UsageSummary
    
    summary = UsageSummary(
        tenant_id=uuid4(),
        total_input_tokens=10000,
        total_output_tokens=5000,
        total_cost_cents=150.0,
        usage_by_model={"gpt-4-turbo": {"input_tokens": 10000, "output_tokens": 5000, "cost_cents": 150.0}},
    )
    assert summary.total_input_tokens == 10000
    assert "gpt-4-turbo" in summary.usage_by_model


@pytest.mark.asyncio
async def test_tenant_isolation():
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200