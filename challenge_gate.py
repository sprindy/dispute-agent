"""
Challenge Gate — evaluates challenge admissibility and debate triggers.

Implements:
- BR-04: Both parties get equal challenge standards and time limits
- BR-05: Frivolous challenges (no substance) don't trigger deep debate
- BR-08: Valid unresolved challenge triggers adaptive debate
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta
from config import CHALLENGE_WINDOW_HOURS, MAX_DEBATE_ROUNDS


@dataclass
class Challenge:
    """A challenge submitted by a party against a preliminary ruling."""
    challenger: str  # "rider" or "driver"
    submitted_at: datetime
    challenge_reason: str
    new_evidence_ids: list[str] = None
    factual_error_claimed: str = ""
    policy_error_claimed: str = ""


@dataclass
class ChallengeResult:
    """Result of evaluating a challenge."""
    admissible: bool
    reason: str
    triggers_debate: bool
    is_frivolous: bool = False


class ChallengeGate:
    """
    Evaluates whether a challenge is admissible and whether it triggers debate.

    A valid challenge must contain:
    - New substantive evidence, OR
    - A specific factual error claim, OR
    - A policy/policy-application error claim

    A simple "I disagree" is NOT admissible (BR-05).
    """

    def __init__(self, challenge_window_hours: int = CHALLENGE_WINDOW_HOURS):
        self.challenge_window_hours = challenge_window_hours

    def is_within_window(self, challenge: Challenge, ruling_issued_at: datetime) -> bool:
        """Check if the challenge was submitted within the time window."""
        deadline = ruling_issued_at + timedelta(hours=self.challenge_window_hours)
        return challenge.submitted_at <= deadline

    def evaluate(self, challenge: Challenge, ruling_issued_at: datetime) -> ChallengeResult:
        """Evaluate whether a challenge is admissible and triggers debate."""
        # 1. Time window check (BR-04: equal standards for both parties)
        if not self.is_within_window(challenge, ruling_issued_at):
            return ChallengeResult(
                admissible=False,
                reason=f"Challenge submitted outside the {self.challenge_window_hours}h window.",
                triggers_debate=False,
                is_frivolous=False,
            )

        # 2. Substance check (BR-05: no frivolous challenges)
        has_new_evidence = bool(challenge.new_evidence_ids)
        has_factual_error = bool(challenge.factual_error_claimed.strip())
        has_policy_error = bool(challenge.policy_error_claimed.strip())

        if not (has_new_evidence or has_factual_error or has_policy_error):
            return ChallengeResult(
                admissible=False,
                reason=(
                    "Challenge lacks substance: no new evidence, factual error, "
                    "or policy error claimed. 'I disagree' is not sufficient (BR-05)."
                ),
                triggers_debate=False,
                is_frivolous=True,
            )

        # 3. Admissible — triggers debate (BR-08)
        substance_parts = []
        if has_new_evidence:
            substance_parts.append(f"new evidence: {challenge.new_evidence_ids}")
        if has_factual_error:
            substance_parts.append(f"factual error: {challenge.factual_error_claimed}")
        if has_policy_error:
            substance_parts.append(f"policy error: {challenge.policy_error_claimed}")

        return ChallengeResult(
            admissible=True,
            reason=f"Valid challenge with {'; '.join(substance_parts)}. Triggers re-evaluation.",
            triggers_debate=True,
            is_frivolous=False,
        )

    def can_continue_debate(self, current_round: int) -> bool:
        """Check if more debate rounds are allowed."""
        return current_round < MAX_DEBATE_ROUNDS
