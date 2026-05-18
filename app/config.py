import os

API_VERSION = "0.1d"
ORCHESTRATOR_BASE_URL = "https://api.stripe.com"

# Populated when the provider onboards with Stripe (out-of-band)
HMAC_SECRET: str = os.environ.get("STRIPE_HMAC_SECRET", "")
ORCHESTRATOR_TOKEN: str = os.environ.get("STRIPE_ORCHESTRATOR_TOKEN", "")

PROVIDER_BASE_URL: str = os.environ.get(
    "PROVIDER_BASE_URL", "http://localhost:8000"
)

# Set to "1" in development to skip signature verification
SKIP_SIGNATURE_VERIFICATION: bool = (
    os.environ.get("SKIP_SIGNATURE_VERIFICATION", "0") == "1"
)
