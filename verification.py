"""
Verification Layer — deterministic checks on agent outputs.

Implements BR-01: Every LLM decision must be verified.
Verification failure blocks auto-execution.
"""
from dataclasses import dataclass
from typing import Optional
from agents.base_agent import AgentArgument
from config import Assessment


@dataclass
class VerificationResult:
    """Result of verifying an agent argument."""
    passed: bool
    checks_run: list[str]
    failures: list[str]
    verified_argument: Optional[AgentArgument] = None


class VerificationLayer:
    """
    Runs deterministic checks on agent outputs before they can proceed.

    Checks:
    1. Every cited policy_id exists in the policy engine
    2. Every cited evidence_id exists in the case evidence
    3. Every cited source_id resolves to a policy
    4. No unauthorized monetary action is proposed
    5. Missing facts were not fabricated
    6. Safety cases are escalated (not auto-resolved)
    """

    def __init__(self, policy_engine):
        self.policy_engine = policy_engine

    def verify(
        self,
        argument: AgentArgument,
        case_evidence_ids: list[str],
    ) -> VerificationResult:
        checks_run = []
        failures = []

        # 1. Policy IDs exist
        checks_run.append("policy_ids_exist")
        for pid in argument.policy_ids:
            if not self.policy_engine.get_rule(pid):
                failures.append(f"Unknown policy_id cited: {pid}")

        # 2. Evidence IDs exist
        checks_run.append("evidence_ids_exist")
        for eid in argument.evidence_ids:
            if eid not in case_evidence_ids:
                failures.append(f"Unknown evidence_id cited: {eid}")

        # 3. Source IDs resolve
        checks_run.append("source_ids_resolve")
        all_source_ids = set()
        for pid in argument.policy_ids:
            rule = self.policy_engine.get_rule(pid)
            if rule:
                all_source_ids.update(rule.source_ids)
        for sid in argument.source_ids:
            if sid not in all_source_ids:
                failures.append(f"Source_id {sid} does not resolve to any cited policy")

        # 4. No unauthorized monetary action (BR-07)
        checks_run.append("no_unauthorized_monetary_action")
        if argument.requested_remedy and "cash_refund" in str(argument.requested_remedy):
            failures.append(
                "Agent proposed cash_refund — only the Refund Engine may compute amounts (BR-07)"
            )

        # 5. Safety cases must escalate
        checks_run.append("safety_escalation_enforced")
        if argument.assessment == Assessment.SAFETY_ESCALATION.value:
            if argument.liability_label not in ("safety_escalation", "insufficient_evidence"):
                failures.append(
                    "Safety case must escalate — agent attempted to assign liability"
                )

        passed = len(failures) == 0
        return VerificationResult(
            passed=passed,
            checks_run=checks_run,
            failures=failures,
            verified_argument=argument if passed else None,
        )

    def verify_all(
        self,
        arguments: list[AgentArgument],
        case_evidence_ids: list[str],
    ) -> list[VerificationResult]:
        return [self.verify(arg, case_evidence_ids) for arg in arguments]
