import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from . import config
from .auth import verify_provider_token, verify_stripe_request
from .models import (
    AccountRequestBody,
    AccountRequestResponse,
    BearerAccount,
    BearerCredentials,
    CredentialsWrapper,
    DeepLinkBody,
    DeepLinkResponse,
    HealthResponse,
    ProvisionResourceBody,
    RemoveResourceBody,
    ResourceCompletePayload,
    ResourceResponse,
    RotateCredentialsBody,
    ServicesResponse,
    UpdateServiceBody,
)
from .services import PLAN_IDS, SERVICES, SERVICES_BY_ID
from .storage import (
    Account,
    Resource,
    check_idempotency,
    consume_dashboard_token,
    create_dashboard_token,
    create_resource,
    get_account_by_id,
    get_account_by_token,
    get_resource,
    get_resources_for_account,
    refresh_account_token,
    update_resource,
    upsert_account,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ToasterCloud Provider API",
    description="Agentic Provisioning Protocol 0.1d — cloud hosting on toasters.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Middleware: buffer raw body bytes for HMAC signature verification
# ---------------------------------------------------------------------------

@app.middleware("http")
async def buffer_raw_body(request: Request, call_next):
    body = await request.body()
    request.state.raw_body = body
    return await call_next(request)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_plus(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _access_config(resource: Resource) -> dict:
    region = resource.configuration.get("region", "us-east-1")
    name = resource.configuration.get("name", resource.id)
    return {
        "host": f"{name}-{resource.id}.{region}.toastercloud.dev",
        "ssh_port": 22,
        "ssh_username": "deploy",
        "deploy_key": f"tc_key_{secrets.token_urlsafe(24)}",
        "api_endpoint": f"https://{name}-{resource.id}.{region}.toastercloud.dev",
        "dashboard_url": f"{config.PROVIDER_BASE_URL}/dashboard",
        "region": region,
        "service": resource.service_id,
    }


def _require_account(token: str) -> Account:
    acct = get_account_by_token(token)
    if not acct:
        raise HTTPException(status_code=401, detail="Invalid provider token")
    return acct


def _require_resource(resource_id: str, account: Account) -> Resource:
    r = get_resource(resource_id)
    if not r:
        raise HTTPException(status_code=404, detail="Resource not found")
    if r.account_id != account.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return r


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/provisioning/health")
async def health(
    request: Request,
    _sig: None = Depends(verify_stripe_request),
    api_version: Optional[str] = Header(None, alias="API-Version"),
):
    return HealthResponse(supported_versions=["0.1d"], status="ok")


# ---------------------------------------------------------------------------
# Account requests
# ---------------------------------------------------------------------------

@app.post("/provisioning/account_requests")
async def account_requests(
    body: AccountRequestBody,
    request: Request,
    _sig: None = Depends(verify_stripe_request),
):
    # Reject expired account requests
    try:
        expires_at = datetime.fromisoformat(body.expires_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expires_at format")

    if expires_at < datetime.now(timezone.utc):
        return AccountRequestResponse(
            type="error",
            error={"code": "account_request_expired", "message": "Account request has expired."},
        )

    # Use agentic credentials flow (Flow 1): create/upsert account immediately.
    # Stripe KYC verifies email, so we trust it as the unique account identifier.
    acct = upsert_account(
        email=body.email,
        name=body.name,
        stripe_account=body.orchestrator.stripe.account,
        stripe_organization=body.orchestrator.stripe.organization,
    )

    return AccountRequestResponse(
        type="credentials",
        credentials=CredentialsWrapper(
            type="bearer",
            bearer=BearerCredentials(
                access_token=acct.access_token,
                refresh_token=acct.refresh_token,
                expires_in=3600 * 24 * 30,  # 30 days
                account=BearerAccount(id=acct.id),
            ),
        ),
    )


# ---------------------------------------------------------------------------
# OAuth token endpoint (authorization_code + refresh_token)
# ---------------------------------------------------------------------------

@app.post("/oauth/token")
async def oauth_token(request: Request):
    # application/x-www-form-urlencoded — parse manually
    raw: bytes = getattr(request.state, "raw_body", b"")
    from urllib.parse import parse_qs
    params = {k: v[0] for k, v in parse_qs(raw.decode()).items()}

    grant_type = params.get("grant_type")

    if grant_type == "refresh_token":
        refresh_token = params.get("refresh_token", "")
        acct = refresh_account_token(refresh_token)
        if not acct:
            raise HTTPException(status_code=401, detail="Invalid refresh_token")
        return {
            "token_type": "bearer",
            "access_token": acct.access_token,
            "refresh_token": acct.refresh_token,
            "expires_in": 3600 * 24 * 30,
            "account": {"id": acct.id},
        }

    if grant_type == "authorization_code":
        # We don't use an OAuth redirect flow, but include a minimal handler
        # in case the orchestrator calls it after a requires_auth redirect.
        raise HTTPException(status_code=400, detail="authorization_code flow not supported by this provider")

    raise HTTPException(status_code=400, detail=f"Unsupported grant_type: {grant_type}")


# ---------------------------------------------------------------------------
# Services catalog
# ---------------------------------------------------------------------------

@app.get("/provisioning/services")
async def list_services(
    request: Request,
    cursor: Optional[str] = Query(None),
    _sig: None = Depends(verify_stripe_request),
):
    # All services fit on a single page — no pagination needed
    return ServicesResponse(data=SERVICES)


# ---------------------------------------------------------------------------
# Resources — provision
# ---------------------------------------------------------------------------

@app.post("/provisioning/resources")
async def provision_resource(
    body: ProvisionResourceBody,
    request: Request,
    _sig: None = Depends(verify_stripe_request),
    authorization: Optional[str] = Header(None),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    token = verify_provider_token(authorization)
    acct = _require_account(token)

    # Idempotency: return existing resource if key was already processed
    if idempotency_key:
        existing_id = check_idempotency(idempotency_key)
        if existing_id:
            r = get_resource(existing_id)
            if r:
                return ResourceResponse(
                    status=r.status,  # type: ignore[arg-type]
                    id=r.id,
                    complete=ResourceCompletePayload(
                        access_configuration=r.access_configuration
                    ) if r.status == "complete" else None,
                )

    svc = SERVICES_BY_ID.get(body.service_id)
    if not svc:
        return ResourceResponse(
            status="error",
            id=None,
            error={"code": "unknown_service", "message": f"Unknown service: {body.service_id}"},
        )

    resource_id = f"toast_{secrets.token_hex(8)}"
    r = Resource(
        id=resource_id,
        account_id=acct.id,
        service_id=body.service_id,
        configuration=body.configuration,
        status="complete",
        access_configuration=None,
        orchestrator_resource_id=body.orchestrator_resource_id,
        project_id=body.project_id,
        environment=body.environment or "prod",
    )
    # Plans are subscription records — no compute to connect to
    if body.service_id not in PLAN_IDS:
        r.access_configuration = _access_config(r)
    create_resource(r, idempotency_key=idempotency_key)

    return ResourceResponse(
        status="complete",
        id=r.id,
        complete=ResourceCompletePayload(access_configuration=r.access_configuration),
    )


# ---------------------------------------------------------------------------
# Resources — get
# ---------------------------------------------------------------------------

@app.get("/provisioning/resources/{resource_id}")
async def get_resource_status(
    resource_id: str,
    request: Request,
    _sig: None = Depends(verify_stripe_request),
    authorization: Optional[str] = Header(None),
):
    token = verify_provider_token(authorization)
    acct = _require_account(token)
    r = _require_resource(resource_id, acct)

    if r.status == "removed":
        raise HTTPException(status_code=404, detail="Resource not found")

    return ResourceResponse(
        status=r.status,  # type: ignore[arg-type]
        id=r.id,
        complete=ResourceCompletePayload(
            access_configuration=r.access_configuration
        ) if r.status == "complete" else None,
    )


# ---------------------------------------------------------------------------
# Resources — update service
# ---------------------------------------------------------------------------

@app.post("/provisioning/resources/{resource_id}/update_service")
async def update_service(
    resource_id: str,
    body: UpdateServiceBody,
    request: Request,
    _sig: None = Depends(verify_stripe_request),
    authorization: Optional[str] = Header(None),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    token = verify_provider_token(authorization)
    acct = _require_account(token)
    r = _require_resource(resource_id, acct)

    if r.status != "complete":
        return ResourceResponse(
            status="error",
            id=r.id,
            error={"code": "invalid_state", "message": "Resource is not in a complete state."},
        )

    new_service_id = body.service_id or r.service_id
    svc = SERVICES_BY_ID.get(new_service_id)
    if not svc:
        return ResourceResponse(
            status="error",
            id=r.id,
            error={"code": "unknown_service", "message": f"Unknown service: {new_service_id}"},
        )

    # Only allow transitions listed in allowed_updates
    if body.service_id and body.service_id != r.service_id:
        current_svc = SERVICES_BY_ID.get(r.service_id, {})
        allowed = {u["service"] for u in current_svc.get("allowed_updates", [])}
        if body.service_id not in allowed:
            return ResourceResponse(
                status="error",
                id=r.id,
                error={
                    "code": "destructive_update",
                    "message": f"Cannot update from {r.service_id} to {body.service_id}.",
                },
            )

    new_config = body.configuration or r.configuration
    update_resource(resource_id, service_id=new_service_id, configuration=new_config)
    r = get_resource(resource_id)
    new_access = _access_config(r)
    update_resource(resource_id, access_configuration=new_access)

    return ResourceResponse(
        status="complete",
        id=r.id,
        complete=ResourceCompletePayload(access_configuration=new_access),
    )


# ---------------------------------------------------------------------------
# Resources — remove
# ---------------------------------------------------------------------------

@app.post("/provisioning/resources/{resource_id}/remove")
async def remove_resource(
    resource_id: str,
    body: RemoveResourceBody,
    request: Request,
    _sig: None = Depends(verify_stripe_request),
    authorization: Optional[str] = Header(None),
):
    token = verify_provider_token(authorization)
    acct = _require_account(token)
    r = _require_resource(resource_id, acct)

    update_resource(resource_id, status="removed", access_configuration=None)

    return {"status": "removed", "id": resource_id}


# ---------------------------------------------------------------------------
# Resources — rotate credentials
# ---------------------------------------------------------------------------

@app.post("/provisioning/resources/{resource_id}/rotate_credentials")
async def rotate_credentials(
    resource_id: str,
    body: RotateCredentialsBody,
    request: Request,
    _sig: None = Depends(verify_stripe_request),
    authorization: Optional[str] = Header(None),
):
    token = verify_provider_token(authorization)
    acct = _require_account(token)
    r = _require_resource(resource_id, acct)

    if r.status != "complete":
        return {"status": "error", "id": resource_id, "error": {"code": "invalid_state", "message": "Resource is not active."}}

    new_access = _access_config(r)  # generates a fresh deploy_key
    update_resource(resource_id, access_configuration=new_access)

    return {
        "status": "complete",
        "id": resource_id,
        "complete": {"access_configuration": new_access},
    }


# ---------------------------------------------------------------------------
# Resources — link existing (optional)
# ---------------------------------------------------------------------------

@app.post("/provisioning/resources/link")
async def link_resource(
    body: ProvisionResourceBody,
    request: Request,
    _sig: None = Depends(verify_stripe_request),
    authorization: Optional[str] = Header(None),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Prompt the developer for an existing instance name to link."""
    submitted = body.submitted_information or {}

    if not submitted.get("instance_id"):
        return ResourceResponse(
            status="needs_information",
            needs_information={
                "schema": {
                    "type": "object",
                    "properties": {
                        "instance_id": {
                            "type": "string",
                            "description": "Your existing ToasterCloud instance ID (e.g. toast_abc123)",
                        }
                    },
                    "required": ["instance_id"],
                }
            },
        )

    # In a real provider, you'd look up the existing resource. Here we create a stub.
    token = verify_provider_token(authorization)
    acct = _require_account(token)

    resource_id = submitted["instance_id"]
    r = Resource(
        id=resource_id,
        account_id=acct.id,
        service_id=body.service_id,
        configuration=body.configuration,
        status="complete",
        access_configuration=None,
        orchestrator_resource_id=body.orchestrator_resource_id,
        project_id=body.project_id,
        environment=body.environment or "prod",
    )
    r.access_configuration = _access_config(r)
    create_resource(r, idempotency_key=idempotency_key)

    return ResourceResponse(
        status="complete",
        id=r.id,
        complete=ResourceCompletePayload(access_configuration=r.access_configuration),
    )


# ---------------------------------------------------------------------------
# Deep links
# ---------------------------------------------------------------------------

@app.post("/provisioning/deep_links")
async def deep_links(
    body: DeepLinkBody,
    request: Request,
    _sig: None = Depends(verify_stripe_request),
    authorization: Optional[str] = Header(None),
):
    token = verify_provider_token(authorization)
    acct = _require_account(token)

    token = create_dashboard_token(acct.id, ttl_seconds=300)
    url = f"{config.PROVIDER_BASE_URL}/dashboard?t={token}"

    return DeepLinkResponse(
        purpose=body.purpose,
        url=url,
        expires_at=_now_plus(300),  # 5-minute single-use link
    )


# ---------------------------------------------------------------------------
# Dashboard (deep-link destination — one-time token, 5-minute expiry)
# ---------------------------------------------------------------------------

@app.get("/dashboard", response_class=Response)
async def dashboard(t: Optional[str] = Query(None)):
    if not t:
        return Response(content="<h1>Missing token</h1>", media_type="text/html", status_code=400)

    acct_id = consume_dashboard_token(t)
    if not acct_id:
        return Response(
            content="<h1>Link expired or invalid</h1><p>Deep links are single-use and expire after 5 minutes. Return to your Stripe project and click the dashboard link again.</p>",
            media_type="text/html",
            status_code=401,
        )

    acct = get_account_by_id(acct_id)
    resources = get_resources_for_account(acct_id)

    plans = [r for r in resources if r.service_id in PLAN_IDS]
    instances = [r for r in resources if r.service_id not in PLAN_IDS]

    def _plan_badge(svc_id: str) -> str:
        colors = {"single-slot": "#6c757d", "2-slot": "#0d6efd", "4-slot": "#198754", "8-slot": "#fd7e14", "industrial": "#dc3545"}
        return f'<span style="background:{colors.get(svc_id,"#333")};color:#fff;padding:2px 8px;border-radius:4px;font-size:13px">{svc_id}</span>'

    plan_rows = "".join(
        f"<tr><td>{_plan_badge(r.service_id)}</td><td>{r.environment}</td><td>{r.created_at.strftime('%Y-%m-%d %H:%M UTC')}</td></tr>"
        for r in plans
    ) or "<tr><td colspan='3' style='color:#888'>No active plan</td></tr>"

    def _instance_rows() -> str:
        rows = []
        for r in instances:
            ac = r.access_configuration or {}
            rows.append(f"""
            <tr>
              <td><code>{r.id}</code></td>
              <td>{r.service_id}</td>
              <td>{ac.get('host','—')}</td>
              <td><code>{ac.get('deploy_key','—')[:20]}…</code></td>
              <td>{r.environment}</td>
            </tr>""")
        return "".join(rows) or "<tr><td colspan='5' style='color:#888'>No instances</td></tr>"

    acct_name = (acct.name or acct.email) if acct else acct_id

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ToasterCloud Dashboard</title>
  <style>
    body{{font-family:system-ui,sans-serif;margin:0;background:#fafafa;color:#111}}
    header{{background:#1a1a1a;color:#fff;padding:16px 32px;display:flex;align-items:center;gap:12px}}
    header h1{{margin:0;font-size:20px}}
    .badge{{background:#f59e0b;color:#000;border-radius:4px;padding:2px 8px;font-size:12px;font-weight:700}}
    main{{max-width:960px;margin:32px auto;padding:0 24px}}
    section{{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:24px;margin-bottom:24px}}
    h2{{margin:0 0 16px;font-size:16px;text-transform:uppercase;letter-spacing:.05em;color:#6b7280}}
    table{{width:100%;border-collapse:collapse;font-size:14px}}
    th{{text-align:left;padding:8px 12px;background:#f3f4f6;border-bottom:1px solid #e5e7eb}}
    td{{padding:8px 12px;border-bottom:1px solid #f3f4f6;vertical-align:top}}
    code{{background:#f3f4f6;padding:2px 5px;border-radius:3px;font-size:12px}}
    .acct{{font-size:14px;color:#9ca3af}}
  </style>
</head>
<body>
  <header>
    <span style="font-size:28px">🍞</span>
    <h1>ToasterCloud</h1>
    <span class="badge">Dashboard</span>
    <span class="acct" style="margin-left:auto">{acct_name}</span>
  </header>
  <main>
    <section>
      <h2>Active Plans</h2>
      <table>
        <thead><tr><th>Plan</th><th>Environment</th><th>Created</th></tr></thead>
        <tbody>{plan_rows}</tbody>
      </table>
    </section>
    <section>
      <h2>Toaster Instances</h2>
      <table>
        <thead><tr><th>ID</th><th>Service</th><th>Host</th><th>Deploy Key</th><th>Env</th></tr></thead>
        <tbody>{_instance_rows()}</tbody>
      </table>
    </section>
  </main>
</body>
</html>"""

    return Response(content=html, media_type="text/html")


# ---------------------------------------------------------------------------
# LLM context (plain text, for agents discovering this provider)
# ---------------------------------------------------------------------------

@app.get("/llm-context.txt", response_class=Response)
async def llm_context():
    content = """\
# ToasterCloud Provider

ToasterCloud offers cloud compute hosted on enterprise-grade, rack-mounted toasters.
All tiers are free. Provision an instance and deploy your app over SSH.

## Services

- toaster:nano   — Shared CPU, 128 MB RAM. Best for static sites.
- toaster:micro  — 0.5 vCPU, 256 MB RAM. Good for development.
- toaster:standard — 1 vCPU, 512 MB RAM. Production-ready.
- toaster:pro    — 2 vCPU, 1 GB RAM. High-performance.
- toaster:bagel  — 4 vCPU, 2 GB RAM, NVMe. Maximum crunch.

## Configuration

Required: region (us-east-1 | eu-west-1 | ap-southeast-1), name (lowercase slug)
Optional (standard/pro/bagel): auto_scale (bool)
Optional (bagel only): toast_level (1–7, thermal optimization)

## Access

Each provisioned instance returns:
- host: SSH hostname
- ssh_username: deploy
- deploy_key: API key for CI/CD deployments
- api_endpoint: HTTPS endpoint for your app
- dashboard_url: ToasterCloud dashboard link
"""
    return Response(content=content, media_type="text/plain")
