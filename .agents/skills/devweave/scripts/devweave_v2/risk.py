"""Risk classification, gate, and review policy."""

from __future__ import annotations

from dataclasses import dataclass

from .verification_contracts import RiskLevel


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    required_gates: tuple[str, ...]
    planning_gates: tuple[str, ...]
    review_mode: str
    max_review_rounds: int


RISK_POLICIES: dict[RiskLevel, RiskPolicy] = {
    RiskLevel.LOW: RiskPolicy(("plan",), ("plan",), "self", 1),
    RiskLevel.STANDARD: RiskPolicy(("plan", "acceptance"), ("plan",), "detached", 1),
    RiskLevel.HIGH: RiskPolicy(("scope", "design", "acceptance"), ("scope", "design"), "detached_fix_reverify", 3),
}

RISK_ORDER = {RiskLevel.LOW: 0, RiskLevel.STANDARD: 1, RiskLevel.HIGH: 2}


def policy_for(risk: RiskLevel) -> RiskPolicy:
    return RISK_POLICIES[risk]


def escalate_risk(requested: RiskLevel, signals: set[str]) -> RiskLevel:
    """Return the minimum safe level for known high-impact signals."""
    normalized = {item.strip().lower() for item in signals}
    high = {"security", "credentials", "data_migration", "public_schema", "git_policy", "release"}
    standard = {"dependencies", "build", "ci", "multiple_modules", "persistent_state"}
    floor = RiskLevel.HIGH if normalized & high else RiskLevel.STANDARD if normalized & standard else RiskLevel.LOW
    return requested if RISK_ORDER[requested] >= RISK_ORDER[floor] else floor
