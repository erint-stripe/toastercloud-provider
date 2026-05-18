"""In-memory storage. State does not persist across restarts."""

import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


_lock = threading.Lock()


def _token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


@dataclass
class Account:
    id: str
    email: str
    name: Optional[str]
    stripe_account: str
    stripe_organization: str
    access_token: str
    refresh_token: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Resource:
    id: str
    account_id: str
    service_id: str
    configuration: dict
    status: str  # pending | complete | pending_removal | removed | error
    access_configuration: Optional[dict]
    orchestrator_resource_id: str
    project_id: Optional[str]
    environment: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_accounts_by_token: dict[str, Account] = {}
_accounts_by_email: dict[str, Account] = {}
_resources: dict[str, Resource] = {}
_idempotency: dict[str, str] = {}  # key -> resource_id
_dashboard_tokens: dict[str, tuple[str, datetime]] = {}  # token -> (acct_id, expires_at)


# --- Accounts ---

def get_account_by_token(token: str) -> Optional[Account]:
    with _lock:
        return _accounts_by_token.get(token)


def upsert_account(
    email: str,
    name: Optional[str],
    stripe_account: str,
    stripe_organization: str,
) -> Account:
    with _lock:
        existing = _accounts_by_email.get(email)
        if existing:
            # Issue fresh tokens on each account request (re-login)
            old_token = existing.access_token
            existing.access_token = _token("pat")
            existing.refresh_token = _token("prt")
            _accounts_by_token.pop(old_token, None)
            _accounts_by_token[existing.access_token] = existing
            return existing

        acct = Account(
            id=f"acct_{secrets.token_hex(8)}",
            email=email,
            name=name,
            stripe_account=stripe_account,
            stripe_organization=stripe_organization,
            access_token=_token("pat"),
            refresh_token=_token("prt"),
        )
        _accounts_by_email[email] = acct
        _accounts_by_token[acct.access_token] = acct
        return acct


def refresh_account_token(refresh_token: str) -> Optional[Account]:
    with _lock:
        for acct in _accounts_by_email.values():
            if acct.refresh_token == refresh_token:
                old_token = acct.access_token
                acct.access_token = _token("pat")
                acct.refresh_token = _token("prt")
                _accounts_by_token.pop(old_token, None)
                _accounts_by_token[acct.access_token] = acct
                return acct
        return None


# --- Resources ---

def get_resource(resource_id: str) -> Optional[Resource]:
    with _lock:
        return _resources.get(resource_id)


def check_idempotency(key: str) -> Optional[str]:
    """Return existing resource_id if this key was already processed."""
    with _lock:
        return _idempotency.get(key)


def create_resource(resource: Resource, idempotency_key: Optional[str] = None) -> None:
    with _lock:
        _resources[resource.id] = resource
        if idempotency_key:
            _idempotency[idempotency_key] = resource.id


def update_resource(resource_id: str, **kwargs: Any) -> Optional[Resource]:
    with _lock:
        r = _resources.get(resource_id)
        if r:
            for k, v in kwargs.items():
                setattr(r, k, v)
        return r


# --- Dashboard tokens ---

def create_dashboard_token(acct_id: str, ttl_seconds: int = 300) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    with _lock:
        _dashboard_tokens[token] = (acct_id, expires_at)
    return token


def consume_dashboard_token(token: str) -> Optional[str]:
    """Return acct_id if token is valid and unexpired, then delete it."""
    with _lock:
        entry = _dashboard_tokens.pop(token, None)
    if not entry:
        return None
    acct_id, expires_at = entry
    if datetime.now(timezone.utc) > expires_at:
        return None
    return acct_id


def get_resources_for_account(acct_id: str) -> list[Resource]:
    with _lock:
        return [r for r in _resources.values() if r.account_id == acct_id and r.status != "removed"]


def get_account_by_id(acct_id: str) -> Optional[Account]:
    with _lock:
        for acct in _accounts_by_email.values():
            if acct.id == acct_id:
                return acct
        return None
