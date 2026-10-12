"""
Dispute Resolver — orchestrates the end-to-end dispute resolution flow.

Flow (from Vision 4):
  1. Intake & Triage → classify dispute, load policies
  2. Evidence Collection → gather & validate evidence
  3. Advocate Assessment → Rider Advocate + Driver Advocate
  4. Verification → deterministic checks on agent outputs
  5. Judge Ruling → evaluate both arguments
  6. Confidence & Risk Routing → auto-resolve / challenge / human
  7. Challenge Window (if applicable) → accept or debate
  8. Refund Engine → deterministic amount (if applicable)
  9. Final Decision & Notification
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from policy_engine import PolicyEngine
from evidence_collector import EvidenceCollector, DisputeCase
from agents import RiderAdvocate, DriverAdvocate, JudgeAgent, AgentArgument
from verification import VerificationLayer
from confidence_router import ConfidenceRouter, RouteDestination
from challenge_gate import ChallengeGate
from refund_engine import RefundEngine
from config import DisputeCategory, Assessment


@dataclass
class DisputeStage:
    """A single stage in the resolution process."""
    stage_name: str
    started_at: str
    completed_at: str = ""
    status: str = "pending"  # pending, in_progress, completed, failed
    details: dict = field(default_factory=dict)


@dataclass
class ResolutionResult:
    """Final result of the dispute resolution pipeline."""
    dispute_id: str
    category: str
    stages: list[DisputeStage] = field(default_factory=list)
    rider_argument: Optional[dict] = None
    driver_argument: Optional[dict] = None
    judge_ruling: Optional[dict] = None
    confidence_score: Optional[dict] = None
    route: str = ""
    refund: Optional[dict] = None
    final_assessment: str = ""
    liability_label: str = ""
    human_review_required: bool = True
    final_decision: bool = False
    next_step: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "dispute_id": self.dispute_id,
            "category": self.category,
            "stages": [
                {"stage": s.stage_name, "status": s.status, "details": s.details}
                for s in self.stages
            ],
            "rider_argument": self.rider_argument,
            "driver_argument": self.driver_argument,
            "judge_ruling": self.judge_ruling,
            "confidence_score": self.confidence_score,
            "route": self.route,
            "refund": self.refund,
            "final_assessment": self.final_assessment,
            "liability_label": self.liability_label,
            "human_review_required": self.human_review_required,
            "final_decision": self.final_decision,
            "next_step": self.next_step,
            "timestamp": self.timestamp,
        }


class DisputeResolver:
    """
    Orchestrates the full dispute resolution pipeline.
    """

    def __init__(self, policy_engine: PolicyEngine):
        self.policy_engine = policy_engine
        self.rider_advocate = RiderAdvocate(policy_engine)
        self.driver_advocate = DriverAdvocate(policy_engine)
        self.judge = JudgeAgent(policy_engine)
        self.verifier = VerificationLayer(policy_engine)
        self.confidence_router = ConfidenceRouter()
        self.challenge_gate = ChallengeGate()
        self.refund_engine = RefundEngine(policy_engine)

    def resolve(self, case: DisputeCase) -> ResolutionResult:
        """Run the full resolution pipeline on a dispute case."""
        result = ResolutionResult(
            dispute_id=case.dispute_id,
            category=case.category,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        # --- Stage 1: Intake & Triage ---
        stage1 = DisputeStage("intake_triage", datetime.utcnow().isoformat() + "Z")
        stage1.status = "in_progress"
        policies = self.policy_engine.get_rules_for_category(
            DisputeCategory(case.category) if case.category in [c.value for c in DisputeCategory] else DisputeCategory.FARE_DISPUTE
        )
        case.policy_context = self.policy_engine.format_policy_context(
            [p.policy_id for p in policies]
        )
        stage1.details = {
            "category": case.category,
            "applicable_policies": [p.policy_id for p in policies],
            "filed_by": case.filed_by,
        }
        stage1.status = "completed"
        stage1.completed_at = datetime.utcnow().isoformat() + "Z"
        result.stages.append(stage1)

        # --- Stage 2: Evidence Collection ---
        stage2 = DisputeStage("evidence_collection", datetime.utcnow().isoformat() + "Z")
        stage2.status = "in_progress"
        evidence_report = EvidenceCollector.validate_evidence(case.evidence)
        case.facts.update(EvidenceCollector.extract_facts(case.evidence))
        stage2.details = evidence_report
        stage2.status = "completed"
        stage2.completed_at = datetime.utcnow().isoformat() + "Z"
        result.stages.append(stage2)

        # --- Stage 3: Advocate Assessment ---
        stage3 = DisputeStage("advocate_assessment", datetime.utcnow().isoformat() + "Z")
        stage3.status = "in_progress"
        rider_arg = self.rider_advocate.assess(case)
        driver_arg = self.driver_advocate.assess(case)
        result.rider_argument = rider_arg.to_dict()
        result.driver_argument = driver_arg.to_dict()
        stage3.details = {"rider_assessment": rider_arg.assessment, "driver_assessment": driver_arg.assessment}
        stage3.status = "completed"
        stage3.completed_at = datetime.utcnow().isoformat() + "Z"
        result.stages.append(stage3)

        # --- Stage 4: Verification ---
        stage4 = DisputeStage("verification", datetime.utcnow().isoformat() + "Z")
        stage4.status = "in_progress"
        evidence_ids = [e.evidence_id for e in case.evidence]
        rider_ver = self.verifier.verify(rider_arg, evidence_ids)
        driver_ver = self.verifier.verify(driver_arg, evidence_ids)
        stage4.details = {
            "rider_verification": {"passed": rider_ver.passed, "failures": rider_ver.failures},
            "driver_verification": {"passed": driver_ver.passed, "failures": driver_ver.failures},
        }
        verification_passed = rider_ver.passed and driver_ver.passed
        stage4.status = "completed"
        stage4.completed_at = datetime.utcnow().isoformat() + "Z"
        result.stages.append(stage4)

        # --- Stage 5: Judge Ruling ---
        stage5 = DisputeStage("judge_ruling", datetime.utcnow().isoformat() + "Z")
        stage5.status = "in_progress"
        judge_arg = self.judge.assess(case, rider_arg, driver_arg)
        result.judge_ruling = judge_arg.to_dict()
        stage5.details = {"liability": judge_arg.liability_label, "assessment": judge_arg.assessment}
        stage5.status = "completed"
        stage5.completed_at = datetime.utcnow().isoformat() + "Z"
        result.stages.append(stage5)

        # --- Stage 6: Confidence & Risk Routing ---
        stage6 = DisputeStage("confidence_routing", datetime.utcnow().isoformat() + "Z")
        stage6.status = "in_progress"
        has_safety = (
            rider_arg.assessment == Assessment.SAFETY_ESCALATION.value
            or driver_arg.assessment == Assessment.SAFETY_ESCALATION.value
        )
        confidence = self.confidence_router.compute_confidence(
            judge_arg, rider_arg, driver_arg, case.category
        )
        route = self.confidence_router.route(
            confidence, case.category, verification_passed, has_safety
        )
        result.confidence_score = confidence.to_dict()
        result.route = route.value
        stage6.details = {"confidence": confidence.to_dict(), "route": route.value}
        stage6.status = "completed"
        stage6.completed_at = datetime.utcnow().isoformat() + "Z"
        result.stages.append(stage6)

        # --- Stage 7: Final Decision ---
        stage7 = DisputeStage("final_decision", datetime.utcnow().isoformat() + "Z")
        stage7.status = "in_progress"
        result.final_assessment = judge_arg.assessment
        result.liability_label = judge_arg.liability_label

        if route == RouteDestination.AUTO_RESOLVE:
            result.human_review_required = False
            result.final_decision = True
            result.next_step = "Auto-resolved. Challenge window open for 48 hours."

            # Compute refund (BR-07: only Refund Engine computes amounts)
            refund = self.refund_engine.calculate(
                case.category, case.facts, judge_arg.liability_label
            )
            result.refund = refund.to_dict()

        elif route == RouteDestination.CHALLENGE_WINDOW:
            result.human_review_required = True
            result.final_decision = False
            result.next_step = "Preliminary ruling issued. Challenge window open."

            refund = self.refund_engine.calculate(
                case.category, case.facts, judge_arg.liability_label
            )
            result.refund = refund.to_dict()

        elif route == RouteDestination.HUMAN_REVIEW:
            result.human_review_required = True
            result.final_decision = False
            result.next_step = (
                "Escalated to human review. "
                + ("Safety allegation requires immediate investigation. " if has_safety else "")
                + "Evidence and agent arguments preserved for audit."
            )

        stage7.details = {
            "final_assessment": result.final_assessment,
            "liability_label": result.liability_label,
            "human_review_required": result.human_review_required,
            "final_decision": result.final_decision,
            "refund": result.refund,
        }
        stage7.status = "completed"
        stage7.completed_at = datetime.utcnow().isoformat() + "Z"
        result.stages.append(stage7)

        return result
