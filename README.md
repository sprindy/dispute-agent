# Ryde Dispute Resolution Agent — CodeBuddy Solution

A multi-agent autonomous dispute resolution system for ride-hailing disputes, built for the Tencent Cloud Hackathon Singapore 2026 — Digital Native Track (Ryde).

## Overview

This solution implements the **Progressive Multi-Agent Dispute Resolution** architecture described in the Ryde Product Design Document (Vision 4). It uses three core agents — **Rider Advocate**, **Driver Advocate**, and **Judge Agent** — backed by the public policy snapshot from `data/ryde_public_policy_v1/`.

### Key Design Principles (from Vision 4)

- **Progressive escalation**: Strong-evidence cases auto-resolve; contested cases enter debate; uncertain/high-risk cases go to human review.
- **Hallucination control**: Every LLM decision is validated; validation failure blocks auto-execution.
- **Financial safety**: LLM proposes liability labels only; refund amounts are computed deterministically by a Refund Engine.
- **Symmetric challenge**: Both parties get equal challenge standards and time limits.
- **Policy over history**: Company policy is normative; historical behavior is reference only and never independently establishes liability.

### Evidence Sources (from Hackathon PDF)

- GPS & Telemetry Data — route deviation, unexpected stops, trip duration
- Chat & Communication Logs — sentiment, agreements, disagreements
- Payment & Fare Data — fare breakdown validation, surge pricing disputes
- Historical Behavior Profiles — dispute history, rating patterns, account age

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Dispute Intake API                       │
│                  (REST endpoint: POST /dispute)               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Triage & Classification                   │
│  Categorize dispute → Load applicable policies → Plan evidence│
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Evidence Collector                        │
│  Gather GPS, chat, payment, profile data → Validate sources  │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
     │   Rider       │ │   Driver     │ │    Judge     │
     │  Advocate     │ │  Advocate    │ │    Agent     │
     │               │ │              │ │              │
     │ Builds case   │ │ Builds case  │ │ Evaluates    │
     │ for rider     │ │ for driver   │ │ both cases   │
     └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
            │                 │                │
            └────────┬───────┘                │
                     ▼                        │
           ┌─────────────────┐                │
           │  Verification   │◄───────────────┘
           │     Layer       │
           └────────┬────────┘
                     │
                     ▼
           ┌─────────────────┐
           │  Confidence &   │
           │  Risk Router    │
           └────────┬────────┘
                     │
          ┌─────────┼──────────┐
          ▼         ▼          ▼
    ┌──────────┐ ┌────────┐ ┌──────────┐
    │ Auto-    │ │Challenge│ │  Human   │
    │ resolve  │ │Window   │ │  Review  │
    └──────────┘ └───┬────┘ └──────────┘
                        │
                   ┌────┴────┐
                   ▼         ▼
             ┌─────────┐ ┌──────────┐
             │ Accept  │ │ Debate   │
             │ (close) │ │ (re-eval)│
             └─────────┘ └──────────┘
                        │
                        ▼
               ┌─────────────────┐
               │  Refund Engine   │
               │ (deterministic)  │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │  Final Decision  │
               └─────────────────┘
```

## Project Structure

```
codebuddy/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── config.py                    # Configuration & constants
├── policy_engine.py             # Policy loader & matcher
├── evidence_collector.py        # Evidence gathering & validation
├── agents/
│   ├── __init__.py
│   ├── base_agent.py            # Base agent with LLM interface
│   ├── rider_advocate.py        # Rider Advocate agent
│   ├── driver_advocate.py        # Driver Advocate agent
│   └── judge_agent.py           # Judge Agent
├── verification.py              # Deterministic verification layer
├── confidence_router.py         # Confidence & risk routing
├── challenge_gate.py            # Challenge admissibility & debate trigger
├── refund_engine.py             # Deterministic refund calculator
├── dispute_resolver.py          # Orchestrator: end-to-end flow
├── api.py                       # REST API (FastAPI)
├── run_demo.py                  # CLI demo runner
├── sample_cases.py              # Sample dispute cases (from DISP-002 & policy data)
└── tests/
    ├── __init__.py
    └── test_resolver.py         # Unit tests
```

## Quick Start

```bash
# Install dependencies
pip install -r codebuddy/requirements.txt

# Run the demo (processes the DISP-002 no-show case)
python codebuddy/run_demo.py

# Start the REST API
uvicorn codebuddy.api:app --reload --port 8000

# Run tests
python -m pytest codebuddy/tests/ -v
```

## Dispute Categories Supported

| Category | Description | Key Policies |
|----------|-------------|-------------|
| `no_show_charge` | Rider charged for no-show; disputes the fee | CAN-01, CAN-02, CAN-10 |
| `route_deviation` | Driver took longer route; rider claims overcharge | FARE-01, FARE-02, FARE-08 |
| `cancellation_fee` | Rider disputes cancellation charge | CAN-01, CAN-04, CAN-05, CAN-06 |
| `waiting_fee` | Rider disputes waiting fee on completed trip | CAN-03 |
| `cleaning_fee` | Driver claims cleaning fee from rider | CLEAN-01 to CLEAN-06 |
| `fare_dispute` | Rider disputes fare amount or extra charges | FARE-02, FARE-10, FARE-11, FARE-14 |
| `safety_incident` | Safety allegation (harassment, dangerous driving) | SAFE-01 to SAFE-08 |

## Business Rules (BR-01 to BR-10)

All agents enforce the 10 core business rules from the design document:

| Rule | Enforcement Point |
|------|-------------------|
| BR-01: Every LLM decision verified | `verification.py` |
| BR-02: Missing facts stay UNKNOWN | `evidence_collector.py` |
| BR-03: Policy > history | `policy_engine.py` |
| BR-04: Symmetric challenge | `challenge_gate.py` |
| BR-05: Frivolous challenges blocked | `challenge_gate.py` |
| BR-06: History ≠ independent liability | `agents/base_agent.py` |
| BR-07: LLM doesn't compute refunds | `refund_engine.py` |
| BR-08: Valid challenge → debate | `dispute_resolver.py` |
| BR-09: Exceeded debate → human | `confidence_router.py` |
| BR-10: Timeout only with safe conditions | `dispute_resolver.py` |

## Data Sources

- **Policy snapshot**: `data/ryde_public_policy_v1/policies.json` (79 rules)
- **Source conflicts**: `data/ryde_public_policy_v1/policy_conflicts.json` (7 conflicts, 4 gaps)
- **Training cases**: `data/ryde_public_policy_v1/train.jsonl` (252 examples)
- **Scenario specs**: `data/ryde_public_policy_v1/scenario_specs.json` (100 scenarios)
- **Sample dispute**: `data/RydeResolve Sample Dataset — DISP-002 No-Show Charge Dispute (SG).md`

## License

Hackathon project — not affiliated with or endorsed by Ryde.
