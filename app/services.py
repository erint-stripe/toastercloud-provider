"""ToasterCloud service catalog — all services are free tier."""

SERVICES: list[dict] = [
    {
        "id": "toaster:nano",
        "description": "Nano Toaster — Shared CPU, 128 MB RAM. Perfect for static sites and lightweight APIs.",
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
        "allowed_updates": [{"service": "toaster:micro", "direction": "up"}],
        "constraints": {"count": {"at_most": 5}},
    },
    {
        "id": "toaster:micro",
        "description": "Micro Toaster — 0.5 vCPU, 256 MB RAM. Ideal for development and small apps.",
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
        "pricing": {"type": "free"},
        "scope": "project",
        "allowed_updates": [
            {"service": "toaster:nano", "direction": "down"},
            {"service": "toaster:standard", "direction": "up"},
        ],
        "constraints": {"count": {"at_most": 3}},
    },
    {
        "id": "toaster:standard",
        "description": "Standard Toaster — 1 vCPU, 512 MB RAM. Production-ready compute.",
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
                    "description": "Enable auto-scaling up to 3 instances",
                    "default": False,
                },
            },
            "required": ["region", "name"],
        },
        "pricing": {"type": "free"},
        "scope": "project",
        "allowed_updates": [
            {"service": "toaster:micro", "direction": "down"},
            {"service": "toaster:pro", "direction": "up"},
        ],
        "constraints": {"count": {"at_most": 2}},
    },
    {
        "id": "toaster:pro",
        "description": "Pro Toaster — 2 vCPU, 1 GB RAM. High-performance compute for demanding workloads.",
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
                    "description": "Enable auto-scaling up to 5 instances",
                    "default": False,
                },
            },
            "required": ["region", "name"],
        },
        "pricing": {"type": "free"},
        "scope": "project",
        "allowed_updates": [
            {"service": "toaster:standard", "direction": "down"},
            {"service": "toaster:bagel", "direction": "up"},
        ],
        "constraints": {"count": {"at_most": 1}},
    },
    {
        "id": "toaster:bagel",
        "description": (
            "Bagel-Optimized Toaster — 4 vCPU, 2 GB RAM, NVMe-backed storage. "
            "Maximum throughput for your crunchiest workloads."
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
                    "description": "Enable auto-scaling up to 10 instances",
                    "default": False,
                },
                "toast_level": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 7,
                    "description": "Thermal optimization level (1=light, 7=extra crispy)",
                    "default": 4,
                },
            },
            "required": ["region", "name"],
        },
        "pricing": {"type": "free"},
        "scope": "project",
        "allowed_updates": [{"service": "toaster:pro", "direction": "down"}],
        "constraints": {"count": {"at_most": 1}},
    },
]

SERVICES_BY_ID: dict[str, dict] = {s["id"]: s for s in SERVICES}
