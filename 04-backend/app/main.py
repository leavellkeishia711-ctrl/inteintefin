from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import auth, imports, consumables, transactions, reports, ad_accounts, campaign_runs, campaign_run_stats, payroll, partners, settings as settings_router, chat, webhooks, alerts, invites

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://staging.financeintel.co",
        "https://app.financeintel.co",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(invites.router, prefix=f"{settings.API_V1_STR}/auth", tags=["invites"])
app.include_router(imports.router, prefix=f"{settings.API_V1_STR}/imports", tags=["imports"])
app.include_router(consumables.router, prefix=f"{settings.API_V1_STR}")
app.include_router(transactions.router, prefix=f"{settings.API_V1_STR}/transactions", tags=["transactions"])
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}")
app.include_router(ad_accounts.router, prefix=f"{settings.API_V1_STR}")
app.include_router(campaign_runs.router, prefix=f"{settings.API_V1_STR}")
app.include_router(campaign_run_stats.router, prefix=f"{settings.API_V1_STR}")
app.include_router(payroll.router, prefix=f"{settings.API_V1_STR}/payroll", tags=["payroll"])
app.include_router(partners.router, prefix=f"{settings.API_V1_STR}/partners", tags=["partners"])
app.include_router(settings_router.router, prefix=f"{settings.API_V1_STR}/settings", tags=["settings"])
app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["chat"])
app.include_router(webhooks.router, prefix=f"{settings.API_V1_STR}/webhooks", tags=["webhooks"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_STR}/alerts", tags=["alerts"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
