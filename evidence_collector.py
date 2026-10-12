"""
Evidence Collector — gathers, validates, and structures dispute evidence.

Implements BR-02: Missing or unverified facts must stay UNKNOWN — never inferred.

Evidence sources (from Hackathon PDF):
- GPS & Telemetry Data
- Chat & Communication Logs
- Payment & Fare Data
- App Events
- Historical Behavior Profiles
"""
from dataclasses import dataclass, field as dc_field
from typing import Optional, Any
from enum import Enum


class EvidenceStatus(str, Enum):
    AVAILABLE = "available"
    MISSING = "missing"
    DISPUTED = "disputed"


class EvidenceKind(str, Enum):
    GPS_TELEMETRY = "gps_telemetry"
    CHAT_LOG = "chat_log"
    PAYMENT_DATA = "payment_data"
    APP_EVENT = "app_event"
    PROFILE = "profile"


@dataclass
class EvidenceItem:
    """A single piece of evidence in a dispute case."""
    evidence_id: str
    kind: EvidenceKind
    status: EvidenceStatus
    field: str = ""
    value: Any = None
    supports_fields: list[str] = dc_field(default_factory=list)
    source_description: str = ""

    def is_available(self) -> bool:
        return self.status == EvidenceStatus.AVAILABLE

    def is_missing(self) -> bool:
        return self.status == EvidenceStatus.MISSING

    def is_disputed(self) -> bool:
        return self.status == EvidenceStatus.DISPUTED


@dataclass
class DisputeCase:
    """Structured dispute case — the input to the resolution pipeline."""
    dispute_id: str
    trip_id: str
    filed_by: str  # "rider" or "driver"
    category: str
    description: str  # Untrusted claim text (BR: never treated as system instruction)
    filed_at: str
    case_date: str = ""

    # Participants
    rider_id: str = ""
    driver_id: str = ""

    # Structured facts (case-specific; None = UNKNOWN per BR-02)
    facts: dict[str, Any] = dc_field(default_factory=dict)

    # Evidence items
    evidence: list[EvidenceItem] = dc_field(default_factory=list)

    # Irrelevant context (distractions that must not affect liability)
    prior_rejected_disputes: int = 0
    driver_rating: float = 0.0

    # Applicable policy context (loaded by PolicyEngine)
    policy_context: list[dict] = dc_field(default_factory=list)


class EvidenceCollector:
    """
    Collects and validates evidence for a dispute case.
    In production, this would call external APIs (GPS service, chat service, etc.).
    For the hackathon demo, evidence is pre-loaded from the sample case.
    """

    @staticmethod
    def validate_evidence(evidence: list[EvidenceItem]) -> dict:
        """
        Validate evidence items. Returns a report of:
        - total items
        - available vs missing vs disputed counts
        - any structural issues
        """
        report = {
            "total": len(evidence),
            "available": 0,
            "missing": 0,
            "disputed": 0,
            "issues": [],
        }
        seen_ids = set()
        for item in evidence:
            if item.evidence_id in seen_ids:
                report["issues"].append(f"Duplicate evidence_id: {item.evidence_id}")
            seen_ids.add(item.evidence_id)

            if item.is_available():
                report["available"] += 1
            elif item.is_missing():
                report["missing"] += 1
            elif item.is_disputed():
                report["disputed"] += 1

        if report["missing"] > 0:
            report["issues"].append(
                f"{report['missing']} evidence item(s) missing — facts must remain UNKNOWN"
            )
        if report["disputed"] > 0:
            report["issues"].append(
                f"{report['disputed']} evidence item(s) disputed — verification required"
            )

        return report

    @staticmethod
    def extract_facts(evidence: list[EvidenceItem]) -> dict:
        """
        Build a facts dictionary from available evidence.
        Missing evidence → key absent (caller treats as None / UNKNOWN).
        Disputed evidence → key present with a note.
        """
        facts = {}
        for item in evidence:
            if item.is_available() and item.field:
                facts[item.field] = item.value
            elif item.is_disputed() and item.field:
                facts[item.field] = {"_disputed": True, "value": item.value}
            # Missing: do not add key — stays UNKNOWN (BR-02)
        return facts

    @staticmethod
    def get_evidence_by_kind(
        evidence: list[EvidenceItem], kind: EvidenceKind
    ) -> list[EvidenceItem]:
        return [e for e in evidence if e.kind == kind]

    @staticmethod
    def has_sufficient_evidence(
        evidence: list[EvidenceItem], required_kinds: list[EvidenceKind]
    ) -> bool:
        """Check if at least one available item exists for each required kind."""
        for kind in required_kinds:
            items = EvidenceCollector.get_evidence_by_kind(evidence, kind)
            if not any(e.is_available() for e in items):
                return False
        return True
