"""
Sample dispute cases derived from:
1. DISP-002 No-Show Charge Dispute (from the sample dataset markdown)
2. Scenario specs from data/ryde_public_policy_v1/scenario_specs.json
3. Public policy rules from data/ryde_public_policy_v1/policies.json
"""
from evidence_collector import DisputeCase, EvidenceItem, EvidenceStatus, EvidenceKind


def build_disp002_case() -> DisputeCase:
    """
    DISP-002: No-Show Charge Dispute from the RydeResolve sample dataset.

    Key facts from the sample data:
    - Driver arrived at Tiong Bahru Plaza at 08:43 (2 min early)
    - Scheduled pickup: 08:45
    - Driver waited from 08:43 to 08:51 (8 min total)
    - Free wait timer: 5 min (08:43–08:48)
    - No-show threshold: 8 min (reached at 08:51)
    - Cancellation fee: $5.00 SGD
    - Rider claims driver never showed up

    NOTE: The DISP-002 sample uses invented 5-min/8-min thresholds that
    the public policy snapshot does NOT confirm. CAN-02 states the
    threshold is "more than 3 minutes of waiting" (180s), not 5 or 8 min.
    The system will assess using the actual public policy, not the
    sample's invented rules.
    """
    return DisputeCase(
        dispute_id="DISP-002",
        trip_id="TRIP-2026-09945",
        filed_by="rider",
        category="no_show_charge",
        description=(
            "I was at the pickup point at Tiong Bahru Plaza on time but the driver "
            "never showed up. I waited 10 minutes at the lobby and couldn't find the "
            "car. The app charged me a $5.00 cancellation fee for a 'no-show' which "
            "is completely unfair — I was there, the driver was not. I want the "
            "charge reversed immediately."
        ),
        filed_at="2026-09-13T09:20:00+08:00",
        case_date="2026-09-13",
        rider_id="R-7823",
        driver_id="D-2398",
        facts={
            "pickup_arrival_verified": True,
            "wait_seconds": 480,  # 8 min from GPS telemetry (08:43 to 08:51)
            "trip_completed": False,
            "rider_absent": True,
            "rider_charge_sgd": 5.00,  # Note: public policy says $6.61, sample says $5
            "driver_payment_sgd": 4.50,  # CAN-09: different role amount
            "fee_type": "no_show",
            "match_to_cancel_seconds": None,  # Not provided in sample
            "service": "on_demand",
        },
        evidence=[
            EvidenceItem(
                evidence_id="E1",
                kind=EvidenceKind.GPS_TELEMETRY,
                status=EvidenceStatus.AVAILABLE,
                field="pickup_arrival_verified",
                value=True,
                supports_fields=["pickup_arrival_verified", "wait_seconds"],
                source_description="GPS telemetry shows driver stationary at pickup from 08:43 to 08:51",
            ),
            EvidenceItem(
                evidence_id="E2",
                kind=EvidenceKind.GPS_TELEMETRY,
                status=EvidenceStatus.AVAILABLE,
                field="wait_seconds",
                value=480,
                supports_fields=["wait_seconds"],
                source_description="GPS: 8 min stationary at pickup coordinates",
            ),
            EvidenceItem(
                evidence_id="E3",
                kind=EvidenceKind.CHAT_LOG,
                status=EvidenceStatus.AVAILABLE,
                field="driver_contact_attempts",
                value=5,  # 4 messages + 1 call
                supports_fields=["driver_contact_attempts"],
                source_description="Driver sent 4 messages + 1 in-app call; rider sent 0",
            ),
            EvidenceItem(
                evidence_id="E4",
                kind=EvidenceKind.PAYMENT_DATA,
                status=EvidenceStatus.AVAILABLE,
                field="rider_charge_sgd",
                value=5.00,
                supports_fields=["rider_charge_sgd"],
                source_description="Cancellation fee of $5.00 charged to rider e-wallet",
            ),
            EvidenceItem(
                evidence_id="E5",
                kind=EvidenceKind.APP_EVENT,
                status=EvidenceStatus.AVAILABLE,
                field="driver_arrival_time",
                value="2026-09-13T08:43:00+08:00",
                supports_fields=["pickup_arrival_verified"],
                source_description="App event: driver_arrived at 08:43, 2 min before scheduled",
            ),
            EvidenceItem(
                evidence_id="E6",
                kind=EvidenceKind.APP_EVENT,
                status=EvidenceStatus.AVAILABLE,
                field="cancellation_time",
                value="2026-09-13T08:51:00+08:00",
                source_description="App event: trip cancelled by driver at 08:51, reason: rider_no_show",
            ),
            EvidenceItem(
                evidence_id="E7",
                kind=EvidenceKind.PAYMENT_DATA,
                status=EvidenceStatus.AVAILABLE,
                field="driver_payment_sgd",
                value=4.50,
                supports_fields=["driver_payment_sgd"],
                source_description="Driver cancellation payment: $4.50 (CAN-09)",
            ),
        ],
        prior_rejected_disputes=3,
        driver_rating=4.9,
    )


