"""ToasterCloud service catalog.

Structure:
  Plans (standalone): single-slot, 2-slot, 4-slot, 8-slot, industrial
    — provision one of these first; one active per project at a time
  Deployable (component): toaster
    — the compute instance; lists all plans as parent_service_ids
"""

_PLAN_CONSTRAINTS = {
    "count": {"at_most": 1},
    "mutual_exclusion": {"allowed_updates": True},
}

_REGION_SCHEMA = {
    "type": "string",
    "enum": ["us-east-1", "eu-west-1", "ap-southeast-1"],
    "description": "Deployment region",
}

_NAME_SCHEMA = {
    "type": "string",
    "maxLength": 63,
    "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$",
    "description": "Instance name (lowercase, alphanumeric, hyphens)",
}

SERVICES: list[dict] = [
    # -------------------------------------------------------------------------
    # Plans — standalone; one active per project at a time
    # -------------------------------------------------------------------------
    {
        "id": "single-slot",
        "description": (
            "Single-Slot Plan — 1 dedicated slot (1 vCPU, 256 MB RAM). "
            "The compact travel toaster. One slot, one job, zero excuses."
        ),
        "categories": ["compute"],
        "kind": "plan",
        "scope": "project",
        "pricing": {"type": "free"},
        "allowed_updates": [{"service": "2-slot", "direction": "up"}],
        "constraints": _PLAN_CONSTRAINTS,
    },
    {
        "id": "2-slot",
        "description": (
            "2-Slot Plan — 2 dedicated slots (2 vCPU, 512 MB RAM). "
            "The classic countertop pop-up."
        ),
        "categories": ["compute"],
        "kind": "plan",
        "scope": "project",
        "pricing": {
            "type": "paid",
            "paid": {"type": "freeform", "freeform": "$9/month"},
        },
        "allowed_updates": [
            {"service": "single-slot", "direction": "down"},
            {"service": "4-slot", "direction": "up"},
        ],
        "constraints": _PLAN_CONSTRAINTS,
    },
    {
        "id": "4-slot",
        "description": (
            "4-Slot Plan — 4 dedicated slots (4 vCPU, 1 GB RAM). "
            "The family-size toaster. Load multiple slots in parallel."
        ),
        "categories": ["compute"],
        "kind": "plan",
        "scope": "project",
        "pricing": {
            "type": "paid",
            "paid": {"type": "freeform", "freeform": "$19/month"},
        },
        "allowed_updates": [
            {"service": "2-slot", "direction": "down"},
            {"service": "8-slot", "direction": "up"},
        ],
        "constraints": _PLAN_CONSTRAINTS,
    },
    {
        "id": "8-slot",
        "description": (
            "8-Slot Plan — 8 dedicated slots (8 vCPU, 2 GB RAM). "
            "The office workhorse. Eight wide slots for high-throughput teams."
        ),
        "categories": ["compute"],
        "kind": "plan",
        "scope": "project",
        "pricing": {
            "type": "paid",
            "paid": {"type": "freeform", "freeform": "$39/month"},
        },
        "allowed_updates": [
            {"service": "4-slot", "direction": "down"},
            {"service": "industrial", "direction": "up"},
        ],
        "constraints": _PLAN_CONSTRAINTS,
    },
    {
        "id": "industrial",
        "description": (
            "Industrial Plan — conveyor belt (16 vCPU, 8 GB RAM, NVMe). "
            "Continuous feed, infinite throughput. Built for the enterprise breakfast rush."
        ),
        "categories": ["compute"],
        "kind": "plan",
        "scope": "project",
        "pricing": {
            "type": "paid",
            "paid": {"type": "freeform", "freeform": "$79/month"},
        },
        "allowed_updates": [{"service": "8-slot", "direction": "down"}],
        "constraints": _PLAN_CONSTRAINTS,
    },

    # -------------------------------------------------------------------------
    # Deployable — compute instance; component of any active plan
    # -------------------------------------------------------------------------
    {
        "id": "toaster",
        "description": (
            "A ToasterCloud compute instance. "
            "Requires an active plan. Specs are determined by the plan in your project."
        ),
        "categories": ["compute"],
        "kind": "deployable",
        "scope": "project",
        "configuration_schema": {
            "type": "object",
            "properties": {
                "region": _REGION_SCHEMA,
                "name": _NAME_SCHEMA,
                "auto_scale": {
                    "type": "boolean",
                    "description": "Run slots in parallel (auto-scaling). Available on 4-slot and above.",
                    "default": False,
                },
                "toast_level": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 7,
                    "description": (
                        "Browning dial — CPU frequency scaling "
                        "(1=light, 7=extra crispy). Industrial plan only."
                    ),
                    "default": 4,
                },
            },
            "required": ["region", "name"],
        },
        "pricing": {
            "type": "component",
            "component": {
                "options": [
                    {
                        "parent_service_ids": [
                            "single-slot",
                            "2-slot",
                            "4-slot",
                            "8-slot",
                            "industrial",
                        ],
                        "type": "free",
                    }
                ]
            },
        },
    },
]

SERVICES_BY_ID: dict[str, dict] = {s["id"]: s for s in SERVICES}

PLAN_IDS: frozenset[str] = frozenset(
    s["id"] for s in SERVICES if s.get("kind") == "plan"
)
