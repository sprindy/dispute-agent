"""
Configuration & constants for the Ryde Dispute Resolution Agent.

Policy data is loaded from the repository's data/ryde_public_policy_v1/ snapshot.
All paths are resolved relative to the repo root.
"""
import os
from pathlib import Path
from enum import Enum

# --- Paths ---
REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_DIR = REPO_ROOT / "data" / "ryde_public_policy_v1"
POLICIES_FILE = POLICY_DIR / "policies.json"
CONFLICTS_FILE = POLICY_DIR / "policy_conflicts.json"
SCENARIO_SPECS_FILE = POLICY_DIR / "scenario_specs.json"
SOURCES_FILE = POLICY_DIR / "sources.json"
TRAIN_FILE = POLICY_DIR / "train.jsonl"

# --- Policy snapshot ---
POLICY_SNAPSHOT_ID = "RYDE-PUBLIC-2026-10-08-v1"

# --- Dispute categories ---
class DisputeCategory(str, Enum):
    NO_SHOW_CHARGE = "no_show_charge"
    ROUTE_DEVIATION = "route_deviation"
    CANCELLATION_FEE = "cancellation_fee"
    WAITING_FEE = "waiting_fee"
    CLEANING_FEE = "cleaning_fee"
    FARE_DISPUTE = "fare_dispute"
    SAFETY_INCIDENT = "safety_incident"

# Map dispute categories to relevant policy IDs
CATEGORY_POLICY_MAP = {
    DisputeCategory.NO_SHOW_CHARGE: ["CAN-01", "CAN-02", "CAN-06", "CAN-07", "CAN-09", "CAN-10"],
    DisputeCategory.ROUTE_DEVIATION: ["FARE-01", "FARE-02", "FARE-08", "FARE-09"],
    DisputeCategory.CANCELLATION_FEE: ["CAN-01", "CAN-04", "CAN-05", "CAN-06", "CAN-07", "CAN-09"],
    DisputeCategory.WAITING_FEE: ["CAN-03", "CAN-08"],
    DisputeCategory.CLEANING_FEE: ["CLEAN-01", "CLEAN-02", "CLEAN-03", "CLEAN-04", "CLEAN-05", "CLEAN-06"],
    DisputeCategory.FARE_DISPUTE: ["FARE-02", "FARE-03", "FARE-04", "FARE-10", "FARE-11", "FARE-12", "FARE-14"],
    DisputeCategory.SAFETY_INCIDENT: ["SAFE-01", "SAFE-02", "SAFE-03", "SAFE-04", "SAFE-07", "SAFE-08"],
}

# --- Assessment labels (from case.schema.json) ---
class Assessment(str, Enum):
    POLICY_CONSISTENT = "policy_consistent"
    POLICY_INCONSISTENT = "policy_inconsistent"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    SOURCE_CONFLICT = "source_conflict"
    POLICY_GAP = "policy_gap"
    DISCRETIONARY_REVIEW = "discretionary_review"
    UNSUPPORTED_RULE = "unsupported_rule"
    NOT_APPLICABLE = "not_applicable"
    SAFETY_ESCALATION = "safety_escalation"

# --- Confidence & routing thresholds (Demo prototypes from Vision 4) ---
# Confidence = 0.30*P + 0.35*E + 0.15*C + 0.10*A + 0.10*R
CONFIDENCE_WEIGHTS = {
    "policy_clarity": 0.30,
    "evidence_strength": 0.35,
    "historical_consistency": 0.15,
    "agent_consistency": 0.10,
    "claim_reliability": 0.10,
}

HIGH_CONFIDENCE_THRESHOLD = 0.75
LOW_CONFIDENCE_THRESHOLD = 0.45
HIGH_RISK_CATEGORIES = {DisputeCategory.SAFETY_INCIDENT}

# --- Challenge window ---
CHALLENGE_WINDOW_HOURS = 48  # Demo: 48 hours for hackathon
MAX_DEBATE_ROUNDS = 3

# --- Safety conditions for auto-finalize ---
SAFETY_CONDITIONS_FOR_TIMEOUT = [
    "verification_passed",
    "evidence_sufficient",
    "no_high_risk_flag",
    "notification_confirmed",
]

# --- Evidence kinds ---
EVIDENCE_KINDS = {
    "gps_telemetry": "GPS & route telemetry data",
    "chat_log": "In-app chat and communication logs",
    "payment_data": "Fare breakdown and payment records",
    "app_event": "System app events (arrival, wait timer, cancellation)",
    "profile": "Rider/driver historical behavior profile",
    "policy": "Applicable company policy rules",
}
