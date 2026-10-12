const POLICY_DATA = {
  "snapshot_id": "RYDE-PUBLIC-2026-10-08-v1",
  "rules": [
    {
      "policy_id": "CAN-01",
      "category": "cancellation",
      "summary": "On-demand rider cancellation within three minutes of matching is free; later cancellation can incur a rider fee.",
      "source_ids": [
        "RYDE-HC-23534478435353",
        "RYDE-HC-4407761228825"
      ],
      "parameters": {
        "grace_seconds": 180,
        "rider_fee_sgd": 6.61
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "CAN-02",
      "category": "no_show",
      "summary": "No-show charging requires arrival at the booked pickup and more than three minutes of waiting before cancellation.",
      "source_ids": [
        "RYDE-HC-23534478435353",
        "RYDE-HC-4407754403353"
      ],
      "parameters": {
        "waiting_seconds_strictly_greater_than": 180,
        "rider_fee_sgd": 6.61
      },
      "status": "public_rule",
      "interpretation_note": "No numeric GPS geofence is stated. The arrival FAQ mislabels the amount as a waiting fee; see CONFLICT-01."
    },
    {
      "policy_id": "CAN-03",
      "category": "waiting",
      "summary": "A completed trip can carry a rider waiting fee after more than three minutes at pickup.",
      "source_ids": [
        "RYDE-HC-23534478435353",
        "RYDE-HC-4407754351257"
      ],
      "parameters": {
        "waiting_seconds_strictly_greater_than": 180,
        "rider_waiting_fee_sgd": 5
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "CAN-04",
      "category": "advance",
      "summary": "Advance cancellations more than fifteen minutes before scheduled pickup are free.",
      "source_ids": [
        "RYDE-HC-23534478435353"
      ],
      "parameters": {
        "free_if_seconds_before_schedule_gt": 900
      },
      "status": "public_rule",
      "interpretation_note": "Exactly fifteen minutes is not resolved clearly by this page."
    },
    {
      "policy_id": "CAN-05",
      "category": "advance",
      "summary": "Late-accepted advance bookings have a three-minute cancellation grace period.",
      "source_ids": [
        "RYDE-HC-23534478435353",
        "RYDE-HC-4407761270937"
      ],
      "parameters": {
        "late_acceptance_window_seconds": 900,
        "match_grace_seconds": 180
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "CAN-06",
      "category": "cancellation",
      "summary": "Driver arrival does not shorten the rider cancellation grace period.",
      "source_ids": [
        "RYDE-HC-4407761270937"
      ],
      "parameters": {
        "on_demand_match_grace_seconds": 180
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "CAN-07",
      "category": "waiver",
      "summary": "Cancellation-fee waiver requests must be filed within thirty days; approved relief is a voucher.",
      "source_ids": [
        "RYDE-HC-18229758389017"
      ],
      "parameters": {
        "request_deadline_days": 30,
        "approved_voucher_sgd": 6.61
      },
      "status": "discretionary",
      "interpretation_note": ""
    },
    {
      "policy_id": "CAN-08",
      "category": "waiver",
      "summary": "Waiting-fee waiver requests must be filed within thirty days; approved relief is a non-cash voucher.",
      "source_ids": [
        "RYDE-HC-27085468660505"
      ],
      "parameters": {
        "request_deadline_days": 30,
        "approved_voucher_sgd": 5
      },
      "status": "discretionary",
      "interpretation_note": ""
    },
    {
      "policy_id": "CAN-09",
      "category": "cancellation",
      "summary": "Driver fee amounts and rider charges are different roles: the driver cancellation policy lists a $4.50 payment.",
      "source_ids": [
        "RYDE-HC-33362932998937"
      ],
      "parameters": {
        "driver_payment_sgd": 4.5
      },
      "status": "public_rule",
      "interpretation_note": "Do not substitute driver earnings for the rider charge."
    },
    {
      "policy_id": "CAN-10",
      "category": "no_show",
      "summary": "Drivers should try in-app contact when a rider is absent; this guidance does not define an extra mandatory fee prerequisite.",
      "source_ids": [
        "RYDE-HC-115001438754"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": "No mandatory number of calls or eight-minute no-show rule is published here."
    },
    {
      "policy_id": "FARE-01",
      "category": "route",
      "summary": "Pickup and destination set the fixed fare; drivers can choose an efficient GPS route and discuss rider preferences.",
      "source_ids": [
        "RYDE-HC-4412121982745",
        "RYDE-HC-4412122016153"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": "No 10%, 15%, or 20% distance-based refund formula is published."
    },
    {
      "policy_id": "FARE-02",
      "category": "fare",
      "summary": "Quoted fares are generally fixed except RydeTAXI; receipts identify separate fees and tolls.",
      "source_ids": [
        "RYDE-HC-30741244296217",
        "RYDE-HC-360004075214"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "FARE-03",
      "category": "erp",
      "summary": "ERP applies when an active gantry is passed; ordinary service fares generally exclude it.",
      "source_ids": [
        "RYDE-HC-115000772653",
        "RYDE-HC-115001438614"
      ],
      "parameters": {},
      "status": "context_dependent",
      "interpretation_note": "Check service exceptions and CONFLICT-02 before assessing a charge."
    },
    {
      "policy_id": "FARE-04",
      "category": "delivery",
      "summary": "RydeSEND fares include ERP, tolls, and parking.",
      "source_ids": [
        "RYDE-HC-360007924554"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "FARE-05",
      "category": "erp",
      "summary": "Public RydePOOL ERP pages differ on inclusion and allocation; no universal pool surcharge is encoded.",
      "source_ids": [
        "RYDE-HC-115000772653",
        "RYDE-HC-115001438614",
        "RYDE-HC-4408072389913",
        "RYDE-HC-23575142762393"
      ],
      "parameters": {},
      "status": "source_conflict",
      "interpretation_note": ""
    },
    {
      "policy_id": "FARE-06",
      "category": "erp",
      "summary": "RydeHIRE-specific fare guidance includes tolls; broad ERP guidance differs.",
      "source_ids": [
        "RYDE-HC-4408072421785",
        "RYDE-HC-115000772653",
        "RYDE-HC-23575142762393"
      ],
      "parameters": {},
      "status": "source_conflict",
      "interpretation_note": ""
    },
    {
      "policy_id": "FARE-07",
      "category": "erp",
      "summary": "Drivers should enter actual ERP charges; excessive amounts can trigger investigation and account action.",
      "source_ids": [
        "RYDE-HC-900005170163"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "FARE-08",
      "category": "destination",
      "summary": "A driver-accepted destination change recalculates the route and fare; RydePOOL, RydeTAXI and multiple-stop bookings are excluded.",
      "source_ids": [
        "RYDE-HC-50798691815449"
      ],
      "parameters": {
        "excluded_services": [
          "RydePOOL",
          "RydeTAXI"
        ],
        "multiple_stop_excluded": true
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "FARE-09",
      "category": "destination",
      "summary": "A driver-accepted add or edit destination request has a receipt fee of $3.",
      "source_ids": [
        "RYDE-HC-51399796192921"
      ],
      "parameters": {
        "accepted_edit_fee_sgd": 3
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "FARE-10",
      "category": "platform_fee",
      "summary": "Platform fees apply to cash and cashless rides at different fare tiers.",
      "source_ids": [
        "RYDE-HC-22836370596377"
      ],
      "parameters": {
        "fare_threshold_sgd": 18,
        "lower_tier_inclusive": true,
        "lower_fee_sgd_inclusive_gst": 1.25,
        "upper_fee_sgd_inclusive_gst": 1.47
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "FARE-11",
      "category": "payment",
      "summary": "Cashless transactions have a processing fee; cash payments do not.",
      "source_ids": [
        "RYDE-HC-52595834493593"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "FARE-12",
      "category": "payment",
      "summary": "Transaction fees depend on payment type and may include a foreign-payment surcharge.",
      "source_ids": [
        "RYDE-HC-52596204611993",
        "RYDE-HC-52596215285273"
      ],
      "parameters": {
        "local_visa_mastercard_rydecoins_pct": 1.96,
        "local_fixed_sgd": 0.24,
        "amex_foreign_other_pct": 3.3,
        "amex_foreign_other_fixed_sgd": 0.5,
        "foreign_cards_alipay_additional_pct": 3
      },
      "status": "context_dependent",
      "interpretation_note": "The calculation base and rounding are not fully specified. Do not fabricate an exact total fee."
    },
    {
      "policy_id": "FARE-13",
      "category": "taxi",
      "summary": "RydeTAXI fares and booking fees follow the taxi company; the public FAQ lists cash payment.",
      "source_ids": [
        "RYDE-HC-900003406966"
      ],
      "parameters": {},
      "status": "context_dependent",
      "interpretation_note": ""
    },
    {
      "policy_id": "FARE-14",
      "category": "fare",
      "summary": "A $0.50 base-fare driver support fee is described as extended through the end of 2027.",
      "source_ids": [
        "RYDE-HC-60349453714585"
      ],
      "parameters": {
        "support_fee_sgd": 0.5,
        "stated_end_date": "2027-12-31"
      },
      "status": "public_rule",
      "interpretation_note": "Do not assume this is a separate receipt line or add it again."
    },
    {
      "policy_id": "FARE-15",
      "category": "entrance",
      "summary": "Sentosa entrance charges depend on entry time and can be waived with listed passes.",
      "source_ids": [
        "RYDE-HC-17735760737817"
      ],
      "parameters": {
        "0700_1200_sgd": 6,
        "1200_1400_sgd": 2,
        "1400_1700_sgd": 6,
        "1700_0700_sgd": 2
      },
      "status": "context_dependent",
      "interpretation_note": "Confirm actual entry, waiver documentation, and the tariff applicable to the trip."
    },
    {
      "policy_id": "CLEAN-01",
      "category": "cleaning",
      "summary": "Professional cleaning claims have severity caps for spillage, bodily fluids or stains, and vomit.",
      "source_ids": [
        "RYDE-HC-900004381243",
        "RYDE-HC-900003466206"
      ],
      "parameters": {
        "spillage_cap_sgd": 40,
        "fluids_stains_cap_sgd": 120,
        "vomit_cap_sgd": 200
      },
      "status": "discretionary",
      "interpretation_note": "Caps are not guaranteed awards; verified cost and Ryde review control reimbursement."
    },
    {
      "policy_id": "CLEAN-02",
      "category": "cleaning",
      "summary": "The vehicle must be professionally cleaned within twenty-four hours and the claim submitted within forty-eight hours.",
      "source_ids": [
        "RYDE-HC-900004381243"
      ],
      "parameters": {
        "professional_cleaning_deadline_hours": 24,
        "claim_deadline_hours": 48
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "CLEAN-03",
      "category": "cleaning",
      "summary": "Evidence must include contamination photos, plate verification and a cleaning-company receipt with specified business and verification details.",
      "source_ids": [
        "RYDE-HC-900004381243"
      ],
      "parameters": {
        "receipt_required": true,
        "plate_photo_required": true,
        "company_stamp_and_signature_required": true
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "CLEAN-04",
      "category": "cleaning",
      "summary": "Immediately cleanable mess and expected pet fur or saliva are excluded from reimbursement.",
      "source_ids": [
        "RYDE-HC-900004381243"
      ],
      "parameters": {
        "excluded": [
          "immediately_cleanable_mess",
          "pet_fur",
          "pet_saliva"
        ]
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "CLEAN-05",
      "category": "cleaning",
      "summary": "A driver can appeal the cleaning-claim outcome within twenty-four hours with additional evidence.",
      "source_ids": [
        "RYDE-HC-900004381243"
      ],
      "parameters": {
        "appeal_deadline_hours": 24
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "CLEAN-06",
      "category": "cleaning",
      "summary": "Drivers should submit claims to Ryde rather than demand payment from riders; approved driver reimbursement is separate from rider recovery.",
      "source_ids": [
        "RYDE-HC-900004381243"
      ],
      "parameters": {},
      "status": "discretionary",
      "interpretation_note": ""
    },
    {
      "policy_id": "SAFE-01",
      "category": "safety",
      "summary": "Drivers need current driving and vocational licences, required permits, and insurance.",
      "source_ids": [
        "RYDE-HC-15395890865561"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "SAFE-02",
      "category": "safety",
      "summary": "Drivers must maintain a clean functioning vehicle and must not smoke inside it.",
      "source_ids": [
        "RYDE-HC-15395890865561"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "SAFE-03",
      "category": "safety",
      "summary": "Abuse, harassment, discriminatory remarks, dangerous driving, and inappropriate personal post-trip contact require investigation.",
      "source_ids": [
        "RYDE-HC-15395890865561",
        "RYDE-WEB-COC"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": "The dataset escalates allegations; it does not infer guilt or impose sanctions."
    },
    {
      "policy_id": "SAFE-04",
      "category": "safety",
      "summary": "Seatbelts are required for riders and drivers; damaged belts should be reported through RydeHELP.",
      "source_ids": [
        "RYDE-HC-51354502165913"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "SAFE-05",
      "category": "child_seat",
      "summary": "Passengers below 1.35 metres need an appropriate restraint or booster in private-hire vehicles.",
      "source_ids": [
        "RYDE-HC-37057430899225",
        "RYDE-HC-900005469083"
      ],
      "parameters": {
        "height_threshold_m": 1.35
      },
      "status": "public_rule",
      "interpretation_note": "The dataset cites Ryde guidance, not an independent legal opinion."
    },
    {
      "policy_id": "SAFE-06",
      "category": "child_seat",
      "summary": "A rider-supplied appropriate child restraint has no surcharge; booked baby and booster options have different prices.",
      "source_ids": [
        "RYDE-HC-900005469083",
        "RYDE-HC-37057430899225"
      ],
      "parameters": {
        "rider_supplied_surcharge_sgd": 0,
        "booked_baby_seat_sgd": 3,
        "booked_child_booster_sgd": 5
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "SAFE-07",
      "category": "safety",
      "summary": "A driver can terminate a trip for safety concerns, rider guideline violations, or breakdown and should stop safely.",
      "source_ids": [
        "RYDE-HC-16925196526489"
      ],
      "parameters": {},
      "status": "context_dependent",
      "interpretation_note": ""
    },
    {
      "policy_id": "SAFE-08",
      "category": "safety",
      "summary": "A mismatched driver or vehicle can be reported with photo evidence; riders may choose alternative transport.",
      "source_ids": [
        "RYDE-HC-35170207360025"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "SAFE-09",
      "category": "privacy",
      "summary": "Dashcam guidance conflicts with the Privacy Policy camera language; refer disputes for clarification.",
      "source_ids": [
        "RYDE-HC-51812996696217",
        "RYDE-HC-33362721809049",
        "RYDE-WEB-PRIV"
      ],
      "parameters": {},
      "status": "source_conflict",
      "interpretation_note": ""
    },
    {
      "policy_id": "SAFE-10",
      "category": "pets",
      "summary": "Guide dogs are accepted across Ryde services; ordinary pet-service requirements must not be applied automatically.",
      "source_ids": [
        "RYDE-HC-4406078531097"
      ],
      "parameters": {},
      "status": "context_dependent",
      "interpretation_note": "The public article mentions religious or health concerns; do not erase these qualifications."
    },
    {
      "policy_id": "SAFE-11",
      "category": "pets",
      "summary": "RydePET specifies transport arrangements and at most two pets, each accompanied by an adult.",
      "source_ids": [
        "RYDE-HC-900004221046"
      ],
      "parameters": {
        "max_pets": 2,
        "adult_per_pet": 1
      },
      "status": "public_rule",
      "interpretation_note": "Size bands leave 40\u201341 cm unclear; capacity also depends on service and carrier/leash subtype."
    },
    {
      "policy_id": "SAFE-12",
      "category": "pets",
      "summary": "A driver can cancel an incorrectly selected pet category; accepted compliant pet rides should ordinarily be honoured.",
      "source_ids": [
        "RYDE-HC-49717696369561",
        "RYDE-HC-49718401889561"
      ],
      "parameters": {},
      "status": "context_dependent",
      "interpretation_note": ""
    },
    {
      "policy_id": "SAFE-13",
      "category": "accessibility",
      "summary": "Bulky items and wheelchairs have no surcharge; fitting and service capacity can affect cancellation.",
      "source_ids": [
        "RYDE-HC-4408080441497",
        "RYDE-HC-4408117287577",
        "RYDE-HC-17947433778713"
      ],
      "parameters": {
        "bulky_wheelchair_surcharge_sgd": 0
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "DRIVER-01",
      "category": "driver_account",
      "summary": "Published performance criteria include rating below 4.80, cancellation rate above 17.5%, and adverse or fraudulent conduct.",
      "source_ids": [
        "RYDE-HC-33362721809049"
      ],
      "parameters": {
        "rating_below": 4.8,
        "cancellation_rate_pct_above": 17.5
      },
      "status": "discretionary",
      "interpretation_note": "Investigation, no-show qualifications and right of response matter; do not automatically suspend anyone."
    },
    {
      "policy_id": "DRIVER-02",
      "category": "driver_account",
      "summary": "Ratings use recent trips and the driver policy describes the last one hundred trips.",
      "source_ids": [
        "RYDE-HC-33362721809049"
      ],
      "parameters": {
        "recent_rating_window_trips": 100
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "DRIVER-03",
      "category": "fraud",
      "summary": "Fare manipulation, ghost trips, false documents and account sharing can trigger investigation and possible sanctions.",
      "source_ids": [
        "RYDE-HC-33362721809049",
        "RYDE-HC-51618294693145"
      ],
      "parameters": {},
      "status": "discretionary",
      "interpretation_note": ""
    },
    {
      "policy_id": "DRIVER-04",
      "category": "ratings",
      "summary": "Biased, fraudulent, irrelevant or conflict-of-interest reviews can be moderated after review.",
      "source_ids": [
        "RYDE-HC-33362498168985"
      ],
      "parameters": {},
      "status": "discretionary",
      "interpretation_note": ""
    },
    {
      "policy_id": "DRIVER-05",
      "category": "driver_account",
      "summary": "Account restoration can involve an appeal or $10 excluding GST processing fee, subject to the published conditions.",
      "source_ids": [
        "RYDE-HC-33362721809049"
      ],
      "parameters": {
        "restoration_fee_sgd_exclusive_gst": 10
      },
      "status": "discretionary",
      "interpretation_note": "The stated December 2025 waiver is expired at retrieval, not a current entitlement."
    },
    {
      "policy_id": "DRIVER-06",
      "category": "driver_account",
      "summary": "Driver dormancy and closure provisions refer to one year and three years respectively; rider dormancy text is internally inconsistent.",
      "source_ids": [
        "RYDE-HC-33362721809049",
        "RYDE-HC-4410772231961"
      ],
      "parameters": {
        "driver_dormant_years": 1,
        "driver_closed_years": 3
      },
      "status": "source_conflict",
      "interpretation_note": "The rider article refers to both six months and one year; no automatic rider denial."
    },
    {
      "policy_id": "DRIVER-07",
      "category": "carpool",
      "summary": "Public carpool guidance limits paid daily trips and simultaneous pickup stacking.",
      "source_ids": [
        "RYDE-HC-115001439493"
      ],
      "parameters": {
        "max_paid_daily_trips": 2,
        "max_stacked_pickups": 2
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "DRIVER-08",
      "category": "capacity",
      "summary": "The newer service comparison describes RydePOOL as one passenger and RydeFLASH as up to four passengers.",
      "source_ids": [
        "RYDE-HC-62948637647129"
      ],
      "parameters": {
        "RydePOOL_passengers": 1,
        "RydeFLASH_passengers": 4
      },
      "status": "context_dependent",
      "interpretation_note": ""
    },
    {
      "policy_id": "SUB-01",
      "category": "subscription",
      "summary": "Ryde+ requires user initiation and initial consent; subsequent renewals follow that authorization.",
      "source_ids": [
        "RYDE-HC-51375551935129",
        "RYDE-HC-51375985332761"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "SUB-02",
      "category": "subscription",
      "summary": "Ryde+ cancellation at least one day before cycle end affects the next billing cycle.",
      "source_ids": [
        "RYDE-HC-4410127978265",
        "RYDE-HC-4410122591001"
      ],
      "parameters": {
        "cancellation_notice_hours": 24
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "SUB-03",
      "category": "subscription",
      "summary": "Published Ryde+ plans cost $19.99 monthly or $49.99 for three months, inclusive of GST.",
      "source_ids": [
        "RYDE-HC-4410127978265"
      ],
      "parameters": {
        "monthly_sgd": 19.99,
        "three_months_sgd": 49.99
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "SUB-04",
      "category": "subscription",
      "summary": "Ryde+ is non-transferable and non-refundable; subscription disputes need the actual consent and billing record.",
      "source_ids": [
        "RYDE-HC-4410127978265"
      ],
      "parameters": {},
      "status": "context_dependent",
      "interpretation_note": ""
    },
    {
      "policy_id": "SUB-05",
      "category": "subscription",
      "summary": "Listed membership cashback requires a completed qualifying ride paid through RydePAY.",
      "source_ids": [
        "RYDE-HC-27376809943705"
      ],
      "parameters": {
        "listed_cashback_pct": 3
      },
      "status": "context_dependent",
      "interpretation_note": "Promotions can change; this is not a guaranteed historical or future benefit."
    },
    {
      "policy_id": "PAY-01",
      "category": "wallet",
      "summary": "RydeCoins are platform-only and cannot ordinarily be converted into cash, transferred or refunded.",
      "source_ids": [
        "RYDE-WEB-TOU"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "PAY-02",
      "category": "payment",
      "summary": "An unpaid-trip request can authorize Ryde to share the rider number for payment arrangements.",
      "source_ids": [
        "RYDE-HC-18230595517465"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": "The mock cases use identifiers, not telephone numbers."
    },
    {
      "policy_id": "SEND-01",
      "category": "delivery",
      "summary": "A delivery trip accepts at most eight kilograms and a parcel within forty by thirty by thirty centimetres.",
      "source_ids": [
        "RYDE-HC-360008030573",
        "RYDE-WEB-TOU"
      ],
      "parameters": {
        "max_weight_kg": 8,
        "max_dimensions_cm": [
          40,
          30,
          30
        ]
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "SEND-02",
      "category": "delivery",
      "summary": "Dangerous, valuable, illegal, live, loose, counterfeit and irreproducible items appear in the prohibited-item categories.",
      "source_ids": [
        "RYDE-HC-360007924254",
        "RYDE-WEB-TOU"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": "Use the source for the complete item list; new classifications require human review."
    },
    {
      "policy_id": "SEND-03",
      "category": "delivery",
      "summary": "Fragile and bending-sensitive deliveries are at the sender risk under the published item guidance.",
      "source_ids": [
        "RYDE-HC-360008030573"
      ],
      "parameters": {},
      "status": "context_dependent",
      "interpretation_note": ""
    },
    {
      "policy_id": "SEND-04",
      "category": "delivery",
      "summary": "RydeSEND loss or damage compensation is bounded by declared item value and $100 per unique delivery trip.",
      "source_ids": [
        "RYDE-HC-4414937800473"
      ],
      "parameters": {
        "per_trip_cap_sgd": 100
      },
      "status": "discretionary",
      "interpretation_note": ""
    },
    {
      "policy_id": "SEND-05",
      "category": "delivery",
      "summary": "Delivery claim pages differ between twelve hours after completion and one day from receipt.",
      "source_ids": [
        "RYDE-HC-4414937897881",
        "RYDE-HC-360008031513"
      ],
      "parameters": {},
      "status": "source_conflict",
      "interpretation_note": "The current Terms page did not resolve the cited old clause; do not invent precedence."
    },
    {
      "policy_id": "SEND-06",
      "category": "delivery",
      "summary": "Delivery claims need value and loss or damage documentation; second-hand items are excluded by the claim guidance.",
      "source_ids": [
        "RYDE-HC-360008031513"
      ],
      "parameters": {
        "second_hand_excluded": true
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "SEND-07",
      "category": "delivery",
      "summary": "For an absent recipient, published guidance specifies ten minutes waiting and encourages at least two calls before leaving items.",
      "source_ids": [
        "RYDE-HC-360008119953",
        "RYDE-HC-360008031573"
      ],
      "parameters": {
        "wait_minutes_at_least": 10,
        "recommended_call_attempts": 2
      },
      "status": "context_dependent",
      "interpretation_note": "The calls are phrased as encouragement, not a rigid mandatory criterion."
    },
    {
      "policy_id": "SEND-08",
      "category": "delivery",
      "summary": "Return-delivery compensation recommendations differ between seventy-five and one hundred percent; private arrangements require agreement.",
      "source_ids": [
        "RYDE-HC-360008119953",
        "RYDE-HC-360007925094"
      ],
      "parameters": {},
      "status": "source_conflict",
      "interpretation_note": "These are recommendations, not a mandatory fixed return tariff."
    },
    {
      "policy_id": "SEND-09",
      "category": "driver_deposit",
      "summary": "RydeSEND deposit refunds to the driver wallet are described as processed within thirty days with a $5 fee.",
      "source_ids": [
        "RYDE-HC-360008005414",
        "RYDE-HC-50123912515865"
      ],
      "parameters": {
        "processing_days": 30,
        "processing_fee_sgd": 5
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "LOST-01",
      "category": "lost_item",
      "summary": "Direct contact for a lost item is available for up to twenty-four hours after a trip; later cases go through RydeHELP.",
      "source_ids": [
        "RYDE-HC-25969395777305"
      ],
      "parameters": {
        "contact_window_hours": 24
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "LOST-02",
      "category": "lost_item",
      "summary": "A $25 minimum return-trip payment is recommended; recovery and immediate return are not guaranteed.",
      "source_ids": [
        "RYDE-HC-25969395777305"
      ],
      "parameters": {
        "recommended_minimum_sgd": 25
      },
      "status": "public_rule",
      "interpretation_note": "A recommendation is not a mandatory lost-item penalty."
    },
    {
      "policy_id": "DATA-01",
      "category": "privacy",
      "summary": "Personal data must be used for its disclosed purpose; retention follows need and lawful exceptions, rather than an arbitrary fixed deletion period.",
      "source_ids": [
        "RYDE-WEB-TOU",
        "RYDE-WEB-PRIV"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "DATA-02",
      "category": "privacy",
      "summary": "Privacy requests can seek access, correction, deletion or consent withdrawal, subject to identity checks and applicable requirements.",
      "source_ids": [
        "RYDE-WEB-PRIV"
      ],
      "parameters": {},
      "status": "context_dependent",
      "interpretation_note": ""
    },
    {
      "policy_id": "DATA-03",
      "category": "privacy",
      "summary": "Corporate accounts disclose relevant business-tagged trip and booking information to the client.",
      "source_ids": [
        "RYDE-WEB-PRIV"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": "Do not disclose unrelated personal rides on the basis of a business profile alone."
    },
    {
      "policy_id": "DATA-04",
      "category": "privacy",
      "summary": "Account deletion uses the app request process; pending payments and non-transferable RydeCoins require attention.",
      "source_ids": [
        "RYDE-HC-18443816997913"
      ],
      "parameters": {
        "stated_processing_weeks_up_to": 2
      },
      "status": "public_rule",
      "interpretation_note": ""
    },
    {
      "policy_id": "WORK-01",
      "category": "driver_earnings",
      "summary": "CPF calculation guidance uses net earnings after transport-specific fixed expense deductions.",
      "source_ids": [
        "RYDE-HC-42604197014041"
      ],
      "parameters": {
        "car_van_lorry_truck_feda_pct": 60,
        "motorcycle_power_assisted_bicycle_feda_pct": 35,
        "bicycle_walker_feda_pct": 20
      },
      "status": "public_rule",
      "interpretation_note": "These are deduction inputs, not CPF contribution rates. Rates need the applicable official calculator and worker details."
    },
    {
      "policy_id": "WORK-02",
      "category": "driver_earnings",
      "summary": "Monthly total CPF rounding and the platform-worker share have different published rounding treatment.",
      "source_ids": [
        "RYDE-HC-48729103790361"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": "Preserve gross/net and worker/operator distinctions; do not advise on an individual tax case."
    },
    {
      "policy_id": "WORK-03",
      "category": "insurance",
      "summary": "Public injury guidance points platform workers to WICA processes; passenger accident guidance refers to the driver insurance.",
      "source_ids": [
        "RYDE-HC-43870027896601",
        "RYDE-HC-115000777634"
      ],
      "parameters": {},
      "status": "context_dependent",
      "interpretation_note": "Do not promise cover or payout without the applicable insurance contract."
    },
    {
      "policy_id": "TERMS-01",
      "category": "governance",
      "summary": "The Terms allow assistance and discretionary cancellation refunds despite broad payment finality language.",
      "source_ids": [
        "RYDE-WEB-TOU"
      ],
      "parameters": {},
      "status": "discretionary",
      "interpretation_note": "A training candidate is not a Ryde refund decision."
    },
    {
      "policy_id": "TERMS-02",
      "category": "governance",
      "summary": "Ryde policies can change; service-specific terms, in-app details and applicable agreements need review for each case.",
      "source_ids": [
        "RYDE-WEB-TOU"
      ],
      "parameters": {},
      "status": "public_rule",
      "interpretation_note": ""
    }
  ],
  "conflicts": [
    {
      "id": "CONFLICT-01",
      "topic": "Waiting fee amount",
      "source_ids": [
        "RYDE-HC-23534478435353",
        "RYDE-HC-4407754403353"
      ],
      "description": "Main rider policy lists $5 for completed-trip waiting; the arrival FAQ calls $6.61 a waiting fee. Verify fee type and receipt rather than substituting amounts."
    },
    {
      "id": "CONFLICT-02",
      "topic": "RydePOOL ERP",
      "source_ids": [
        "RYDE-HC-115000772653",
        "RYDE-HC-115001438614",
        "RYDE-HC-4408072389913",
        "RYDE-HC-23575142762393"
      ],
      "description": "Pages differ on inclusion and whether half is shared with a driver or other riders. Service-specific contract or Ryde confirmation is required."
    },
    {
      "id": "CONFLICT-03",
      "topic": "RydeHIRE ERP",
      "source_ids": [
        "RYDE-HC-4408072421785",
        "RYDE-HC-115000772653"
      ],
      "description": "Hire-specific guidance includes tolls whereas the broad ERP FAQ says only SEND includes them."
    },
    {
      "id": "CONFLICT-04",
      "topic": "Delivery claim deadline",
      "source_ids": [
        "RYDE-HC-4414937897881",
        "RYDE-HC-360008031513"
      ],
      "description": "Twelve hours after completion versus one day from receipt. No source hierarchy is asserted."
    },
    {
      "id": "CONFLICT-05",
      "topic": "Delivery return payment",
      "source_ids": [
        "RYDE-HC-360008119953",
        "RYDE-HC-360007925094"
      ],
      "description": "Recommendations of 75% versus 100%; private agreement is relevant and neither is encoded as a mandatory tariff."
    },
    {
      "id": "CONFLICT-06",
      "topic": "Dashcams",
      "source_ids": [
        "RYDE-HC-51812996696217",
        "RYDE-WEB-PRIV"
      ],
      "description": "Driver guidance prohibits cameras while Privacy Policy camera language says personal cameras are neither endorsed nor prohibited."
    },
    {
      "id": "CONFLICT-07",
      "topic": "Rider dormancy",
      "source_ids": [
        "RYDE-HC-4410772231961"
      ],
      "description": "Same article mentions both six months and one year. Escalate rather than infer the current threshold."
    },
    {
      "id": "GAP-01",
      "topic": "Exact advance boundary",
      "source_ids": [
        "RYDE-HC-23534478435353"
      ],
      "description": "The page says free if more than fifteen minutes before pickup and charged if less; exactly fifteen minutes is unclear."
    },
    {
      "id": "GAP-02",
      "topic": "Geofence and route refund",
      "source_ids": [
        "RYDE-HC-4412121982745",
        "RYDE-HC-4407754403353"
      ],
      "description": "No public numeric pickup geofence or distance-percentage refund threshold found. Existing mock 50/100 m and 10/20% rules are not adopted."
    },
    {
      "id": "GAP-03",
      "topic": "Transaction fee calculation",
      "source_ids": [
        "RYDE-HC-52596204611993"
      ],
      "description": "Percentages are listed but rounding and complete calculation base are not fully specified."
    },
    {
      "id": "GAP-04",
      "topic": "Image tables and old material",
      "source_ids": [
        "RYDE-HC-17947433778713",
        "RYDE-WEB-COC"
      ],
      "description": "Some capacity details are image-only; old pandemic-mask text and expired December 2025 restoration waivers are not used as current enforcement rules."
    }
  ]
};
