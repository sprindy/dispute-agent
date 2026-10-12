"""
Base Agent — shared logic for all agents in the dispute resolution system.

Implements BR-06: Historical behavior must not independently establish liability.
All agents extend this base and produce structured, verifiable arguments.
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class AgentRole(str, Enum):
    RIDER_ADVOCATE = "rider_advocate"
    DRIVER_ADVOCATE = "driver_advocate"
    JUDGE = "judge"


@dataclass
class AgentArgument:
    """
    Structured output from an agent.
    Every claim must cite policy_ids and evidence_ids.
    """
    agent_role: AgentRole
    liability_label: str  # e.g. "rider_fault", "driver_fault", "no_fault", "insufficient_evidence"
    assessment: str  # One of the Assessment enum values
    rationale: str
    policy_ids: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    confidence_factors: dict = field(default_factory=dict)
    requested_remedy: Optional[str] = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent_role": self.agent_role.value,
            "liability_label": self.liability_label,
            "assessment": self.assessment,
            "rationale": self.rationale,
            "policy_ids": self.policy_ids,
            "source_ids": self.source_ids,
            "evidence_ids": self.evidence_ids,
            "confidence_factors": self.confidence_factors,
            "requested_remedy": self.requested_remedy,
            "warnings": self.warnings,
        }


class BaseAgent:
    """
    Base class for all agents.

    In a production system, each agent would call an LLM with a structured prompt.
    For this hackathon demo, agents use deterministic rule-based logic that
    mirrors the policy assessment patterns from the training data.

    Key constraint (BR-06): Historical behavior (driver_rating, prior_rejected_disputes)
    may influence confidence/risk routing but MUST NOT independently determine liability.
    """

    def __init__(self, role: AgentRole, policy_engine, evidence_collector_cls=None):
        self.role = role
        self.policy_engine = policy_engine
        self.EvidenceCollector = evidence_collector_cls

    def _get_policy_params(self, policy_id: str) -> dict:
        rule = self.policy_engine.get_rule(policy_id)
        return rule.parameters if rule else {}

    def _format_history_note(self, case) -> str:
        """
        Format historical context as a reference note.
        Explicitly mark it as non-determinative (BR-06).
        """
        return (
            f"Historical reference (non-determinative): "
            f"driver_rating={case.driver_rating}, "
            f"prior_rejected_disputes={case.prior_rejected_disputes}. "
            f"These may affect confidence and risk routing only."
        )

    def _check_conflicts(self, policy_ids: list[str]) -> list[str]:
        """Check for source conflicts or gaps affecting the cited policies."""
        warnings = []
        for pid in policy_ids:
            conflicts = self.policy_engine.get_conflicts_for_policy(pid)
            for c in conflicts:
                tag = "GAP" if c.is_gap else "CONFLICT"
                warnings.append(f"{c.id} ({tag}): {c.description}")
        return warnings

    def assess(self, case) -> AgentArgument:
        """Override in subclasses — produce a structured argument."""
        raise NotImplementedError
