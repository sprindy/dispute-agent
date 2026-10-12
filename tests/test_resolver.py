"""
Unit tests for the Ryde Dispute Resolution Agent.

Tests cover:
- Policy engine loading and queries
- Evidence collector validation
- Agent assessment logic
- Verification layer
- Confidence router
- Refund engine
- End-to-end dispute resolution
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from policy_engine import PolicyEngine
from evidence_collector import EvidenceCollector, DisputeCase, EvidenceItem, EvidenceStatus, EvidenceKind
from agents import RiderAdvocate, DriverAdvocate, JudgeAgent
from verification import VerificationLayer
from confidence_router import ConfidenceRouter, RouteDestination
from challenge_gate import ChallengeGate
from refund_engine import RefundEngine
from dispute_resolver import DisputeResolver
from sample_cases import (
    build_disp002_case,
    build_route_deviation_case,
    build_cancellation_grace_case,
    build_cash_processing_fee_case,
    build_safety_incident_case,
)
from config import Assessment, DisputeCategory


class TestPolicyEngine:
    def test_loads_all_rules(self):
        pe = PolicyEngine()
        assert len(pe.rules) == 79

    def test_get_rule(self):
        pe = PolicyEngine()
        rule = pe.get_rule("CAN-01")
        assert rule is not None
        assert rule.category == "cancellation"
        assert rule.parameters.get("grace_seconds") == 180

    def test_get_rules_for_category(self):
        pe = PolicyEngine()
        rules = pe.get_rules_for_category(DisputeCategory.NO_SHOW_CHARGE)
        assert len(rules) > 0
        assert any(r.policy_id == "CAN-02" for r in rules)

    def test_get_conflicts(self):
        pe = PolicyEngine()
        conflicts = pe.conflicts
        assert len(conflicts) == 11  # 7 conflicts + 4 gaps
        assert any(c.id == "CONFLICT-01" for c in conflicts)
        assert any(c.id == "GAP-01" for c in conflicts)

    def test_snapshot_id(self):
        pe = PolicyEngine()
        assert pe.snapshot_id == "RYDE-PUBLIC-2026-10-08-v1"


class TestEvidenceCollector:
    def test_validate_evidence(self):
        items = [
            EvidenceItem("E1", EvidenceKind.GPS_TELEMETRY, EvidenceStatus.AVAILABLE, field="test", value=True),
            EvidenceItem("E2", EvidenceKind.CHAT_LOG, EvidenceStatus.MISSING),
            EvidenceItem("E3", EvidenceKind.PAYMENT_DATA, EvidenceStatus.DISPUTED, field="amount", value=10),
        ]
        report = EvidenceCollector.validate_evidence(items)
        assert report["total"] == 3
        assert report["available"] == 1
        assert report["missing"] == 1
        assert report["disputed"] == 1

    def test_extract_facts_missing_stays_unknown(self):
        items = [
            EvidenceItem("E1", EvidenceKind.GPS_TELEMETRY, EvidenceStatus.MISSING, field="arrival", value=None),
            EvidenceItem("E2", EvidenceKind.APP_EVENT, EvidenceStatus.AVAILABLE, field="charge", value=6.61),
        ]
        facts = EvidenceCollector.extract_facts(items)
        assert "arrival" not in facts  # Missing → stays UNKNOWN (BR-02)
        assert facts.get("charge") == 6.61


class TestRiderAdvocate:
    def test_disp002_no_show(self):
        pe = PolicyEngine()
        advocate = RiderAdvocate(pe)
        case = build_disp002_case()
        result = advocate.assess(case)
        assert result.agent_role.value == "rider_advocate"
        # Driver arrived and waited > 3 min → charge is policy-consistent
        assert result.assessment == Assessment.POLICY_CONSISTENT.value
        assert "CAN-02" in result.policy_ids

    def test_cancellation_grace(self):
        pe = PolicyEngine()
        advocate = RiderAdvocate(pe)
        case = build_cancellation_grace_case()
        result = advocate.assess(case)
        # Cancelled within 3 min → charge is inconsistent
        assert result.assessment == Assessment.POLICY_INCONSISTENT.value
        assert "CAN-01" in result.policy_ids

    def test_cash_processing_fee(self):
        pe = PolicyEngine()
        advocate = RiderAdvocate(pe)
        case = build_cash_processing_fee_case()
        result = advocate.assess(case)
        assert result.assessment == Assessment.POLICY_INCONSISTENT.value
        assert "FARE-11" in result.policy_ids


class TestDriverAdvocate:
    def test_disp002_no_show(self):
        pe = PolicyEngine()
        advocate = DriverAdvocate(pe)
        case = build_disp002_case()
        result = advocate.assess(case)
        # Driver arrived, waited > 3 min → consistent
        assert result.assessment == Assessment.POLICY_CONSISTENT.value

    def test_safety_escalation(self):
        pe = PolicyEngine()
        advocate = DriverAdvocate(pe)
        case = build_safety_incident_case()
        result = advocate.assess(case)
        assert result.assessment == Assessment.SAFETY_ESCALATION.value


class TestVerificationLayer:
    def test_valid_argument_passes(self):
        pe = PolicyEngine()
        verifier = VerificationLayer(pe)
        from agents.base_agent import AgentArgument, AgentRole
        arg = AgentArgument(
            agent_role=AgentRole.RIDER_ADVOCATE,
            liability_label="no_fault",
            assessment=Assessment.POLICY_INCONSISTENT.value,
            rationale="Test",
            policy_ids=["CAN-01"],
            source_ids=pe.get_rule("CAN-01").source_ids,
            evidence_ids=["E1"],
        )
        result = verifier.verify(arg, ["E1"])
        assert result.passed
        assert len(result.failures) == 0

    def test_unknown_policy_fails(self):
        pe = PolicyEngine()
        verifier = VerificationLayer(pe)
        from agents.base_agent import AgentArgument, AgentRole
        arg = AgentArgument(
            agent_role=AgentRole.RIDER_ADVOCATE,
            liability_label="no_fault",
            assessment=Assessment.POLICY_INCONSISTENT.value,
            rationale="Test",
            policy_ids=["FAKE-99"],
            source_ids=[],
            evidence_ids=["E1"],
        )
        result = verifier.verify(arg, ["E1"])
        assert not result.passed
        assert any("FAKE-99" in f for f in result.failures)


class TestConfidenceRouter:
    def test_safety_routes_to_human(self):
        router = ConfidenceRouter()
        from agents.base_agent import AgentArgument, AgentRole
        from confidence_router import ConfidenceScore
        score = ConfidenceScore(0.9, 0.9, 0.8, 0.9, 0.8, 0.85)
        route = router.route(score, "safety_incident", verification_passed=True, has_safety_flag=True)
        assert route == RouteDestination.HUMAN_REVIEW

    def test_low_confidence_routes_to_human(self):
        router = ConfidenceRouter()
        from confidence_router import ConfidenceScore
        score = ConfidenceScore(0.3, 0.2, 0.3, 0.3, 0.3, 0.28)
        route = router.route(score, "no_show_charge", verification_passed=True)
        assert route == RouteDestination.HUMAN_REVIEW


class TestRefundEngine:
    def test_rider_fault_no_refund(self):
        pe = PolicyEngine()
        engine = RefundEngine(pe)
        result = engine.calculate("no_show_charge", {"rider_charge_sgd": 6.61}, "rider_fault")
        assert result.amount_sgd == 0.0

    def test_cancellation_voucher(self):
        pe = PolicyEngine()
        engine = RefundEngine(pe)
        result = engine.calculate("cancellation_fee", {"rider_charge_sgd": 6.61}, "no_fault")
        assert result.amount_sgd == 6.61  # CAN-07 voucher amount
        assert result.capped is True

    def test_cleaning_cap(self):
        pe = PolicyEngine()
        engine = RefundEngine(pe)
        result = engine.calculate("cleaning_fee", {
            "mess": "vomit",
            "verified_cleaning_cost_sgd": 260,
        }, "no_fault")
        assert result.amount_sgd == 200  # Capped at vomit cap
        assert result.capped is True


class TestDisputeResolver:
    def test_disp002_resolution(self):
        pe = PolicyEngine()
        resolver = DisputeResolver(pe)
        case = build_disp002_case()
        result = resolver.resolve(case)
        assert result.dispute_id == "DISP-002"
        assert len(result.stages) == 7
        assert result.final_assessment != ""
        # Both advocates agree → consensus → auto-resolve or challenge
        assert result.route in [RouteDestination.AUTO_RESOLVE.value, RouteDestination.CHALLENGE_WINDOW.value]

    def test_safety_case_escalates(self):
        pe = PolicyEngine()
        resolver = DisputeResolver(pe)
        case = build_safety_incident_case()
        result = resolver.resolve(case)
        assert result.route == RouteDestination.HUMAN_REVIEW.value
        assert result.human_review_required is True
        assert result.final_decision is False

    def test_cancellation_grace_inconsistent(self):
        pe = PolicyEngine()
        resolver = DisputeResolver(pe)
        case = build_cancellation_grace_case()
        result = resolver.resolve(case)
        assert result.final_assessment == Assessment.POLICY_INCONSISTENT.value
