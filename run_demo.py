#!/usr/bin/env python3
"""
CLI demo runner — processes sample dispute cases through the full pipeline.

Usage:
    python codebuddy/run_demo.py              # Run all demo cases
    python codebuddy/run_demo.py disp002      # Run specific case
"""
import sys
import os
import json

# Add the codebuddy directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from policy_engine import PolicyEngine
from dispute_resolver import DisputeResolver
from sample_cases import (
    build_disp002_case,
    build_route_deviation_case,
    build_cancellation_grace_case,
    build_cash_processing_fee_case,
    build_safety_incident_case,
)

DEMO_CASES = {
    "disp002": ("DISP-002: No-Show Charge Dispute (rider claims driver never showed)", build_disp002_case),
    "route_deviation": ("DISP-003: Route Deviation (rider requests 20% refund)", build_route_deviation_case),
    "cancellation_grace": ("DISP-004: Cancellation within 3-min grace", build_cancellation_grace_case),
    "cash_fee": ("DISP-005: Cash payment with processing fee", build_cash_processing_fee_case),
    "safety": ("DISP-006: Safety allegation (auto-escalation)", build_safety_incident_case),
}


def print_separator(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(result):
    print(f"\n  Dispute ID:     {result.dispute_id}")
    print(f"  Category:       {result.category}")
    print(f"  Route:          {result.route}")
    print(f"  Assessment:     {result.final_assessment}")
    print(f"  Liability:      {result.liability_label}")
    print(f"  Human Review:   {result.human_review_required}")
    print(f"  Final Decision: {result.final_decision}")
    print(f"  Next Step:      {result.next_step}")

    if result.confidence_score:
        print(f"\n  Confidence Score:")
        for k, v in result.confidence_score.items():
            print(f"    {k}: {v}")

    if result.refund:
        print(f"\n  Refund Engine:")
        print(f"    Amount:   ${result.refund.get('amount_sgd', 0)} SGD")
        print(f"    Policy:   {result.refund.get('policy_id', 'N/A')}")
        print(f"    Capped:   {result.refund.get('capped', False)}")
        basis = result.refund.get('calculation_basis', '')
        if basis:
            print(f"    Basis:    {basis[:100]}...")

    print(f"\n  Stages:")
    for stage in result.stages:
        status_icon = "OK" if stage.status == "completed" else "..."
        print(f"    [{status_icon}] {stage.stage_name}")


def main():
    print_separator("Ryde Dispute Resolution Agent — Demo Runner")
    print("  Tencent Cloud Hackathon Singapore 2026 — Digital Native Track")
    print("  Progressive Multi-Agent Dispute Resolution (Vision 4)")

    # Initialize
    print("\n  Initializing policy engine...")
    pe = PolicyEngine()
    summary = pe.summary()
    print(f"    Snapshot:      {summary['snapshot_id']}")
    print(f"    Rules:         {summary['total_rules']}")
    print(f"    Conflicts:     {summary['total_conflicts']}")
    print(f"    Gaps:          {summary['total_gaps']}")

    resolver = DisputeResolver(pe)
    print("  Resolver initialized with Rider Advocate, Driver Advocate, Judge Agent.")

    # Determine which cases to run
    if len(sys.argv) > 1:
        case_keys = [sys.argv[1]]
    else:
        case_keys = list(DEMO_CASES.keys())

    for key in case_keys:
        if key not in DEMO_CASES:
            print(f"\n  Unknown case: {key}")
            print(f"  Available: {', '.join(DEMO_CASES.keys())}")
            continue

        title, builder = DEMO_CASES[key]
        print_separator(title)

        case = builder()
        print(f"\n  Description: {case.description[:120]}...")
        print(f"  Filed by:    {case.filed_by}")
        print(f"  Rider:       {case.rider_id}")
        print(f"  Driver:      {case.driver_id}")
        print(f"  Evidence:    {len(case.evidence)} item(s)")

        result = resolver.resolve(case)
        print_result(result)

    print_separator("Demo Complete")
    print("  All cases processed. Review the output above for routing decisions.")
    print("  To start the REST API: uvicorn codebuddy.api:app --reload --port 8000")


if __name__ == "__main__":
    main()