def build_route_deviation_case() -> DisputeCase:
    """
    A route deviation case where the rider claims a 25% longer route
    and requests a 20% refund. FARE-01 states no percentage refund formula exists.
    """
    return DisputeCase(
        dispute_id="DISP-003",
        trip_id="TRIP-2026-10067",
        filed_by="rider",
        category="route_deviation",
        description=(
            "The driver took a longer route from Tiong Bahru to VivoCity. "
            "I was overcharged by at least 25%. I want a 20% refund."
        ),
        filed_at="2026-09-15T14:30:00+08:00",
        case_date="2026-09-15",
        rider_id="R-5432",
        driver_id="D-1102",
        facts={
            "service": "RydeFLASH",
            "quoted_fare_sgd": 18,
            "base_fare_charged_sgd": 18,
            "route_distance_increase_pct": 25,
            "requested_refund_pct": 20,
            "accepted_destination_edit": False,
            "extra_lines_explained": False,
        },
        evidence=[
            EvidenceItem(
                evidence_id="E1",
                kind=EvidenceKind.PAYMENT_DATA,
                status=EvidenceStatus.AVAILABLE,
                field="quoted_fare_sgd",
                value=18,
                source_description="Quoted fare at booking: $18.00 SGD",
            ),
            EvidenceItem(
                evidence_id="E2",
                kind=EvidenceKind.PAYMENT_DATA,
                status=EvidenceStatus.AVAILABLE,
                field="base_fare_charged_sgd",
                value=18,
                source_description="Charged base fare: $18.00 SGD",
            ),
            EvidenceItem(
                evidence_id="E3",
                kind=EvidenceKind.GPS_TELEMETRY,
                status=EvidenceStatus.AVAILABLE,
                field="route_distance_increase_pct",
                value=25,
                source_description="GPS route analysis: 25% longer than optimal route",
            ),
        ],
        prior_rejected_disputes=0,
        driver_rating=4.7,
    )


def build_cancellation_grace_case() -> DisputeCase:
    """
    A rider cancelled 120s (2 min) after matching — within the 3-min grace.
    CAN-01: cancellation within 3 min of matching is free.
    """
    return DisputeCase(
        dispute_id="DISP-004",
        trip_id="TRIP-2026-10089",
        filed_by="rider",
        category="cancellation_fee",
        description=(
            "I cancelled my ride right after matching because I realised I "
            "entered the wrong destination. The app charged me $6.61 but "
            "it was within 2 minutes."
        ),
        filed_at="2026-09-16T10:15:00+08:00",
        case_date="2026-09-16",
        rider_id="R-8890",
        driver_id="D-3344",
        facts={
            "service": "RydeFLASH",
            "match_to_cancel_seconds": 120,
            "rider_charge_sgd": 6.61,
            "driver_arrived_before_cancel": False,
        },
        evidence=[
            EvidenceItem(
                evidence_id="E1",
                kind=EvidenceKind.APP_EVENT,
                status=EvidenceStatus.AVAILABLE,
                field="match_to_cancel_seconds",
                value=120,
                source_description="App event: match at 10:13:00, cancellation at 10:15:00 (120s)",
            ),
            EvidenceItem(
                evidence_id="E2",
                kind=EvidenceKind.PAYMENT_DATA,
                status=EvidenceStatus.AVAILABLE,
                field="rider_charge_sgd",
                value=6.61,
                source_description="Cancellation fee: $6.61 SGD",
            ),
        ],
        prior_rejected_disputes=0,
        driver_rating=4.5,
    )


def build_cash_processing_fee_case() -> DisputeCase:
    """
    Rider paid cash but was charged a processing fee.
    FARE-11: Cash payments do not have a processing fee.
    """
    return DisputeCase(
        dispute_id="DISP-005",
        trip_id="TRIP-2026-10112",
        filed_by="rider",
        category="fare_dispute",
        description="I paid cash for my ride but there's a $0.60 processing fee on my receipt.",
        filed_at="2026-09-17T16:00:00+08:00",
        case_date="2026-09-17",
        rider_id="R-2233",
        driver_id="D-7788",
        facts={
            "payment": "cash",
            "processing_fee_sgd": 0.60,
            "fare_sgd": 15.00,
            "platform_fee_sgd": 1.25,
        },
        evidence=[
            EvidenceItem(
                evidence_id="E1",
                kind=EvidenceKind.PAYMENT_DATA,
                status=EvidenceStatus.AVAILABLE,
                field="payment",
                value="cash",
                source_description="Payment method: cash",
            ),
            EvidenceItem(
                evidence_id="E2",
                kind=EvidenceKind.PAYMENT_DATA,
                status=EvidenceStatus.AVAILABLE,
                field="processing_fee_sgd",
                value=0.60,
                source_description="Receipt shows $0.60 processing fee",
            ),
        ],
        prior_rejected_disputes=0,
        driver_rating=4.6,
    )


def build_safety_incident_case() -> DisputeCase:
    """
    A safety allegation — must always escalate to human review.
    """
    return DisputeCase(
        dispute_id="DISP-006",
        trip_id="TRIP-2026-10134",
        filed_by="rider",
        category="safety_incident",
        description=(
            "The driver was driving dangerously and made inappropriate comments "
            "during the trip. I felt unsafe."
        ),
        filed_at="2026-09-18T20:30:00+08:00",
        case_date="2026-09-18",
        rider_id="R-4455",
        driver_id="D-9911",
        facts={
            "harassment_allegation": True,
            "message_record_present": True,
            "responsibility_verified": False,
        },
        evidence=[
            EvidenceItem(
                evidence_id="E1",
                kind=EvidenceKind.CHAT_LOG,
                status=EvidenceStatus.AVAILABLE,
                field="harassment_allegation",
                value=True,
                source_description="Chat logs show inappropriate messages from driver",
            ),
        ],
        prior_rejected_disputes=0,
        driver_rating=4.2,
    )
