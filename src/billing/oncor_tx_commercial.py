"""Small-commercial Electricity Facts Labels for Oncor meters.

NEC changes its rate on the invoice issue date and requires single-phase
secondary service below 10 kW. Ambit prices attach to a signed fixed-term
contract and apply to both of the secondary delivery schedules below.
Money fields are dollars. See docs/Oncor_Commercial_Plans.md for the sources.
"""

_AMBIT_SOURCES = "https://mediaserver.ambitenergy.com//media/get/"
_AMBIT_LABELS = (
    (12, "0.1290", "TSC1YTCNG12_555_283_1",
     "035d9baaba6852bdfbab58f1798a5f3b1468e8a433de187acbd5f49e6231dd9c"),
    (24, "0.1150", "TSC24MTCNG24_557_283_1",
     "5ab403130010afde5cbf65c1abd2f49006644bb6bb2c767af5b0d7646963bfb9"),
)
COMMERCIAL_OFFERS = {
    f"ambit_tsc{months}_20250510_{suffix}": {
        "supplier": "Ambit Texas, LLC",
        "product": f"Ambit TSC {months}-month fixed",
        "label_date": "2025-05-10",
        "source": _AMBIT_SOURCES + document,
        "version": document + "250510",
        "sha256": sha256,
        "terms": _AMBIT_SOURCES + "TSCTermsOfService/en",
        "term_months": months,
        "monthly": "0.00",
        "per_kwh": rate,
        "usage_fee_below_kwh": 1250,
        "usage_fee_usd": "9.99",
        "schedule": schedule,
        "puca_treatment": "unverified",
    }
    for months, rate, document, sha256 in _AMBIT_LABELS
    for suffix, schedule in (("le10", "secondary_le_10_kw"), ("gt10", "secondary_gt_10_kw"))
}

_LABEL_ROOT = "https://neccoopenergy.com/wp-content/uploads/"

# Bill date, final verified bill date inclusive, REP $/kWh, TDU $/month,
# TDU $/kWh, EFL source, and published comparison prices (cents/kWh at
# 1,500 / 2,500 / 3,500 kWh). The REP base charge is $7.50 in every label.
_LABELS = (
    ("2025-02-01", "2025-02-28", "0.0688", "6.87", "0.0447",
     "2025/01/EFL-2-1-25-SM-COMM-_Oncor.pdf", ("12.3", "11.9", "11.8")),
    ("2025-05-01", "2025-05-31", "0.0963", "6.87", "0.046202",
     "2025/04/EFL-5-1-25-SM-COMM-_Oncor.pdf", ("15.2", "14.8", "14.7")),
    ("2025-09-01", "2025-09-30", "0.0983", "6.87", "0.045753",
     "2025/08/EFL-9-1-25-SM-COMM-_Oncor.pdf", ("15.4", "15", "14.8")),
    ("2025-10-01", "2025-10-02", "0.0841", "6.87", "0.045753",
     "2025/10/EFL-10-1-25-SM-COMM-_Oncor.pdf", ("13.9", "13.6", "13.4")),
    ("2025-10-03", "2025-10-31", "0.0781", "6.87", "0.045753",
     "2025/10/EFL-10-3-25-SM-COMM-_Oncor.pdf", ("13.3", "13", "12.8")),
    ("2025-11-01", "2025-11-30", "0.0741", "6.87", "0.045753",
     "2025/10/EFL-11-1-25-SM-COMM-_Oncor.pdf", ("12.9", "12.6", "12.4")),
    ("2025-12-01", "2025-12-31", "0.0691", "6.87", "0.046229",
     "2025/12/EFL-12-1-25-SM-COMM-_Oncor.pdf", ("12.5", "12.1", "11.9")),
    ("2026-01-01", "2026-01-31", "0.0781", "6.87", "0.046229",
     "2025/12/EFL-1-1-26-SM-COMM-_Oncor.pdf", ("13.4", "13", "12.8")),
    ("2026-02-01", "2026-02-28", "0.0799", "6.87", "0.045623",
     "2026/01/EFL-2-1-26-SM-COMM-_Oncor.pdf", ("13.5", "13.1", "13")),
    ("2026-03-01", "2026-03-31", "0.0869", "6.87", "0.045874",
     "2026/02/EFL-3-1-26-SM-COMM-_Oncor.pdf", ("14.2", "13.9", "13.7")),
    ("2026-04-01", "2026-04-30", "0.0877", "6.87", "0.045874",
     "2026/03/EFL-4-1-26-SM-COMM-_Oncor.pdf", ("14.3", "13.9", "13.8")),
    ("2026-05-01", "2026-05-31", "0.0944", "6.87", "0.045874",
     "2026/04/EFL-5-1-26-SM-COMM-_Oncor.pdf", ("15", "14.6", "14.4")),
    ("2026-06-01", "2026-06-30", "0.0974", "6.70", "0.049532",
     "2026/05/EFL-6-1-26-SM-COMM-_Oncor.pdf", ("15.6", "15.3", "15.1")),
    ("2026-07-01", "2026-07-31", "0.0994", "6.70", "0.049532",
     "2026/06/EFL-7-1-26-SM-COMM-_Oncor.pdf", ("15.8", "15.5", "15.3")),
    ("2026-09-01", "2026-09-30", "0.0944", "6.70", "0.051227",
     "2026/08/EFL-9-1-26-SM-COMM-_Oncor.pdf", ("15.5", "15.1", "15")),
    ("2026-10-01", "2026-10-31", "0.0878", "6.70", "0.053843",
     "2026/09/EFL-10-1-26-SM-COMM-_Oncor.pdf", ("15.1", "14.7", "14.6")),
    ("2026-11-01", "2026-11-19", "0.0778", "6.70", "0.053843",
     "2026/10/EFL-11-1-26-SM-COMM-_Oncor.pdf", ("14.1", "13.7", "13.6")),
)

NEC_COMMERCIAL_RATES = {
    bill_start: {
        "supplier": "NEC Co-op Energy",
        "name": "Small Commercial Service",
        "label_date": bill_start,
        "bill_end": bill_end,
        "term_months": 0,
        "monthly": "7.50",
        "per_kwh": supply_rate,
        "delivery_monthly": delivery_fixed,
        "delivery_per_kwh": delivery_rate,
        "source": _LABEL_ROOT + pdf_path,
        "average_cents": average_cents,
    }
    for bill_start, bill_end, supply_rate, delivery_fixed, delivery_rate, pdf_path, average_cents
    in _LABELS
}

