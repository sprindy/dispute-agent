"""
Rider Advocate — builds the case from the rider's perspective.

Uses policy rules to check whether charges applied to the rider are
consistent with public policy. Cites evidence and policy IDs.
"""
from agents.base_agent import BaseAgent, AgentRole, AgentArgument
from config import Assessment, DisputeCategory
from evidence_collector import EvidenceStatus


class RiderAdvocate(BaseAgent):
    """
    The Rider Advocate examines whether charges or actions against the rider
    are supported by verified evidence and consistent with public policy.

    It advocates for the rider but does NOT fabricate facts (BR-02)
    and does NOT use history as independent liability (BR-06).
    """

    def __init__(self, policy_engine, evidence_collector_cls=None):
        super().__init__(AgentRole.RIDER_ADVOCATE, policy_engine, evidence_collector_cls)

    def assess(self, case) -> AgentArgument:
        category = case.category

        if category == DisputeCategory.NO_SHOW_CHARGE.value:
            return self._assess_no_show(case)
        elif category == DisputeCategory.CANCELLATION_FEE.value:
            return self._assess_cancellation(case)
        elif category == DisputeCategory.ROUTE_DEVIATION.value:
            return self._assess_route_deviation(case)
        elif category == DisputeCategory.WAITING_FEE.value:
            return self._assess_waiting_fee(case)
        elif category == DisputeCategory.FARE_DISPUTE.value:
            return self._assess_fare_dispute(case)
        else:
            return AgentArgument(
                agent_role=self.role,
                liability_label="insufficient_evidence",
                assessment=Assessment.INSUFFICIENT_EVIDENCE.value,
                rationale="Rider Advocate: no specific assessment logic for this category yet.",
                policy_ids=[],
                source_ids=[],
                evidence_ids=[e.evidence_id for e in case.evidence if e.is_available()],
                warnings=["Category not yet fully implemented for rider advocacy."],
            )

    def _assess_no_show(self, case) -> AgentArgument:
        """
        CAN-02: No-show requires arrival at booked pickup AND >3 min waiting.
        CAN-01: Cancellation within 3 min of matching is free.
        CAN-10: No mandatory call count or 8-min rule is published.
        """
        facts = case.facts
        policy_ids = ["CAN-01", "CAN-02", "CAN-06", "CAN-10"]
        warnings = self._check_conflicts(policy_ids)
        available_evidence = [e.evidence_id for e in case.evidence if e.is_available()]

        # Check key facts
        pickup_arrival = facts.get("pickup_arrival_verified")
        wait_seconds = facts.get("wait_seconds")
        match_to_cancel = facts.get("match_to_cancel_seconds")
        rider_charge = facts.get("rider_charge_sgd")

        # CAN-01: If cancellation within 3 min of matching, fee is inconsistent
        if match_to_cancel is not None and match_to_cancel <= 180:
            return AgentArgument(
                agent_role=self.role,
                liability_label="no_fault",
                assessment=Assessment.POLICY_INCONSISTENT.value,
                rationale=(
                    f"Rider cancelled within the three-minute matching grace period "
                    f"(match_to_cancel={match_to_cancel}s, grace=180s). "
                    f"Per CAN-01, cancellation within three minutes of matching is free. "
                    f"The {rider_charge} SGD charge should be flagged for review."
                ),
                policy_ids=policy_ids,
                source_ids=self._collect_source_ids(policy_ids),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.95, "evidence_strength": 0.80},
                requested_remedy="waiver_review",
                warnings=warnings,
            )

        # CAN-02: Check no-show conditions
        if pickup_arrival is False:
            return AgentArgument(
                agent_role=self.role,
                liability_label="driver_fault",
                assessment=Assessment.POLICY_INCONSISTENT.value,
                rationale=(
                    "No-show charging requires arrival at the booked pickup. "
                    "GPS or system records do not confirm driver arrival at the "
                    "booked pickup location. The no-show charge is not supported."
                ),
                policy_ids=["CAN-02"],
                source_ids=self._collect_source_ids(["CAN-02"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.90, "evidence_strength": 0.75},
                requested_remedy="charge_reversal",
                warnings=warnings,
            )

        if wait_seconds is not None and wait_seconds <= 180:
            return AgentArgument(
                agent_role=self.role,
                liability_label="no_fault",
                assessment=Assessment.POLICY_INCONSISTENT.value,
                rationale=(
                    f"Waiting time was {wait_seconds}s; CAN-02 requires "
                    f"strictly more than 180s (3 min) before a no-show charge. "
                    f"The charge does not meet the published threshold."
                ),
                policy_ids=["CAN-02"],
                source_ids=self._collect_source_ids(["CAN-02"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.90, "evidence_strength": 0.80},
                requested_remedy="charge_reversal",
                warnings=warnings,
            )

        # If arrival verified and wait > 3 min → charge is policy-consistent
        if pickup_arrival is True and wait_seconds is not None and wait_seconds > 180:
            return AgentArgument(
                agent_role=self.role,
                liability_label="rider_fault",
                assessment=Assessment.POLICY_CONSISTENT.value,
                rationale=(
                    f"Verified pickup arrival and {wait_seconds}s waiting exceed "
                    f"the three-minute no-show threshold (CAN-02). The no-show "
                    f"charge appears policy-consistent. Rider may still request "
                    f"a discretionary waiver under CAN-07."
                ),
                policy_ids=policy_ids + ["CAN-07"],
                source_ids=self._collect_source_ids(policy_ids + ["CAN-07"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.90, "evidence_strength": 0.85},
                requested_remedy="inform_rider_of_waiver_option",
                warnings=warnings,
            )

        # Missing evidence
        missing_fields = []
        if pickup_arrival is None:
            missing_fields.append("pickup_arrival_verified")
        if wait_seconds is None:
            missing_fields.append("wait_seconds")

        return AgentArgument(
            agent_role=self.role,
            liability_label="insufficient_evidence",
            assessment=Assessment.INSUFFICIENT_EVIDENCE.value,
            rationale=(
                f"Cannot determine no-show consistency — missing: {missing_fields}. "
                f"These facts must be retrieved from verified sources, not inferred."
            ),
            policy_ids=policy_ids,
            source_ids=self._collect_source_ids(policy_ids),
            evidence_ids=available_evidence,
            confidence_factors={"policy_clarity": 0.85, "evidence_strength": 0.30},
            warnings=warnings + [self._format_history_note(case)],
        )

    def _assess_cancellation(self, case) -> AgentArgument:
        """CAN-01, CAN-04, CAN-05, CAN-06: Cancellation grace and advance rules."""
        facts = case.facts
        policy_ids = ["CAN-01", "CAN-04", "CAN-05", "CAN-06"]
        warnings = self._check_conflicts(policy_ids)
        available_evidence = [e.evidence_id for e in case.evidence if e.is_available()]

        match_to_cancel = facts.get("match_to_cancel_seconds")
        seconds_before_schedule = facts.get("seconds_before_schedule_at_cancel")

        # CAN-04: Advance cancellation > 15 min before pickup = free
        if seconds_before_schedule is not None and seconds_before_schedule > 900:
            return AgentArgument(
                agent_role=self.role,
                liability_label="no_fault",
                assessment=Assessment.POLICY_INCONSISTENT.value,
                rationale=(
                    f"Advance cancellation {seconds_before_schedule}s before scheduled "
                    f"pickup exceeds the 900s (15 min) free threshold (CAN-04). "
                    f"The charge is inconsistent with public policy."
                ),
                policy_ids=["CAN-04"],
                source_ids=self._collect_source_ids(["CAN-04"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.90, "evidence_strength": 0.80},
                requested_remedy="charge_reversal",
                warnings=warnings,
            )

        # CAN-01: On-demand grace within 3 min
        if match_to_cancel is not None and match_to_cancel <= 180:
            return AgentArgument(
                agent_role=self.role,
                liability_label="no_fault",
                assessment=Assessment.POLICY_INCONSISTENT.value,
                rationale=(
                    f"Cancellation at {match_to_cancel}s after matching is within the "
                    f"three-minute grace period (CAN-01). The charge should be flagged."
                ),
                policy_ids=["CAN-01"],
                source_ids=self._collect_source_ids(["CAN-01"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.95, "evidence_strength": 0.80},
                requested_remedy="charge_reversal",
                warnings=warnings,
            )

        return AgentArgument(
            agent_role=self.role,
            liability_label="insufficient_evidence",
            assessment=Assessment.INSUFFICIENT_EVIDENCE.value,
            rationale="Missing timing data to assess cancellation consistency.",
            policy_ids=policy_ids,
            source_ids=self._collect_source_ids(policy_ids),
            evidence_ids=available_evidence,
            confidence_factors={"policy_clarity": 0.80, "evidence_strength": 0.30},
            warnings=warnings,
        )

    def _assess_route_deviation(self, case) -> AgentArgument:
        """FARE-01: No published percentage refund formula; don't invent one."""
        facts = case.facts
        policy_ids = ["FARE-01", "FARE-02"]
        warnings = self._check_conflicts(policy_ids)
        available_evidence = [e.evidence_id for e in case.evidence if e.is_available()]

        route_increase = facts.get("route_distance_increase_pct")
        requested_refund = facts.get("requested_refund_pct")
        base_fare_charged = facts.get("base_fare_charged_sgd")
        quoted_fare = facts.get("quoted_fare_sgd")

        if base_fare_charged is not None and quoted_fare is not None and base_fare_charged > quoted_fare:
            return AgentArgument(
                agent_role=self.role,
                liability_label="driver_fault",
                assessment=Assessment.POLICY_INCONSISTENT.value,
                rationale=(
                    f"Quoted fare was {quoted_fare} SGD but charged {base_fare_charged} SGD. "
                    f"FARE-02 states fares are generally fixed. An unexplained increase "
                    f"requires investigation and receipt breakdown."
                ),
                policy_ids=["FARE-02"],
                source_ids=self._collect_source_ids(["FARE-02"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.90, "evidence_strength": 0.85},
                requested_remedy="fare_review",
                warnings=warnings,
            )

        if requested_refund is not None and requested_refund > 0:
            return AgentArgument(
                agent_role=self.role,
                liability_label="no_fault",
                assessment=Assessment.UNSUPPORTED_RULE.value,
                rationale=(
                    f"Rider requests {requested_refund}% refund for a {route_increase}% "
                    f"route increase. No public percentage-based route refund formula "
                    f"is published (FARE-01). Review route choice and rider agreement "
                    f"without inventing a discount."
                ),
                policy_ids=["FARE-01"],
                source_ids=self._collect_source_ids(["FARE-01"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.85, "evidence_strength": 0.70},
                warnings=warnings,
            )

        return AgentArgument(
            agent_role=self.role,
            liability_label="insufficient_evidence",
            assessment=Assessment.INSUFFICIENT_EVIDENCE.value,
            rationale="Insufficient fare data to assess route deviation claim.",
            policy_ids=policy_ids,
            source_ids=self._collect_source_ids(policy_ids),
            evidence_ids=available_evidence,
            confidence_factors={"policy_clarity": 0.80, "evidence_strength": 0.30},
            warnings=warnings,
        )

    def _assess_waiting_fee(self, case) -> AgentArgument:
        """CAN-03: Completed trip waiting fee after >3 min."""
        facts = case.facts
        policy_ids = ["CAN-03"]
        warnings = self._check_conflicts(policy_ids)
        available_evidence = [e.evidence_id for e in case.evidence if e.is_available()]

        wait_seconds = facts.get("wait_seconds")
        trip_completed = facts.get("trip_completed")
        rider_charge = facts.get("rider_charge_sgd")

        if wait_seconds is not None and wait_seconds <= 180:
            return AgentArgument(
                agent_role=self.role,
                liability_label="no_fault",
                assessment=Assessment.POLICY_INCONSISTENT.value,
                rationale=(
                    f"Waiting time {wait_seconds}s does not exceed the three-minute "
                    f"threshold (CAN-03). The {rider_charge} SGD waiting fee is inconsistent."
                ),
                policy_ids=policy_ids,
                source_ids=self._collect_source_ids(policy_ids),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.90, "evidence_strength": 0.80},
                requested_remedy="charge_review",
                warnings=warnings,
            )

        return AgentArgument(
            agent_role=self.role,
            liability_label="insufficient_evidence",
            assessment=Assessment.INSUFFICIENT_EVIDENCE.value,
            rationale="Insufficient waiting data to assess fee consistency.",
            policy_ids=policy_ids,
            source_ids=self._collect_source_ids(policy_ids),
            evidence_ids=available_evidence,
            confidence_factors={"policy_clarity": 0.85, "evidence_strength": 0.30},
            warnings=warnings,
        )

    def _assess_fare_dispute(self, case) -> AgentArgument:
        """FARE-10, FARE-11, FARE-14: Platform fee, processing fee, support fee."""
        facts = case.facts
        policy_ids = ["FARE-02", "FARE-10", "FARE-11", "FARE-14"]
        warnings = self._check_conflicts(policy_ids)
        available_evidence = [e.evidence_id for e in case.evidence if e.is_available()]

        payment = facts.get("payment")
        processing_fee = facts.get("processing_fee_sgd")

        # FARE-11: Cash payments should not have processing fee
        if payment == "cash" and processing_fee is not None and processing_fee > 0:
            return AgentArgument(
                agent_role=self.role,
                liability_label="driver_fault",
                assessment=Assessment.POLICY_INCONSISTENT.value,
                rationale=(
                    f"Cash payment carries a {processing_fee} SGD processing fee. "
                    f"FARE-11 states cashless transactions have a processing fee; "
                    f"cash payments do not. This charge is inconsistent."
                ),
                policy_ids=["FARE-11"],
                source_ids=self._collect_source_ids(["FARE-11"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.95, "evidence_strength": 0.90},
                requested_remedy="fee_reversal",
                warnings=warnings,
            )

        # FARE-10: Platform fee tier check
        fare = facts.get("fare_sgd")
        platform_fee = facts.get("platform_fee_sgd")
        if fare is not None and platform_fee is not None:
            expected_fee = 1.25 if fare <= 18 else 1.47
            if abs(platform_fee - expected_fee) > 0.01:
                return AgentArgument(
                    agent_role=self.role,
                    liability_label="driver_fault",
                    assessment=Assessment.POLICY_INCONSISTENT.value,
                    rationale=(
                        f"Fare {fare} SGD with platform fee {platform_fee} SGD. "
                        f"Expected {expected_fee} SGD (FARE-10 tier). "
                        f"The platform fee is inconsistent with the published tier."
                    ),
                    policy_ids=["FARE-10"],
                    source_ids=self._collect_source_ids(["FARE-10"]),
                    evidence_ids=available_evidence,
                    confidence_factors={"policy_clarity": 0.95, "evidence_strength": 0.90},
                    requested_remedy="fee_correction",
                    warnings=warnings,
                )

        return AgentArgument(
            agent_role=self.role,
            liability_label="insufficient_evidence",
            assessment=Assessment.INSUFFICIENT_EVIDENCE.value,
            rationale="Insufficient fare data to assess the dispute.",
            policy_ids=policy_ids,
            source_ids=self._collect_source_ids(policy_ids),
            evidence_ids=available_evidence,
            confidence_factors={"policy_clarity": 0.80, "evidence_strength": 0.30},
            warnings=warnings,
        )

    def _collect_source_ids(self, policy_ids: list[str]) -> list[str]:
        result = []
        for pid in policy_ids:
            rule = self.policy_engine.get_rule(pid)
            if rule:
                for sid in rule.source_ids:
                    if sid not in result:
                        result.append(sid)
        return result
