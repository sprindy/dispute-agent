"""
Refund Engine — deterministic refund/compensation calculator.

Implements BR-07: LLM does not compute refund amounts.
The Refund Engine uses verified financial data and machine-readable policy
parameters to compute amounts deterministically.
"""
from dataclasses import dataclass
from typing import Optional
from policy_engine import PolicyEngine


@dataclass
class RefundResult:
    """Result of a refund calculation."""
    amount_sgd: float
    currency: str = "SGD"
    policy_id: str = ""
    calculation_basis: str = ""
    capped: bool = False
    notes: list[str] = None

    def to_dict(self) -> dict:
        return {
            "amount_sgd": round(self.amount_sgd, 2),
            "currency": self.currency,
            "policy_id": self.policy_id,
            "calculation_basis": self.calculation_basis,
            "capped": self.capped,
            "notes": self.notes or [],
        }


class RefundEngine:
    """
    Computes refund/compensation amounts from verified data and policy parameters.
    This is the ONLY component that produces monetary amounts.
    """

    def __init__(self, policy_engine: PolicyEngine):
        self.policy_engine = policy_engine

    def calculate(
        self,
        category: str,
        verified_facts: dict,
        liability_label: str,
    ) -> Optional[RefundResult]:
        """
        Calculate refund based on dispute category, verified facts, and liability.

        Only produces amounts when liability favors the rider (rider is not at fault).
        """
        # No refund if rider is at fault
        if liability_label in ("rider_fault", "safety_escalation"):
            return RefundResult(
                amount_sgd=0.0,
                policy_id="",
                calculation_basis="Rider at fault or safety escalation — no refund.",
                notes=["Liability does not support a refund."],
            )

        # No refund if insufficient evidence
        if liability_label in ("insufficient_evidence", "contested", "source_conflict",
                                "policy_gap", "discretionary_review"):
            return RefundResult(
                amount_sgd=0.0,
                policy_id="",
                calculation_basis="Insufficient evidence or requires human review.",
                notes=["No auto-refund; case requires human determination."],
            )

        # Category-specific calculations
        if category == "no_show_charge" or category == "cancellation_fee":
            return self._calc_cancellation_refund(verified_facts)
        elif category == "waiting_fee":
            return self._calc_waiting_fee_refund(verified_facts)
        elif category == "cleaning_fee":
            return self._calc_cleaning_refund(verified_facts)
        elif category == "fare_dispute":
            return self._calc_fare_refund(verified_facts)
        else:
            return RefundResult(
                amount_sgd=0.0,
                calculation_basis="No deterministic refund rule for this category.",
                notes=["Manual review required for refund determination."],
            )

    def _calc_cancellation_refund(self, facts: dict) -> RefundResult:
        """
        Cancellation/no-show refund = verified charge reversal.
        CAN-07: Approved relief is a voucher (SGD 6.61), not guaranteed cash.
        """
        charge = facts.get("rider_charge_sgd")
        if charge is None:
            return RefundResult(
                amount_sgd=0.0,
                policy_id="CAN-07",
                calculation_basis="No verified charge amount available.",
                notes=["Cannot compute refund without verified charge amount."],
            )

        rule = self.policy_engine.get_rule("CAN-07")
        voucher_amount = rule.parameters.get("approved_voucher_sgd", 6.61) if rule else 6.61

        return RefundResult(
            amount_sgd=voucher_amount,
            policy_id="CAN-07",
            calculation_basis=(
                f"Verified charge: {charge} SGD. "
                f"CAN-07: approved relief is a non-cash voucher of {voucher_amount} SGD. "
                f"Voucher, not guaranteed cash refund. Subject to waiver review."
            ),
            capped=True,
            notes=[
                "Relief is a voucher, not cash (CAN-07).",
                "Must be filed within 30 days.",
                "Subject to discretionary approval.",
            ],
        )

    def _calc_waiting_fee_refund(self, facts: dict) -> RefundResult:
        """
        CAN-08: Waiting-fee waiver approved relief is a non-cash voucher.
        """
        rule = self.policy_engine.get_rule("CAN-08")
        voucher_amount = rule.parameters.get("approved_voucher_sgd", 5.0) if rule else 5.0

        return RefundResult(
            amount_sgd=voucher_amount,
            policy_id="CAN-08",
            calculation_basis=(
                f"CAN-08: approved waiting-fee waiver relief is a {voucher_amount} SGD voucher. "
                f"Non-cash voucher, subject to review."
            ),
            capped=True,
            notes=[
                "Relief is a voucher, not cash (CAN-08).",
                "Must be filed within 30 days.",
            ],
        )

    def _calc_cleaning_refund(self, facts: dict) -> RefundResult:
        """
        CLEAN-01: Severity caps apply. Caps are ceilings, not guaranteed awards.
        """
        rule = self.policy_engine.get_rule("CLEAN-01")
        if not rule:
            return RefundResult(amount_sgd=0.0, notes=["CLEAN-01 not found."])

        mess = facts.get("mess", "")
        verified_cost = facts.get("verified_cleaning_cost_sgd", 0)

        caps = {
            "spillage": rule.parameters.get("spillage_cap_sgd", 40),
            "bodily_fluid_stain": rule.parameters.get("fluids_stains_cap_sgd", 120),
            "vomit": rule.parameters.get("vomit_cap_sgd", 200),
        }
        cap = caps.get(mess)
        if cap is None:
            return RefundResult(
                amount_sgd=0.0,
                policy_id="CLEAN-01",
                calculation_basis=f"Unknown mess type: {mess}.",
                notes=["Cannot determine cap for this mess type."],
            )

        amount = min(verified_cost, cap)
        return RefundResult(
            amount_sgd=amount,
            policy_id="CLEAN-01",
            calculation_basis=(
                f"Verified cost: {verified_cost} SGD. "
                f"{mess} cap: {cap} SGD. "
                f"Reimbursement capped at min(cost, cap) = {amount} SGD. "
                f"Subject to eligibility review."
            ),
            capped=verified_cost > cap,
            notes=[
                "Caps are ceilings, not guaranteed awards (CLEAN-01).",
                "Subject to Ryde review and eligibility verification.",
            ],
        )

    def _calc_fare_refund(self, facts: dict) -> RefundResult:
        """
        Fare dispute: refund = overcharged amount (verified).
        No percentage-based formula (FARE-01).
        """
        quoted = facts.get("quoted_fare_sgd")
        charged = facts.get("base_fare_charged_sgd")

        if quoted is None or charged is None:
            return RefundResult(
                amount_sgd=0.0,
                policy_id="FARE-02",
                calculation_basis="Cannot compute without verified quoted and charged fares.",
                notes=["Need both quoted and charged amounts."],
            )

        overcharge = max(charged - quoted, 0)
        return RefundResult(
            amount_sgd=overcharge,
            policy_id="FARE-02",
            calculation_basis=(
                f"Quoted: {quoted} SGD. Charged: {charged} SGD. "
                f"Overcharge = max({charged} - {quoted}, 0) = {overcharge} SGD."
            ),
            capped=False,
            notes=["Refund equals verified overcharge amount."],
        )
