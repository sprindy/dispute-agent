"""
REST API for the Ryde Dispute Resolution Agent.

Exposes endpoints for:
- Auth: register, login, me, change-password
- POST /dispute: Submit a new dispute case (stores to DB if logged in)
- GET /dispute/{dispute_id}/result: Get resolution result
- GET /dispute/history: Get current user's dispute history
- POST /dispute/bookmark/{dispute_id}: Bookmark a dispute
- DELETE /dispute/bookmark/{dispute_id}: Remove bookmark
- GET /dispute/bookmarks: Get bookmarked disputes
- GET /admin/users: List all users (admin only)
- GET /admin/disputes: List all disputes (admin only)
- DELETE /admin/users/{user_id}: Delete a user (admin only)
- GET /policies: List all policy rules
- GET /health: Health check
"""
from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Any
import json
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
import database as db
import auth

app = FastAPI(
    title="Ryde Dispute Resolution Agent",
    description="Multi-agent autonomous dispute resolution for ride-hailing (Tencent Cloud Hackathon 2026)",
    version="2.0.0",
)

# Initialize engine and resolver
_policy_engine = PolicyEngine()
_resolver = DisputeResolver(_policy_engine)

# Initialize database
db.init_db()

# In-memory store for demo (still used for non-authed disputes)
_results_store: dict[str, dict] = {}


# --- Helper ---

def _extract_token(authorization: Optional[str]) -> Optional[dict]:
    """Extract and verify user from Authorization header."""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    return auth.get_current_user(token)


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


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# --- Endpoints: Health ---

@app.get("/health")
async def health():
    return {"status": "ok", "policy_engine": _policy_engine.summary()}


# --- Endpoints: Auth ---

