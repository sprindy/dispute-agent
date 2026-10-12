"""
Judge Agent — evaluates both advocate arguments and produces a ruling.

The Judge Agent:
- Compares Rider Advocate and Driver Advocate arguments
- Resolves conflicts using policy (BR-03)
- Does NOT compute refund amounts (BR-07)
- Routes to human review when confidence is low or risk is high (BR-09)
"""
from agents.base_agent import BaseAgent, AgentRole, AgentArgument
from config import Assessment, DisputeCategory


class JudgeAgent(BaseAgent):
    """
    The Judge Agent receives arguments from both advocates and produces
    a structured ruling with liability label, assessment, and routing decision.

    It enforces:
    - BR-01: Every decision is verified (delegates to verification layer)
    - BR-06: History must not independently establish liability
    - BR-07: Does NOT output refund amounts (Refund Engine handles that)
    """

    def __init__(self, policy_engine, evidence_collector_cls=None):
        super().__init__(AgentRole.JUDGE, policy_engine, evidence_collector_cls)

    def assess(self, case, rider_arg: AgentArgument, driver_arg: AgentArgument) -> AgentArgument:
        """
        Compare both advocate arguments and produce a ruling.
        """
        category = case.category

        # Safety cases: always escalate
        if rider_arg.assessment == Assessment.SAFETY_ESCALATION.value or \
           driver_arg.assessment == Assessment.SAFETY_ESCALATION.value:
            return AgentArgument(
                agent_role=self.role,
                liability_label="safety_escalation",
                assessment=Assessment.SAFETY_ESCALATION.value,
                rationale=(
                    "Safety allegation detected. Immediate human review required. "
                    "The system does not infer guilt or impose sanctions automatically."
                ),
                policy_ids=list(set(rider_arg.policy_ids + driver_arg.policy_ids)),
                source_ids=list(set(rider_arg.source_ids + driver_arg.source_ids)),
                evidence_ids=list(set(rider_arg.evidence_ids + driver_arg.evidence_ids)),
                confidence_factors={"policy_clarity": 0.95, "evidence_strength": 0.40},
                warnings=["SAFETY ESCALATION: Route to human review immediately."],
            )

        # Both agree → high confidence
        if rider_arg.liability_label == driver_arg.liability_label and \
           rider_arg.assessment == driver_arg.assessment:
            return self._build_consensus_ruling(case, rider_arg, driver_arg)

        # Source conflict
        if rider_arg.assessment == Assessment.SOURCE_CONFLICT.value or \
           driver_arg.assessment == Assessment.SOURCE_CONFLICT.value:
            return self._build_source_conflict_ruling(rider_arg, driver_arg)

        # Policy gap
        if rider_arg.assessment == Assessment.POLICY_GAP.value or \
           driver_arg.assessment == Assessment.POLICY_GAP.value:
            return self._build_policy_gap_ruling(rider_arg, driver_arg)

        # Insufficient evidence from either side
        if rider_arg.assessment == Assessment.INSUFFICIENT_EVIDENCE.value or \
           driver_arg.assessment == Assessment.INSUFFICIENT_EVIDENCE.value:
            return self._build_insufficient_ruling(rider_arg, driver_arg)

        # Disagreement on liability → debate or human review
        return self._build_disagreement_ruling(rider_arg, driver_arg)

    def _build_consensus_ruling(self, case, rider_arg, driver_arg) -> AgentArgument:
        """Both advocates agree — build a consensus ruling."""
        all_policy_ids = list(set(rider_arg.policy_ids + driver_arg.policy_ids))
        all_source_ids = list(set(rider_arg.source_ids + driver_arg.source_ids))
        all_evidence_ids = list(set(rider_arg.evidence_ids + driver_arg.evidence_ids))
        all_warnings = list(set(rider_arg.warnings + driver_arg.warnings))

        liability = rider_arg.liability_label
        assessment = rider_arg.assessment

        # Check if discretionary
        if assessment == Assessment.DISCRETIONARY_REVIEW.value:
            liability = "discretionary_review"

        return AgentArgument(
            agent_role=self.role,
            liability_label=liability,
            assessment=assessment,
            rationale=(
                f"Consensus ruling: Both Rider Advocate and Driver Advocate agree. "
                f"{rider_arg.rationale} "
                f"Liability: {liability}. "
                f"Refund amount (if applicable) to be calculated by Refund Engine."
            ),
            policy_ids=all_policy_ids,
            source_ids=all_source_ids,
            evidence_ids=all_evidence_ids,
            confidence_factors={
                "policy_clarity": 0.90,
                "evidence_strength": 0.85,
                "agent_consistency": 0.95,
            },
            warnings=all_warnings + [self._format_history_note(case)],
        )

    def _build_source_conflict_ruling(self, rider_arg, driver_arg) -> AgentArgument:
        all_policy_ids = list(set(rider_arg.policy_ids + driver_arg.policy_ids))
        return AgentArgument(
            agent_role=self.role,
            liability_label="source_conflict",
            assessment=Assessment.SOURCE_CONFLICT.value,
            rationale=(
                "Published policy sources conflict on this topic. "
                "Do not invent precedence between sources. "
                "Route to human review with a request for Ryde clarification."
            ),
            policy_ids=all_policy_ids,
            source_ids=list(set(rider_arg.source_ids + driver_arg.source_ids)),
            evidence_ids=list(set(rider_arg.evidence_ids + driver_arg.evidence_ids)),
            confidence_factors={"policy_clarity": 0.40, "evidence_strength": 0.60},
            warnings=[
                "Source conflict: cannot auto-resolve. Human review required.",
                "Do not assert source hierarchy without confirmation.",
            ],
        )

    def _build_policy_gap_ruling(self, rider_arg, driver_arg) -> AgentArgument:
        return AgentArgument(
            agent_role=self.role,
            liability_label="policy_gap",
            assessment=Assessment.POLICY_GAP.value,
            rationale=(
                "The public policy text does not resolve this boundary or detail. "
                "Obtain clarification before making a determination."
            ),
            policy_ids=list(set(rider_arg.policy_ids + driver_arg.policy_ids)),
            source_ids=list(set(rider_arg.source_ids + driver_arg.source_ids)),
            evidence_ids=list(set(rider_arg.evidence_ids + driver_arg.evidence_ids)),
            confidence_factors={"policy_clarity": 0.30, "evidence_strength": 0.60},
            warnings=["Policy gap: boundary unresolved in public text. Human review."],
        )

    def _build_insufficient_ruling(self, rider_arg, driver_arg) -> AgentArgument:
        return AgentArgument(
            agent_role=self.role,
            liability_label="insufficient_evidence",
            assessment=Assessment.INSUFFICIENT_EVIDENCE.value,
            rationale=(
                "Insufficient verified evidence to reach a determination. "
                "Missing facts must remain UNKNOWN. Request additional evidence "
                "from the relevant party or system."
            ),
            policy_ids=list(set(rider_arg.policy_ids + driver_arg.policy_ids)),
            source_ids=list(set(rider_arg.source_ids + driver_arg.source_ids)),
            evidence_ids=list(set(rider_arg.evidence_ids + driver_arg.evidence_ids)),
            confidence_factors={"policy_clarity": 0.70, "evidence_strength": 0.25},
            warnings=[
                "Insufficient evidence: do not infer or fabricate missing facts (BR-02).",
                "Request additional evidence before proceeding.",
            ],
        )

    def _build_disagreement_ruling(self, rider_arg, driver_arg) -> AgentArgument:
        return AgentArgument(
            agent_role=self.role,
            liability_label="contested",
            assessment=Assessment.CONFLICTING_EVIDENCE.value,
            rationale=(
                "Advocates disagree on liability. The case requires "
                "re-evaluation or debate. If debate rounds are exhausted "
                "without resolution, route to human review (BR-09)."
            ),
            policy_ids=list(set(rider_arg.policy_ids + driver_arg.policy_ids)),
            source_ids=list(set(rider_arg.source_ids + driver_arg.source_ids)),
            evidence_ids=list(set(rider_arg.evidence_ids + driver_arg.evidence_ids)),
            confidence_factors={"policy_clarity": 0.70, "evidence_strength": 0.50, "agent_consistency": 0.40},
            warnings=[
                "Advocate disagreement: trigger challenge gate for debate eligibility.",
                "If unresolved after max debate rounds, escalate to human review.",
            ],
        )
