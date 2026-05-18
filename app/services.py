"""ToasterCloud service catalog."""

SERVICES: list[dict] = [
    {
        "id": "pop",
        "description": "Pop — Shared CPU, 128 MB RAM. Every great idea starts with a little pop. Free forever.",
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
        "allowed_updates": [{"service": "golden", "direction": "up"}],
        "constraints": {"count": {"at_most": 5}},
    },
    {
        "id": "golden",
        "description": "Golden — 0.5 vCPU, 256 MB RAM. Golden brown performance for apps that need a little more warmth.",
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
            {"service": "pop", "direction": "down"},
            {"service": "well-done", "direction": "up"},
        ],
        "constraints": {"count": {"at_most": 3}},
    },
    {
        "id": "well-done",
        "description": "Well Done — 1 vCPU, 512 MB RAM. No pink in the middle. Production-ready compute for serious workloads.",
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
        "pricing": {
            "type": "paid",
            "paid": [{"type": "freeform", "freeform": "$19/month", "is_default": True}],
        },
        "scope": "project",
        "allowed_updates": [
            {"service": "golden", "direction": "down"},
            {"service": "artisan", "direction": "up"},
        ],
        "constraints": {"count": {"at_most": 2}},
    },
    {
        "id": "artisan",
        "description": "Artisan — 2 vCPU, 1 GB RAM. Slow-toasted to perfection. High-performance compute for demanding applications.",
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
        "pricing": {
            "type": "paid",
            "paid": [{"type": "freeform", "freeform": "$39/month", "is_default": True}],
        },
        "scope": "project",
        "allowed_updates": [
            {"service": "well-done", "direction": "down"},
            {"service": "sourdough", "direction": "up"},
        ],
        "constraints": {"count": {"at_most": 1}},
    },
    {
        "id": "sourdough",
        "description": (
            "Sourdough — 4 vCPU, 2 GB RAM, NVMe-backed storage. "
            "The long ferment. Maximum throughput. Takes time to appreciate."
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
        "pricing": {
            "type": "paid",
            "paid": [{"type": "freeform", "freeform": "$79/month", "is_default": True}],
        },
        "scope": "project",
        "allowed_updates": [{"service": "artisan", "direction": "down"}],
        "constraints": {"count": {"at_most": 1}},
    },
]

SERVICES_BY_ID: dict[str, dict] = {s["id"]: s for s in SERVICES}
