import os
import ssl

# Disable SSL verification in dev when behind a corporate proxy/firewall
if os.environ.get("DISABLE_SSL_VERIFY", "").strip().lower() in ("1", "true", "yes"):
    # 1. Global default SSL context — no verification
    ssl._create_default_https_context = ssl._create_unverified_context

    # 2. Patch requests.Session so every HTTP call skips verification
    import requests
    import requests.adapters

    _orig_session_init = requests.Session.__init__

    def _patched_session_init(self, *args, **kwargs):
        _orig_session_init(self, *args, **kwargs)
        self.verify = False

    requests.Session.__init__ = _patched_session_init

    # 3. Patch httpx clients
    import httpx

    _orig_client_init = httpx.Client.__init__

    def _patched_client_init(self, *args, **kwargs):
        kwargs.setdefault("verify", False)
        _orig_client_init(self, *args, **kwargs)

    httpx.Client.__init__ = _patched_client_init

    _orig_async_init = httpx.AsyncClient.__init__

    def _patched_async_init(self, *args, **kwargs):
        kwargs.setdefault("verify", False)
        _orig_async_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = _patched_async_init

    # 4. Suppress warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # 5. Set env vars that some libraries check
    os.environ["CURL_CA_BUNDLE"] = ""
    os.environ["REQUESTS_CA_BUNDLE"] = ""
    os.environ["PYTHONHTTPSVERIFY"] = "0"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agents, assets, balance_sheet, chat, health, liabilities, statements
from app.config import settings

app = FastAPI(
    title="Financial Copilot AI Orchestrator",
    description=(
        "LangGraph multi-agent orchestration for Financial Copilot. "
        "Balance-sheet intelligence: assets, liabilities, net worth, "
        "bond optimisation, and debt analysis. "
        "Reads financial data from financial-copilot-api only."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(agents.router)
app.include_router(statements.router)
app.include_router(assets.router)
app.include_router(liabilities.router)
app.include_router(balance_sheet.router)
