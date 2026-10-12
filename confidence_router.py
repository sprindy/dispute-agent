"""
Confidence & Risk Router — computes confidence scores and routes cases.

From Vision 4:
  Confidence = 0.30*P + 0.35*E + 0.15*C + 0.10*A + 0.10*R

Where:
  P = policy_clarity
  E = evidence_strength
  C = historical_consistency
  A = agent_consistency
  R = claim_reliability

Routes:
  High confidence + low risk → auto-resolve with challenge window
  Standard case → challenge window; valid challenge triggers debate
  Low confidence / high risk / verification failure → human review
"""
from dataclasses import dataclass
from enum import Enum
from agents.base_agent import AgentArgument
from config import (
    CONFIDENCE_WEIGHTS,
    HIGH_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
    HIGH_RISK_CATEGORIES,
    DisputeCategory,
    Assessment,
)


class RouteDestination(str, Enum):
    AUTO_RESOLVE = "auto_resolve"
    CHALLENGE_WINDOW = "challenge_window"
    HUMAN_REVIEW = "human_review"
    DEBATE = "debate"


@dataclass
class ConfidenceScore:
    """Breakdown of the confidence calculation."""
    policy_clarity: float
    evidence_strength: float
    historical_consistency: float
    agent_consistency: float
    claim_reliability: float
    total: float

    def to_dict(self) -> dict:
        return {
            "policy_clarity": round(self.policy_clarity, 3),
            "evidence_strength": round(self.evidence_strength, 3),
            "historical_consistency": round(self.historical_consistency, 3),
            "agent_consistency": round(self.agent_consistency, 3),
            "claim_reliability": round(self.claim_reliability, 3),
            "total": round(self.total, 3),
        }


class ConfidenceRouter:
    """
    Computes confidence scores from agent outputs and routes cases.
    """

    def compute_confidence(
        self,
        judge_arg: AgentArgument,
        rider_arg: AgentArgument,
        driver_arg: AgentArgument,
        case_category: str,
        case_rider_fraud_flags: int = 0,
        case_driver_fraud_flags: int = 0,
    ) -> ConfidenceScore:
        # P: policy clarity — from judge's confidence factors
        p = judge_arg.confidence_factors.get("policy_clarity", 0.50)

        # E: evidence strength — average of both advocates' evidence strength
        e_rider = rider_arg.confidence_factors.get("evidence_strength", 0.50)
        e_driver = driver_arg.confidence_factors.get("evidence_strength", 0.50)
        e = (e_rider + e_driver) / 2

        # C: historical consistency — lower if fraud flags present
        c = 0.80
        if case_rider_fraud_flags > 0 or case_driver_fraud_flags > 0:
            c = 0.50  # Fraud flags reduce consistency but don't determine liability

        # A: agent consistency — do both advocates agree?
        a = judge_arg.confidence_factors.get("agent_consistency", 0.50)

        # R: claim reliability — from judge's confidence factors
        r = judge_arg.confidence_factors.get("claim_reliability", 0.50)

        total = (
            CONFIDENCE_WEIGHTS["policy_clarity"] * p
            + CONFIDENCE_WEIGHTS["evidence_strength"] * e
            + CONFIDENCE_WEIGHTS["historical_consistency"] * c
            + CONFIDENCE_WEIGHTS["agent_consistency"] * a
            + CONFIDENCE_WEIGHTS["claim_reliability"] * r
        )

        return ConfidenceScore(
            policy_clarity=p,
            evidence_strength=e,
            historical_consistency=c,
            agent_consistency=a,
            claim_reliability=r,
            total=total,
        )

    def route(
        self,
        confidence: ConfidenceScore,
        category: str,
        verification_passed: bool,
        has_safety_flag: bool = False,
    ) -> RouteDestination:
        """
        Determine the route destination based on confidence, risk, and verification.
        """
        # Safety always escalates
        if has_safety_flag:
            return RouteDestination.HUMAN_REVIEW

        # Verification failure → human review
        if not verification_passed:
            return RouteDestination.HUMAN_REVIEW

        # High-risk categories → human review unless very high confidence
        if category in [c.value for c in HIGH_RISK_CATEGORIES]:
            if confidence.total < HIGH_CONFIDENCE_THRESHOLD:
                return RouteDestination.HUMAN_REVIEW

        # Low confidence → human review
        if confidence.total < LOW_CONFIDENCE_THRESHOLD:
            return RouteDestination.HUMAN_REVIEW

        # High confidence → auto-resolve (with challenge window)
        if confidence.total >= HIGH_CONFIDENCE_THRESHOLD:
            return RouteDestination.AUTO_RESOLVE

        # Standard case → challenge window
        return RouteDestination.CHALLENGE_WINDOW
