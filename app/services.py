"""ToasterCloud service catalog."""

SERVICES: list[dict] = [
    {
        "id": "single-slot",
        "description": (
            "Single-Slot — 1 vCPU, 256 MB RAM. "
            "The compact travel toaster. One slot, one job, zero excuses."
        ),
        "categories": ["compute"],
        "group": "toaster",
        "configuration_schema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "enum": ["us-east-1", "eu-west-1", "ap-southeast-1"],
                    "description": "Deployment region",
                },
                "name": {
                    "type": "string",
                    "maxLength": 63,
                    "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$",
                    "description": "Instance name (lowercase, alphanumeric, hyphens)",
                },
            },
            "required": ["region", "name"],
        },
        "pricing": {"type": "free"},
        "scope": "project",
        "allowed_updates": [{"service": "2-slot", "direction": "up"}],
        "constraints": {"count": {"at_most": 5}},
    },
    {
        "id": "2-slot",
        "description": (
            "2-Slot — 2 vCPU, 512 MB RAM. "
            "The classic countertop pop-up. Two dedicated slots for the everyday workload."
        ),
        "categories": ["compute"],
        "group": "toaster",
        "configuration_schema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "enum": ["us-east-1", "eu-west-1", "ap-southeast-1"],
                    "description": "Deployment region",
                },
                "name": {
                    "type": "string",
                    "maxLength": 63,
                    "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$",
                    "description": "Instance name",
                },
            },
            "required": ["region", "name"],
        },
        "pricing": {
            "type": "paid",
            "paid": [{"type": "freeform", "freeform": "$9/month", "is_default": True}],
        },
        "scope": "project",
        "allowed_updates": [
            {"service": "single-slot", "direction": "down"},
            {"service": "4-slot", "direction": "up"},
        ],
        "constraints": {"count": {"at_most": 3}},
    },
    {
        "id": "4-slot",
        "description": (
            "4-Slot — 4 vCPU, 1 GB RAM. "
            "The family-size toaster. Load multiple slots simultaneously for parallel workloads."
        ),
        "categories": ["compute"],
        "group": "toaster",
        "configuration_schema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "enum": ["us-east-1", "eu-west-1", "ap-southeast-1"],
                    "description": "Deployment region",
                },
                "name": {
                    "type": "string",
                    "maxLength": 63,
                    "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$",
                    "description": "Instance name",
                },
                "auto_scale": {
                    "type": "boolean",
                    "description": "Load all four slots simultaneously (auto-scaling up to 3 instances)",
                    "default": False,
                },
            },
            "required": ["region", "name"],
        },
        "pricing": {
            "type": "paid",
            "paid": [{"type": "freeform", "freeform": "$19/month", "is_default": True}],
        },
        "scope": "project",
        "allowed_updates": [
            {"service": "2-slot", "direction": "down"},
            {"service": "8-slot", "direction": "up"},
        ],
        "constraints": {"count": {"at_most": 2}},
    },
    {
        "id": "8-slot",
        "description": (
            "8-Slot — 8 vCPU, 2 GB RAM. "
            "The office workhorse. Eight wide slots, built for high-throughput teams."
        ),
        "categories": ["compute"],
        "group": "toaster",
        "configuration_schema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "enum": ["us-east-1", "eu-west-1", "ap-southeast-1"],
                    "description": "Deployment region",
                },
                "name": {
                    "type": "string",
                    "maxLength": 63,
                    "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$",
                    "description": "Instance name",
                },
                "auto_scale": {
                    "type": "boolean",
                    "description": "Run all eight slots in parallel (auto-scaling up to 5 instances)",
                    "default": False,
                },
            },
            "required": ["region", "name"],
        },
        "pricing": {
            "type": "paid",
            "paid": [{"type": "freeform", "freeform": "$39/month", "is_default": True}],
        },
        "scope": "project",
        "allowed_updates": [
            {"service": "4-slot", "direction": "down"},
            {"service": "industrial", "direction": "up"},
        ],
        "constraints": {"count": {"at_most": 1}},
    },
    {
        "id": "industrial",
        "description": (
            "Industrial — 16 vCPU, 8 GB RAM, NVMe-backed storage. "
            "The conveyor belt toaster. Continuous feed, infinite throughput, "
            "precision browning control. Built for the enterprise breakfast rush."
        ),
        "categories": ["compute"],
        "group": "toaster",
        "configuration_schema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "enum": ["us-east-1", "eu-west-1", "ap-southeast-1"],
                    "description": "Deployment region",
                },
                "name": {
                    "type": "string",
                    "maxLength": 63,
                    "pattern": "^[a-z0-9][a-z0-9-]*[a-z0-9]$",
                    "description": "Instance name",
                },
                "auto_scale": {
                    "type": "boolean",
                    "description": "Engage continuous conveyor mode (auto-scaling up to 10 instances)",
                    "default": False,
                },
                "toast_level": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 7,
                    "description": "Browning dial — controls CPU frequency scaling (1=light, 7=extra crispy)",
                    "default": 4,
                },
            },
            "required": ["region", "name"],
        },
        "pricing": {
            "type": "paid",
            "paid": [{"type": "freeform", "freeform": "$79/month", "is_default": True}],
        },
        "scope": "project",
        "allowed_updates": [{"service": "8-slot", "direction": "down"}],
        "constraints": {"count": {"at_most": 1}},
    },
]

SERVICES_BY_ID: dict[str, dict] = {s["id"]: s for s in SERVICES}
