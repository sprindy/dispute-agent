"""
REST API for the Ryde Dispute Resolution Agent.

Exposes endpoints for:
- POST /dispute: Submit a new dispute case
- GET /dispute/{dispute_id}/result: Get resolution result
- GET /policies: List all policy rules
- GET /health: Health check
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any
import sys
import os

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from policy_engine import PolicyEngine
from dispute_resolver import DisputeResolver
from evidence_collector import DisputeCase, EvidenceItem, EvidenceStatus, EvidenceKind
from sample_cases import (
    build_disp002_case,
    build_route_deviation_case,
    build_cancellation_grace_case,
    build_cash_processing_fee_case,
    build_safety_incident_case,
)

app = FastAPI(
    title="Ryde Dispute Resolution Agent",
    description="Multi-agent autonomous dispute resolution for ride-hailing (Tencent Cloud Hackathon 2026)",
    version="1.0.0",
)

# Initialize engine and resolver
_policy_engine = PolicyEngine()
_resolver = DisputeResolver(_policy_engine)

# In-memory store for demo
_results_store: dict[str, dict] = {}


# --- Models ---

class EvidenceItemModel(BaseModel):
    evidence_id: str
    kind: str
    status: str
    field: str = ""
    value: Any = None
    supports_fields: list[str] = Field(default_factory=list)
    source_description: str = ""


class DisputeRequest(BaseModel):
    dispute_id: str
    trip_id: str = ""
    filed_by: str = "rider"
    category: str
    description: str
    filed_at: str = ""
    case_date: str = ""
    rider_id: str = ""
    driver_id: str = ""
    facts: dict = Field(default_factory=dict)
    evidence: list[EvidenceItemModel] = Field(default_factory=list)
    prior_rejected_disputes: int = 0
    driver_rating: float = 0.0


# --- Endpoints ---

@app.get("/health")
async def health():
    return {"status": "ok", "policy_engine": _policy_engine.summary()}


@app.get("/policies")
async def list_policies():
    return {
        "snapshot": _policy_engine.summary(),
        "rule_ids": _policy_engine.all_rule_ids(),
    }


@app.get("/policies/{policy_id}")
async def get_policy(policy_id: str):
    rule = _policy_engine.get_rule(policy_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")
    return {
        "policy_id": rule.policy_id,
        "category": rule.category,
        "summary": rule.summary,
        "status": rule.status,
        "parameters": rule.parameters,
        "interpretation_note": rule.interpretation_note,
        "source_ids": rule.source_ids,
        "conflicts": [
            {"id": c.id, "topic": c.topic, "description": c.description}
            for c in _policy_engine.get_conflicts_for_policy(policy_id)
        ],
    }


@app.post("/dispute")
async def submit_dispute(req: DisputeRequest):
    """Submit a dispute case and run the full resolution pipeline."""
    evidence_items = [
        EvidenceItem(
            evidence_id=e.evidence_id,
            kind=EvidenceKind(e.kind) if e.kind in [k.value for k in EvidenceKind] else EvidenceKind.APP_EVENT,
            status=EvidenceStatus(e.status) if e.status in [s.value for s in EvidenceStatus] else EvidenceStatus.AVAILABLE,
            field=e.field,
            value=e.value,
            supports_fields=e.supports_fields,
            source_description=e.source_description,
        )
        for e in req.evidence
    ]

    case = DisputeCase(
        dispute_id=req.dispute_id,
        trip_id=req.trip_id,
        filed_by=req.filed_by,
        category=req.category,
        description=req.description,
        filed_at=req.filed_at,
        case_date=req.case_date,
        rider_id=req.rider_id,
        driver_id=req.driver_id,
        facts=req.facts,
        evidence=evidence_items,
        prior_rejected_disputes=req.prior_rejected_disputes,
        driver_rating=req.driver_rating,
    )

    result = _resolver.resolve(case)
    _results_store[req.dispute_id] = result.to_dict()
    return result.to_dict()


@app.get("/dispute/{dispute_id}/result")
async def get_result(dispute_id: str):
    if dispute_id not in _results_store:
        raise HTTPException(status_code=404, detail=f"No result for dispute {dispute_id}")
    return _results_store[dispute_id]


@app.post("/demo/{case_name}")
async def run_demo_case(case_name: str):
    """Run a pre-built demo case."""
    demo_cases = {
        "disp002": build_disp002_case,
        "route_deviation": build_route_deviation_case,
        "cancellation_grace": build_cancellation_grace_case,
        "cash_processing_fee": build_cash_processing_fee_case,
        "safety_incident": build_safety_incident_case,
    }
    if case_name not in demo_cases:
        raise HTTPException(status_code=400, detail=f"Unknown demo case: {case_name}")
    case = demo_cases[case_name]()
    result = _resolver.resolve(case)
    _results_store[case.dispute_id] = result.to_dict()
    return result.to_dict()
