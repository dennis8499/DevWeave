"""Registry for the five versioned public DevWeave schemas."""

from __future__ import annotations

from typing import Any, Callable

from .plan_contracts import PendingDecision, RunPlanDraft
from .snapshot_contracts import RunSnapshot
from .verification_contracts import ReviewFinding, VerificationPlan
from .version import SCHEMA_VERSION

PUBLIC_SCHEMA_TYPES: dict[str, type[Any]] = {
    "PendingDecision": PendingDecision,
    "ReviewFinding": ReviewFinding,
    "RunPlanDraft": RunPlanDraft,
    "RunSnapshot": RunSnapshot,
    "VerificationPlan": VerificationPlan,
}

PUBLIC_SCHEMA_TRACES: dict[str, tuple[str, ...]] = {
    "PendingDecision": ("REQ-008", "AC-008", "AC-011", "AC-016"),
    "ReviewFinding": ("REQ-014", "AC-011", "AC-014"),
    "RunPlanDraft": ("REQ-007", "REQ-011", "AC-007", "AC-011"),
    "RunSnapshot": ("REQ-007", "REQ-011", "AC-007", "AC-011", "AC-017"),
    "VerificationPlan": ("REQ-013", "AC-011", "AC-013"),
}


def parse_public_schema(name: str, raw: Any) -> Any:
    schema_type = PUBLIC_SCHEMA_TYPES.get(name)
    if schema_type is None:
        from .errors import ContractError, ErrorCode
        raise ContractError(
            ErrorCode.INVALID_VALUE,
            "Unknown public schema name.",
            {"schema": name, "allowed": sorted(PUBLIC_SCHEMA_TYPES)},
        )
    parser: Callable[[Any], Any] = schema_type.from_dict
    return parser(raw)


def schema_catalog() -> dict[str, Any]:
    """A stable machine catalog; full validation remains in typed parsers."""
    return {
        "schema_version": SCHEMA_VERSION,
        "schemas": [
            {
                "name": name,
                "additional_properties": False,
                "traces": list(PUBLIC_SCHEMA_TRACES[name]),
            }
            for name in sorted(PUBLIC_SCHEMA_TYPES)
        ],
    }
