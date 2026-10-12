"""
Driver Advocate — builds the case from the driver's perspective.

Checks whether the driver followed policy, whether evidence supports
the driver's position, and whether charges are correctly applied.
"""
from agents.base_agent import BaseAgent, AgentRole, AgentArgument
from config import Assessment, DisputeCategory


class DriverAdvocate(BaseAgent):
    """
    The Driver Advocate examines whether the driver acted consistently
    with public policy and whether the evidence supports the driver's position.
    """

    def __init__(self, policy_engine, evidence_collector_cls=None):
        super().__init__(AgentRole.DRIVER_ADVOCATE, policy_engine, evidence_collector_cls)

    def assess(self, case) -> AgentArgument:
        category = case.category

        if category == DisputeCategory.NO_SHOW_CHARGE.value:
            return self._assess_no_show(case)
        elif category == DisputeCategory.CANCELLATION_FEE.value:
            return self._assess_cancellation(case)
        elif category == DisputeCategory.ROUTE_DEVIATION.value:
            return self._assess_route_deviation(case)
        elif category == DisputeCategory.FARE_DISPUTE.value:
            return self._assess_fare_dispute(case)
        elif category == DisputeCategory.CLEANING_FEE.value:
            return self._assess_cleaning_fee(case)
        elif category == DisputeCategory.SAFETY_INCIDENT.value:
            return self._assess_safety(case)
        else:
            return AgentArgument(
                agent_role=self.role,
                liability_label="insufficient_evidence",
                assessment=Assessment.INSUFFICIENT_EVIDENCE.value,
                rationale="Driver Advocate: no specific assessment logic for this category.",
                policy_ids=[],
                source_ids=[],
                evidence_ids=[e.evidence_id for e in case.evidence if e.is_available()],
                warnings=["Category not yet fully implemented for driver advocacy."],
            )

    def _assess_no_show(self, case) -> AgentArgument:
        """
        CAN-02: Driver arrived at pickup, waited >3 min → no-show charge is consistent.
        CAN-09: Driver payment ($4.50) ≠ rider charge ($6.61) — different roles.
        CAN-10: In-app contact is guidance, not a mandatory fee prerequisite.
        """
        facts = case.facts
        policy_ids = ["CAN-02", "CAN-09", "CAN-10"]
        warnings = self._check_conflicts(policy_ids)
        available_evidence = [e.evidence_id for e in case.evidence if e.is_available()]

        pickup_arrival = facts.get("pickup_arrival_verified")
        wait_seconds = facts.get("wait_seconds")
        rider_charge = facts.get("rider_charge_sgd")
        driver_payment = facts.get("driver_payment_sgd")

        # CAN-09: Different amounts for rider vs driver
        if rider_charge is not None and driver_payment is not None and rider_charge != driver_payment:
            warnings.append(
                f"CAN-09: Rider charge ({rider_charge} SGD) and driver payment "
                f"({driver_payment} SGD) are different roles; this alone is not overcharging."
            )

        # CAN-02: Check no-show conditions
        if pickup_arrival is True and wait_seconds is not None and wait_seconds > 180:
            return AgentArgument(
                agent_role=self.role,
                liability_label="rider_fault",
                assessment=Assessment.POLICY_CONSISTENT.value,
                rationale=(
                    f"Driver verified arrival at booked pickup and waited {wait_seconds}s "
                    f"(>180s threshold per CAN-02). The no-show charge is policy-consistent. "
                    f"Driver attempted in-app contact per CAN-10 guidance."
                ),
                policy_ids=policy_ids,
                source_ids=self._collect_source_ids(policy_ids),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.90, "evidence_strength": 0.85},
                warnings=warnings + [self._format_history_note(case)],
            )

        # Arrival not verified
        if pickup_arrival is False:
            return AgentArgument(
                agent_role=self.role,
                liability_label="insufficient_evidence",
                assessment=Assessment.POLICY_INCONSISTENT.value,
                rationale=(
                    "Driver arrival at the booked pickup cannot be verified. "
                    "The no-show charge requires verified arrival (CAN-02). "
                    "Driver should provide GPS evidence of arrival."
                ),
                policy_ids=["CAN-02"],
                source_ids=self._collect_source_ids(["CAN-02"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.90, "evidence_strength": 0.40},
                warnings=warnings,
            )

        # Missing
        return AgentArgument(
            agent_role=self.role,
            liability_label="insufficient_evidence",
            assessment=Assessment.INSUFFICIENT_EVIDENCE.value,
            rationale="Missing arrival or wait data to verify no-show conditions.",
            policy_ids=policy_ids,
            source_ids=self._collect_source_ids(policy_ids),
            evidence_ids=available_evidence,
            confidence_factors={"policy_clarity": 0.85, "evidence_strength": 0.30},
            warnings=warnings,
        )

    def _assess_cancellation(self, case) -> AgentArgument:
        """Driver's view: charge is consistent if timing conditions are met."""
        facts = case.facts
        policy_ids = ["CAN-01", "CAN-04", "CAN-09"]
        warnings = self._check_conflicts(policy_ids)
        available_evidence = [e.evidence_id for e in case.evidence if e.is_available()]

        match_to_cancel = facts.get("match_to_cancel_seconds")
        seconds_before_schedule = facts.get("seconds_before_schedule_at_cancel")

        # CAN-01: If within grace, charge is inconsistent (driver agrees with policy)
        if match_to_cancel is not None and match_to_cancel <= 180:
            return AgentArgument(
                agent_role=self.role,
                liability_label="no_fault",
                assessment=Assessment.POLICY_INCONSISTENT.value,
                rationale=(
                    f"Rider cancelled {match_to_cancel}s after matching, within the "
                    f"three-minute grace period (CAN-01). The cancellation charge "
                    f"is inconsistent with public policy."
                ),
                policy_ids=["CAN-01"],
                source_ids=self._collect_source_ids(["CAN-01"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.95, "evidence_strength": 0.85},
                warnings=warnings,
            )

        if match_to_cancel is not None and match_to_cancel > 180:
            return AgentArgument(
                agent_role=self.role,
                liability_label="rider_fault",
                assessment=Assessment.POLICY_CONSISTENT.value,
                rationale=(
                    f"Rider cancelled {match_to_cancel}s after matching, beyond the "
                    f"three-minute grace (CAN-01). The cancellation charge is consistent."
                ),
                policy_ids=["CAN-01"],
                source_ids=self._collect_source_ids(["CAN-01"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.95, "evidence_strength": 0.85},
                warnings=warnings,
            )

        if seconds_before_schedule is not None and seconds_before_schedule > 900:
            return AgentArgument(
                agent_role=self.role,
                liability_label="no_fault",
                assessment=Assessment.POLICY_INCONSISTENT.value,
                rationale=(
                    f"Rider cancelled {seconds_before_schedule}s before scheduled pickup "
                    f"(>900s/15min). CAN-04 states this is free. Charge should be reviewed."
                ),
                policy_ids=["CAN-04"],
                source_ids=self._collect_source_ids(["CAN-04"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.90, "evidence_strength": 0.80},
                warnings=warnings,
            )

        return AgentArgument(
            agent_role=self.role,
            liability_label="insufficient_evidence",
            assessment=Assessment.INSUFFICIENT_EVIDENCE.value,
            rationale="Missing timing data to assess cancellation.",
            policy_ids=policy_ids,
            source_ids=self._collect_source_ids(policy_ids),
            evidence_ids=available_evidence,
            confidence_factors={"policy_clarity": 0.80, "evidence_strength": 0.30},
            warnings=warnings,
        )

    def _assess_route_deviation(self, case) -> AgentArgument:
        """FARE-01: Drivers can choose efficient GPS route; no percentage refund."""
        facts = case.facts
        policy_ids = ["FARE-01", "FARE-02"]
        warnings = self._check_conflicts(policy_ids)
        available_evidence = [e.evidence_id for e in case.evidence if e.is_available()]

        return AgentArgument(
            agent_role=self.role,
            liability_label="no_fault",
            assessment=Assessment.UNSUPPORTED_RULE.value,
            rationale=(
                "FARE-01 allows the driver to choose an efficient GPS route. "
                "No public percentage-based refund formula exists. "
                "The route deviation claim cannot be resolved by a formula; "
                "review actual route choice and any rider agreement."
            ),
            policy_ids=policy_ids,
            source_ids=self._collect_source_ids(policy_ids),
            evidence_ids=available_evidence,
            confidence_factors={"policy_clarity": 0.85, "evidence_strength": 0.65},
            warnings=warnings,
        )

    def _assess_cleaning_fee(self, case) -> AgentArgument:
        """CLEAN-01 to CLEAN-06: Cleaning claim validation."""
        facts = case.facts
        policy_ids = ["CLEAN-01", "CLEAN-02", "CLEAN-03", "CLEAN-04"]
        warnings = self._check_conflicts(policy_ids)
        available_evidence = [e.evidence_id for e in case.evidence if e.is_available()]

        mess = facts.get("mess")
        cost = facts.get("verified_cleaning_cost_sgd")
        cleaning_delay = facts.get("professional_cleaning_delay_hours")
        claim_delay = facts.get("claim_delay_hours")
        receipt_stamp = facts.get("receipt_stamp_present")

        # CLEAN-02: Timing checks
        if cleaning_delay is not None and cleaning_delay > 24:
            return AgentArgument(
                agent_role=self.role,
                liability_label="insufficient_evidence",
                assessment=Assessment.POLICY_INCONSISTENT.value,
                rationale=(
                    f"Professional cleaning delay {cleaning_delay}h exceeds the 24h "
                    f"limit (CLEAN-02). The claim may not be eligible."
                ),
                policy_ids=["CLEAN-02"],
                source_ids=self._collect_source_ids(["CLEAN-02"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.90, "evidence_strength": 0.70},
                warnings=warnings,
            )

        # CLEAN-03: Evidence requirements
        if receipt_stamp is False:
            return AgentArgument(
                agent_role=self.role,
                liability_label="insufficient_evidence",
                assessment=Assessment.INSUFFICIENT_EVIDENCE.value,
                rationale=(
                    "Cleaning receipt lacks the required company stamp (CLEAN-03). "
                    "Request complete supporting documents."
                ),
                policy_ids=["CLEAN-03"],
                source_ids=self._collect_source_ids(["CLEAN-03"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.90, "evidence_strength": 0.50},
                warnings=warnings,
            )

        # CLEAN-01: Cap check
        if mess and cost is not None:
            params = self._get_policy_params("CLEAN-01")
            caps = {
                "spillage": params.get("spillage_cap_sgd", 40),
                "bodily_fluid_stain": params.get("fluids_stains_cap_sgd", 120),
                "vomit": params.get("vomit_cap_sgd", 200),
            }
            cap = caps.get(mess)
            if cap and cost > cap:
                return AgentArgument(
                    agent_role=self.role,
                    liability_label="no_fault",
                    assessment=Assessment.DISCRETIONARY_REVIEW.value,
                    rationale=(
                        f"Cleaning cost {cost} SGD exceeds the {mess} cap of {cap} SGD "
                        f"(CLEAN-01). Caps are not guaranteed awards; subject to review."
                    ),
                    policy_ids=["CLEAN-01"],
                    source_ids=self._collect_source_ids(["CLEAN-01"]),
                    evidence_ids=available_evidence,
                    confidence_factors={"policy_clarity": 0.85, "evidence_strength": 0.75},
                    warnings=warnings,
                )

        # CLEAN-04: Excluded mess types
        excluded = ["immediately_cleanable_mess", "pet_fur", "pet_saliva"]
        if mess in excluded:
            return AgentArgument(
                agent_role=self.role,
                liability_label="no_fault",
                assessment=Assessment.POLICY_INCONSISTENT.value,
                rationale=(
                    f"Mess type '{mess}' is excluded from reimbursement (CLEAN-04). "
                    f"A cleaning bill alone does not establish eligibility."
                ),
                policy_ids=["CLEAN-04"],
                source_ids=self._collect_source_ids(["CLEAN-04"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.90, "evidence_strength": 0.80},
                warnings=warnings,
            )

        return AgentArgument(
            agent_role=self.role,
            liability_label="insufficient_evidence",
            assessment=Assessment.INSUFFICIENT_EVIDENCE.value,
            rationale="Insufficient cleaning claim data to assess.",
            policy_ids=policy_ids,
            source_ids=self._collect_source_ids(policy_ids),
            evidence_ids=available_evidence,
            confidence_factors={"policy_clarity": 0.80, "evidence_strength": 0.30},
            warnings=warnings,
        )

    def _assess_fare_dispute(self, case) -> AgentArgument:
        """FARE-11: Cash payments do not have processing fees; FARE-10: platform fee tiers."""
        facts = case.facts
        policy_ids = ["FARE-02", "FARE-10", "FARE-11"]
        warnings = self._check_conflicts(policy_ids)
        available_evidence = [e.evidence_id for e in case.evidence if e.is_available()]

        payment = facts.get("payment")
        processing_fee = facts.get("processing_fee_sgd")

        # FARE-11: Cash + processing fee = inconsistent (driver should acknowledge)
        if payment == "cash" and processing_fee is not None and processing_fee > 0:
            return AgentArgument(
                agent_role=self.role,
                liability_label="driver_fault",
                assessment=Assessment.POLICY_INCONSISTENT.value,
                rationale=(
                    f"Cash payment carries a {processing_fee} SGD processing fee. "
                    f"FARE-11: cashless transactions have a processing fee; "
                    f"cash payments do not. The charge is inconsistent."
                ),
                policy_ids=["FARE-11"],
                source_ids=self._collect_source_ids(["FARE-11"]),
                evidence_ids=available_evidence,
                confidence_factors={"policy_clarity": 0.95, "evidence_strength": 0.90},
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

    def _assess_safety(self, case) -> AgentArgument:
        """Safety cases always escalate — never auto-resolve."""
        policy_ids = ["SAFE-01", "SAFE-03", "SAFE-07"]
        available_evidence = [e.evidence_id for e in case.evidence if e.is_available()]

        return AgentArgument(
            agent_role=self.role,
            liability_label="insufficient_evidence",
            assessment=Assessment.SAFETY_ESCALATION.value,
            rationale=(
                "Safety allegations require immediate human review. "
                "The system escalates without inferring guilt or imposing sanctions. "
                "Evidence must be preserved and investigated."
            ),
            policy_ids=policy_ids,
            source_ids=self._collect_source_ids(policy_ids),
            evidence_ids=available_evidence,
            confidence_factors={"policy_clarity": 0.95, "evidence_strength": 0.40},
            warnings=["SAFETY ESCALATION: Do not auto-resolve. Preserve evidence."],
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