@app.post("/auth/register")
async def register(req: RegisterRequest):
    """Register a new user account."""
    try:
        result = auth.register(req.username, req.email, req.password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
async def login(req: LoginRequest):
    """Login and receive a JWT token."""
    try:
        result = auth.login(req.username, req.password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.get("/auth/me")
async def get_me(authorization: Optional[str] = Header(None)):
    """Get current user info from token."""
    user = _extract_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user": user}


@app.post("/auth/change-password")
async def change_password(req: ChangePasswordRequest, authorization: Optional[str] = Header(None)):
    """Change password for the current user."""
    user = _extract_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        auth.change_password(user["id"], req.old_password, req.new_password)
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
async def submit_dispute(req: DisputeRequest, authorization: Optional[str] = Header(None)):
    """Submit a dispute case and run the full resolution pipeline.
    If authenticated, saves the result to the user's dispute history."""
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
    result_dict = result.to_dict()
    _results_store[req.dispute_id] = result_dict

    # Save to DB if user is logged in
    user = _extract_token(authorization)
    if user:
        db.save_dispute(
            user_id=user["id"],
            dispute_id=req.dispute_id,
            category=req.category,
            filed_by=req.filed_by,
            description=req.description,
            result_json=json.dumps(result_dict),
        )

    return result_dict


@app.get("/dispute/{dispute_id}/result")
async def get_result(dispute_id: str):
    if dispute_id not in _results_store:
        raise HTTPException(status_code=404, detail=f"No result for dispute {dispute_id}")
    return _results_store[dispute_id]


@app.post("/demo/{case_name}")
async def run_demo_case(case_name: str, authorization: Optional[str] = Header(None)):
    """Run a pre-built demo case."""
    demo_cases = {
        "disp002": build_disp002_case,
        "route_deviation": build_route_deviation_case,
        "cancellation_grace": build_cancellation_grace_case,
        "cash_fee": build_cash_processing_fee_case,
        "cash_processing_fee": build_cash_processing_fee_case,
        "safety": build_safety_incident_case,
        "safety_incident": build_safety_incident_case,
    }
    if case_name not in demo_cases:
        raise HTTPException(status_code=400, detail=f"Unknown demo case: {case_name}")
    case = demo_cases[case_name]()
    result = _resolver.resolve(case)
    result_dict = result.to_dict()
    _results_store[case.dispute_id] = result_dict

    # Save to DB if user is logged in
    user = _extract_token(authorization)
    if user:
        db.save_dispute(
            user_id=user["id"],
            dispute_id=case.dispute_id,
            category=case.category,
            filed_by=case.filed_by,
            description=case.description,
            result_json=json.dumps(result_dict),
        )

    return result_dict


# --- Endpoints: Dispute History ---

@app.get("/dispute/history")
async def get_dispute_history(authorization: Optional[str] = Header(None)):
    """Get the current user's dispute history."""
    user = _extract_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    disputes = db.get_user_disputes(user["id"])
    return {"disputes": [
        {
            "id": d["id"],
            "dispute_id": d["dispute_id"],
            "category": d["category"],
            "filed_by": d["filed_by"],
            "description": d["description"],
            "result": json.loads(d["result_json"]) if d["result_json"] else None,
            "created_at": d["created_at"],
        }
        for d in disputes
    ]}


@app.delete("/dispute/history/{dispute_pk}")
async def delete_dispute_from_history(dispute_pk: int, authorization: Optional[str] = Header(None)):
    """Delete a dispute from the user's history."""
    user = _extract_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db.delete_dispute(dispute_pk, user["id"])
    return {"message": "Dispute deleted"}


# --- Endpoints: Bookmarks ---

@app.post("/dispute/bookmark/{dispute_id}")
async def add_bookmark(dispute_id: str, authorization: Optional[str] = Header(None)):
    """Bookmark a dispute for later review."""
    user = _extract_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db.add_bookmark(user["id"], dispute_id)
    return {"message": "Bookmarked", "dispute_id": dispute_id}


@app.delete("/dispute/bookmark/{dispute_id}")
async def remove_bookmark(dispute_id: str, authorization: Optional[str] = Header(None)):
    """Remove a bookmark."""
    user = _extract_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    db.remove_bookmark(user["id"], dispute_id)
    return {"message": "Bookmark removed", "dispute_id": dispute_id}


@app.get("/dispute/bookmarks")
async def get_bookmarks(authorization: Optional[str] = Header(None)):
    """Get the user's bookmarked disputes."""
    user = _extract_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    bookmarks = db.get_user_bookmarks(user["id"])
    return {"bookmarks": [
        {
            "id": b["id"],
            "dispute_id": b["dispute_id"],
            "category": b.get("category"),
            "description": b.get("description"),
            "result": json.loads(b["result_json"]) if b.get("result_json") else None,
            "created_at": b["created_at"],
        }
        for b in bookmarks
    ]}


# --- Endpoints: Admin ---

@app.get("/admin/users")
async def admin_list_users(authorization: Optional[str] = Header(None)):
    """List all users (admin only)."""
    user = _extract_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    users = db.list_all_users()
    return {"users": users, "total": len(users)}


@app.get("/admin/disputes")
async def admin_list_disputes(authorization: Optional[str] = Header(None)):
    """List all disputes across all users (admin only)."""
    user = _extract_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    disputes = db.get_all_disputes()
    return {"disputes": [
        {
            "id": d["id"],
            "dispute_id": d["dispute_id"],
            "username": d["username"],
            "category": d["category"],
            "filed_by": d["filed_by"],
            "description": d["description"],
            "result": json.loads(d["result_json"]) if d["result_json"] else None,
            "created_at": d["created_at"],
        }
        for d in disputes
    ], "total": len(disputes)}


@app.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: int, authorization: Optional[str] = Header(None)):
    """Delete a user (admin only)."""
    user = _extract_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    if user["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    db.delete_user(user_id)
    return {"message": "User deleted"}


# --- Serve UI ---
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/")
async def serve_ui():
    return FileResponse(os.path.join(_static_dir, "index.html"))
