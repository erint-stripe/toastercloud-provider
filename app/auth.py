import base64
import hashlib
import hmac as _hmac
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import Header, HTTPException, Request

from . import config

logger = logging.getLogger(__name__)

# Simple TTL cache for Stripe's Ed25519 public keys
_public_keys: dict = {}  # kid -> Ed25519PublicKey
_public_keys_fetched_at: float = 0.0
_PUBLIC_KEYS_TTL = 300  # seconds


def _pad_base64url(s: str) -> str:
    return s + "=" * (-len(s) % 4)


async def _fetch_public_keys() -> None:
    global _public_keys, _public_keys_fetched_at
    if not config.ORCHESTRATOR_TOKEN:
        return
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{config.ORCHESTRATOR_BASE_URL}/v2/provisioning/public_keys",
                headers={"Authorization": f"Bearer {config.ORCHESTRATOR_TOKEN}"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.exception("Failed to fetch Stripe public keys")
        return

    new_keys: dict = {}
    now = datetime.now(timezone.utc)
    for key in data.get("public_keys", []):
        expires_at = datetime.fromisoformat(key["expires_at"].replace("Z", "+00:00"))
        if expires_at > now and key.get("crv") == "Ed25519":
            raw = base64.urlsafe_b64decode(_pad_base64url(key["x"]))
            new_keys[key["kid"]] = Ed25519PublicKey.from_public_bytes(raw)

    _public_keys = new_keys
    _public_keys_fetched_at = time.time()


async def _get_public_key(kid: str) -> Optional[Ed25519PublicKey]:
    if time.time() - _public_keys_fetched_at > _PUBLIC_KEYS_TTL:
        await _fetch_public_keys()
    return _public_keys.get(kid)


def _verify_hmac(signature_header: str, raw_body: bytes, tolerance: int = 300) -> bool:
    if not config.HMAC_SECRET:
        return False
    try:
        parts = dict(
            item.split("=", 1)
            for item in signature_header.split(",")
            if "=" in item
        )
    except Exception:
        return False

    timestamp = parts.get("t")
    v1 = parts.get("v1")
    if not timestamp or not v1:
        return False

    try:
        ts = int(timestamp)
    except ValueError:
        return False

    if abs(time.time() - ts) > tolerance:
        logger.warning("Stripe-Signature timestamp outside tolerance: %d", ts)
        return False

    message = f"{timestamp}.".encode() + raw_body
    expected = _hmac.new(
        config.HMAC_SECRET.encode("utf-8"), message, hashlib.sha256
    ).hexdigest()
    return _hmac.compare_digest(expected, v1)


async def _verify_jwt_v2(jwt_header: str, raw_body: bytes, method: str, url: str) -> bool:
    try:
        unverified = jwt.get_unverified_header(jwt_header)
        kid = unverified.get("kid")
        if not kid:
            return False

        public_key = await _get_public_key(kid)
        if not public_key:
            logger.warning("Unknown kid in Stripe-Signature-V2: %s", kid)
            return False

        claims = jwt.decode(
            jwt_header,
            public_key,
            algorithms=["EdDSA"],
            options={"verify_exp": True},
        )

        if claims.get("version") != 1:
            return False
        if claims.get("htm") != method.upper():
            return False

        digest = base64.urlsafe_b64encode(hashlib.sha256(raw_body).digest()).rstrip(b"=").decode()
        if claims.get("digest") != digest:
            return False

        return True
    except Exception:
        logger.exception("JWT V2 verification failed")
        return False


async def verify_stripe_request(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    stripe_signature_v2: Optional[str] = Header(None, alias="Stripe-Signature-V2"),
) -> None:
    if config.SKIP_SIGNATURE_VERIFICATION:
        return

    raw_body: bytes = getattr(request.state, "raw_body", b"")

    hmac_ok = stripe_signature and _verify_hmac(stripe_signature, raw_body)
    if not hmac_ok:
        raise HTTPException(status_code=401, detail="Invalid or missing Stripe-Signature")

    # JWT V2 is optional during rollout — log failures but don't reject
    if stripe_signature_v2:
        url = str(request.url)
        method = request.method
        jwt_ok = await _verify_jwt_v2(stripe_signature_v2, raw_body, method, url)
        if not jwt_ok:
            logger.warning("Stripe-Signature-V2 verification failed (non-fatal during rollout)")


def verify_provider_token(
    authorization: Optional[str] = Header(None),
) -> str:
    """Return the bearer token from the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return authorization.removeprefix("Bearer ")
