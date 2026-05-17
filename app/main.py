from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, assistants, usage, webhooks, integrations

app = FastAPI(title="AI Orchestration Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(assistants.router)
app.include_router(usage.router)
app.include_router(webhooks.router)
app.include_router(integrations.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/")
async def root():
    return {"message": "AI Orchestration Platform API"}