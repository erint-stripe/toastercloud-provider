"""Pydantic models for APP 0.1d request/response bodies."""

from typing import Any, Literal, Optional
from pydantic import BaseModel


# --- Account Request ---

class KYC(BaseModel):
    verified_fields: list[str] = []


class Actor(BaseModel):
    email: Optional[str] = None
    ip_address: Optional[str] = None


class StripeOrchestrator(BaseModel):
    organization: str
    organisation: str  # deprecated alias
    account: str


class OrchestratorDetails(BaseModel):
    type: str
    stripe: StripeOrchestrator


class AccountRequestBody(BaseModel):
    id: str
    object: str
    name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    country: Optional[str] = None
    scopes: list[str] = []
    kyc: Optional[KYC] = None
    client_capabilities: list[str] = []
    actor: Optional[Actor] = None
    configuration: Optional[dict[str, Any]] = None
    confirmation_secret: str
    expires_at: str
    orchestrator: OrchestratorDetails


class BearerAccount(BaseModel):
    id: str
    payment_credentials: Optional[Literal["orchestrator", "provider"]] = None


class BearerCredentials(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    account: BearerAccount


class CredentialsWrapper(BaseModel):
    type: Literal["bearer"]
    bearer: BearerCredentials


class AccountRequestResponse(BaseModel):
    type: Literal["credentials", "requires_auth", "oauth", "error"]
    credentials: Optional[CredentialsWrapper] = None
    oauth: Optional[dict[str, str]] = None
    requires_auth: Optional[dict] = None
    error: Optional[dict[str, str]] = None


# --- Services ---

class ServicesResponse(BaseModel):
    data: list[dict[str, Any]]
    next_cursor: Optional[str] = None


# --- Resources ---

class ProvisionResourceBody(BaseModel):
    service_id: str
    configuration: dict[str, Any] = {}
    project_id: Optional[str] = None
    orchestrator_resource_id: str
    environment: Optional[str] = "prod"
    actor: Optional[Actor] = None
    payment_credentials: Optional[dict[str, Any]] = None
    submitted_information: Optional[dict[str, Any]] = None


class ResourceCompletePayload(BaseModel):
    access_configuration: Optional[dict[str, Any]] = None


class ResourceResponse(BaseModel):
    status: Literal["pending", "complete", "pending_removal", "removed", "error", "needs_information"]
    id: Optional[str] = None
    complete: Optional[ResourceCompletePayload] = None
    error: Optional[dict[str, str]] = None
    needs_information: Optional[dict] = None


class UpdateServiceBody(BaseModel):
    service_id: Optional[str] = None
    configuration: Optional[dict[str, Any]] = None
    payment_credentials: Optional[dict[str, Any]] = None
    actor: Optional[Actor] = None


class RemoveResourceBody(BaseModel):
    actor: Optional[Actor] = None


class RotateCredentialsBody(BaseModel):
    actor: Optional[Actor] = None


# --- Deep Links ---

class DeepLinkBody(BaseModel):
    purpose: str
    actor: Optional[Actor] = None


class DeepLinkResponse(BaseModel):
    purpose: str
    url: str
    expires_at: str


# --- Health ---

class HealthResponse(BaseModel):
    supported_versions: list[str]
    status: Literal["ok"]
