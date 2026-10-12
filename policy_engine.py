"""
Policy Engine — loads and queries the Ryde public policy snapshot.

Implements BR-03: Company policy takes priority over historical references.
All policy IDs are project-assigned, not Ryde clause IDs.
"""
import json
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path

from config import (
    POLICIES_FILE,
    CONFLICTS_FILE,
    POLICY_SNAPSHOT_ID,
    CATEGORY_POLICY_MAP,
    DisputeCategory,
)


@dataclass
class PolicyRule:
    """A single encoded policy rule from the public snapshot."""
    policy_id: str
    category: str
    summary: str
    source_ids: list[str]
    parameters: dict
    status: str  # public_rule, discretionary, context_dependent, source_conflict
    interpretation_note: str = ""
    effective_from: Optional[str] = None
    as_of: str = ""
    final_authority: str = "Ryde support or applicable agreement"

    def is_discretionary(self) -> bool:
        return self.status == "discretionary"

    def is_source_conflict(self) -> bool:
        return self.status == "source_conflict"

    def is_context_dependent(self) -> bool:
        return self.status == "context_dependent"


@dataclass
class PolicyConflict:
    """A documented conflict between public sources or an unresolved gap."""
    id: str
    topic: str
    source_ids: list[str]
    description: str
    is_gap: bool = False


class PolicyEngine:
    """
    Loads the full policy snapshot and provides lookup utilities.
    All agents use this engine — no agent invents policy.
    """

    def __init__(self):
        self.snapshot_id = POLICY_SNAPSHOT_ID
        self.rules: dict[str, PolicyRule] = {}
        self.conflicts: list[PolicyConflict] = []
        self._load()

    def _load(self):
        with open(POLICIES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.snapshot_id = data.get("policy_snapshot_id", POLICY_SNAPSHOT_ID)
        for r in data.get("rules", []):
            rule = PolicyRule(
                policy_id=r["policy_id"],
                category=r["category"],
                summary=r["summary"],
                source_ids=r.get("source_ids", []),
                parameters=r.get("parameters", {}),
                status=r.get("status", "public_rule"),
                interpretation_note=r.get("interpretation_note", ""),
                effective_from=r.get("effective_from"),
                as_of=r.get("as_of", ""),
            )
            self.rules[rule.policy_id] = rule

        with open(CONFLICTS_FILE, "r", encoding="utf-8") as f:
            for c in json.load(f):
                self.conflicts.append(PolicyConflict(
                    id=c["id"],
                    topic=c["topic"],
                    source_ids=c.get("source_ids", []),
                    description=c["description"],
                    is_gap=c["id"].startswith("GAP"),
                ))

    def get_rule(self, policy_id: str) -> Optional[PolicyRule]:
        return self.rules.get(policy_id)

    def get_rules_for_category(self, category: DisputeCategory) -> list[PolicyRule]:
        """Return all policy rules relevant to a dispute category."""
        policy_ids = CATEGORY_POLICY_MAP.get(category, [])
        return [self.rules[pid] for pid in policy_ids if pid in self.rules]

    def get_conflicts_for_policy(self, policy_id: str) -> list[PolicyConflict]:
        """Return conflicts/gaps that reference the given policy's sources."""
        rule = self.get_rule(policy_id)
        if not rule:
            return []
        return [
            c for c in self.conflicts
            if any(sid in c.source_ids for sid in rule.source_ids)
        ]

    def get_conflict_by_id(self, conflict_id: str) -> Optional[PolicyConflict]:
        for c in self.conflicts:
            if c.id == conflict_id:
                return c
        return None

    def format_policy_context(self, policy_ids: list[str]) -> list[dict]:
        """Format policy rules for agent consumption."""
        result = []
        for pid in policy_ids:
            rule = self.get_rule(pid)
            if rule:
                result.append({
                    "policy_id": rule.policy_id,
                    "category": rule.category,
                    "summary": rule.summary,
                    "status": rule.status,
                    "parameters": rule.parameters,
                    "interpretation_note": rule.interpretation_note,
                    "source_ids": rule.source_ids,
                })
        return result

    def all_rule_ids(self) -> list[str]:
        return sorted(self.rules.keys())

    def summary(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "total_rules": len(self.rules),
            "total_conflicts": len([c for c in self.conflicts if not c.is_gap]),
            "total_gaps": len([c for c in self.conflicts if c.is_gap]),
        }
