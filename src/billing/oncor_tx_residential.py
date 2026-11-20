"""Source rows for residential retail service in Oncor's delivery area.

Money fields are decimal strings in dollars/month and dollars/kWh. Published
average prices are in cents/kWh at 500, 1,000 and 2,000 kWh. NEC delivery
references describe the EFL examples and may differ from the TDU tariff.
"""

_CONSTELLATION = "https://www.constellation.com/bin/residential/GetContractVersionPDF?versionNum="
_NEC_UPLOADS = "https://neccoopenergy.com/wp-content/uploads/"


# Distinct documents for the same fixed-price product. Actual initial meter
# read and contract enrollment establish the service term.
def _fixed_offer(version, label_date, per_kwh, averages, sha256):
    return {
        "product": "Constellation residential fixed",
        "name": "12 Month Residential Fixed Rate",
        "supplier": "Constellation NewEnergy, Inc.",
        "label_date": label_date,
        "term_months": 12,
        "monthly": "0.00",
        "per_kwh": per_kwh,
        "average_cents": averages,
        "source": _CONSTELLATION + version,
        "terms": _CONSTELLATION + "4863156",
        "puca_treatment": "separately_reimbursed",
        "sha256": sha256,
    }


def _fourchange_offer(source, label_date, per_kwh, averages, sha256):
    return {
        "product": "4Change Energy One Rate 24",
        "name": "One Rate 24",
        "supplier": "Value Based Brands LLC dba 4Change Energy",
        "label_date": label_date,
        "term_months": 24,
        "monthly": "4.95",
        "per_kwh": per_kwh,
        "average_cents": averages,
        "source": source,
        "sha256": sha256,
        "terms": "https://www.4changeenergy.com/docs/TOSA_4ChangeEnergy.pdf",
        "enrollment_confirmation": (
            "Active paperless service with a valid email, standard 9% renewable selection, "
            "ordinary monthly billing and no optional products, payment fees or contract amendments"
        ),
        "positive_usage_required": True,  # The terms permit a fee for a zero-use cycle.
        "puca_treatment": "unverified",
    }


RESIDENTIAL_OFFERS = {
    "constellation_310745": _fixed_offer(
        "310745", "2024-12-06", "0.1040", ("16.6", "16.1", "15.9"),
        "436e1c318a7bb8d6332e1ac06fd83e86533a40fdec5534bbca5aabdc4ca64307",
    ),
    "constellation_381771": _fixed_offer(
        "381771", "2025-05-01", "0.1130", ("17.2", "16.8", "16.5"),
        "936eb0ae529215440813dee0d8a1066bc46b8ef506cc569716e9ea39f8a10aa2",
    ),
    "constellation_4930520": _fixed_offer(
        "4930520", "2026-04-01", "0.0885", ("15.3", "14.9", "14.7"),
        "b15988c655da2954eed5de664b0da49341c7c7384c9c11bfcd4565d21bfa3f42",
    ),
    "fourchange_onerta24lah_o": _fourchange_offer(
        "https://www.4changeenergy.com/docs/efl_onerta24lah_o.pdf",
        "2024-09-01", "0.098273", ("16.9", "15.9", "15.5"),
        "060cc25f2fea3d67310ba53c13210117841019a2517d68650a6cd69251807e4f",
    ),
    "fourchange_onerta24mac_o": _fourchange_offer(
        "https://www.4changeenergy.com/Docs2/efl_onerta24mac_o.pdf",
        "2025-09-02", "0.107278", ("18.2", "17.2", "16.8"),
        "f9c24bf8055d302f6cc7ce9bdeb4b2be8c06d76939783500a3b1245e46842cee",
    ),
}

# First and last bill issue date, REP energy, example delivery (monthly and
# per kWh), published average cents, issuer's PDF location and SHA-256.
_NEC_EFLS = (
    ("2025-02-01", "2025-02-28", "0.0688", "4.23", "0.0529", ("14.5", "13.4", "12.8"),
     "2025/01/EFL-2-1-25-RESIDENTIAL-Oncor.pdf",
     "f274e81870e91d4cb66cceb1898a709ab4595bb1fd48f07be41fe935f8a457f5"),
    ("2025-03-01", "2025-03-31", "0.0853", "4.23", "0.05008", ("15.9", "14.7", "14.1"),
     "2025/02/EFL-3-1-25-RESIDENTIAL-Oncor.pdf",
     "523e88e9c2a562abb6d0dc272c9aeb4ba16cf37d1fe5f9e0a4badc969f4163b8"),
    ("2025-04-01", "2025-04-30", "0.0923", "4.23", "0.050029", ("16.6", "15.4", "14.8"),
     "2025/03/EFL-4-1-25-RESIDENTIAL-Oncor.pdf",
     "732afd5e89c36558789b0ccf5081306f6cf13114a9ed92f3df541496dd87fd8f"),
    ("2025-05-01", "2025-05-31", "0.0963", "4.23", "0.051248", ("17.1", "15.9", "15.3"),
     "2025/04/EFL-5-1-25-RESIDENTIAL-Oncor.pdf",
     "e6fca3a15429965d7e0cb0f04316a5e7b13f068559c5b2fce619604dc5afa964"),
    ("2025-06-01", "2025-06-30", "0.1022", "4.23", "0.051248", ("17.7", "16.5", "15.9"),
     "2025/05/EFL-6-1-25-RESIDENTIAL-Oncor.pdf",
     "cb51d31c4257d7374517f3753cdd32a83ab2d4909f8da6840ff5996f5f8bd0d6"),
    ("2025-07-01", "2025-07-31", "0.1032", "4.23", "0.051248", ("17.8", "16.6", "16"),
     "2025/06/EFL-7-1-25-RESIDENTIAL-Oncor.pdf",
     "4efa1e0a5390f6517e9933e449f2340331c23c5a584a7bafe261a47f4836ef09"),
    ("2025-08-01", "2025-08-31", "0.102", "4.23", "0.051248", ("17.7", "16.5", "15.9"),
     "2025/07/EFL-8-1-25-RESIDENTIAL-Oncor.pdf",
     "f7b89a565a2023f66739f0cc205ea81fc9e214c49bc0e874d735bd4c4d8c2198"),
    ("2025-09-01", "2025-09-30", "0.0983", "4.23", "0.056032", ("17.8", "16.6", "16"),
     "2025/08/EFL-9-1-25-RESIDENTIAL-Oncor.pdf",
     "7248e64db41546b795da1f8127e3decd4eba98ab52af1ea130dccc312ea84674"),
    ("2025-10-01", "2025-10-02", "0.0841", "4.23", "0.056032", ("16.4", "15.2", "14.6"),
     "2025/10/EFL-10-1-25-RESIDENTIAL-Oncor.pdf",
     "46c0c4f49717bb8e75f7af8706f52f7c3a9f85ee29619d26930b05ed42257b63"),
    ("2025-10-03", "2025-10-31", "0.0781", "4.23", "0.056032", ("15.8", "14.6", "14"),
     "2025/10/EFL-10-3-25-RESIDENTIAL-Oncor.pdf",
     "0dac452a1133698cfa43c094ec36a053b8b7761f32262916b10749ab8f36f116"),
    ("2025-11-01", "2025-11-30", "0.0741", "4.23", "0.056032", ("15.4", "14.2", "13.6"),
     "2025/10/EFL-11-1-25-RESIDENTIAL-Oncor.pdf",
     "e35389dd1bd93c20f5f793fb1b31df59f8fbdcb65f9a2baad40b01e825d6164b"),
    ("2025-12-01", "2025-12-31", "0.0691", "4.23", "0.05686", ("14.9", "13.8", "13.2"),
     "2025/12/EFL-12-1-25-RESIDENTIAL-Oncor.pdf",
     "5f171fc9dabd1b6f47e37e98682b2ea8ab4eaf996e6b26458504ca4bdfa75b54"),
    ("2026-01-01", "2026-01-31", "0.0781", "4.23", "0.05686", ("15.8", "14.7", "13.2"),
     "2025/12/EFL-1-1-26-RESIDENTIAL-Oncor.pdf",
     "78e54251c88900bafed611b22004bbc5dfb7af61c036d6496a84166af7d97f46"),
    ("2026-02-01", "2026-02-28", "0.0799", "4.23", "0.055833", ("15.9", "14.7", "14.2"),
     "2026/01/EFL-2-1-26-RESIDENTIAL-Oncor.pdf",
     "7fc14fd111b2f82d97be8d1518850d27b05e29059ace904052936d52be00c92a"),
    ("2026-03-01", "2026-03-31", "0.0869", "4.23", "0.056183", ("16.7", "15.5", "14.9"),
     "2026/02/EFL-3-1-26-RESIDENTIAL-Oncor.pdf",
     "1b6825b51fd67afa0645ba19c2d183e19afcd64899c4ed085fcd87d122183fd6"),
    ("2026-04-01", "2026-04-30", "0.0877", "4.23", "0.056183", ("16.7", "15.6", "15"),
     "2026/03/EFL-4-1-26-RESIDENTIAL-Oncor.pdf",
     "0ef51c54545ab344804e1284dd2b4486f5aec4b03b1b0672903244a8e9b5a495"),
    ("2026-05-01", "2026-05-31", "0.0944", "4.23", "0.056183", ("17.4", "16.2", "15.6"),
     "2026/04/EFL-5-1-26-RESIDENTIAL-Oncor.pdf",
     "5525ef6cf766c400bb50a714ab323b493c33fad5b5a629bd4cf9e04c98b6d42c"),
    ("2026-06-01", "2026-06-30", "0.0974", "4.06", "0.061196", ("18.2", "17", "16.4"),
     "2026/05/EFL-6-1-26-RESIDENTIAL-Oncor.pdf",
     "d0fbbd467e105bfecef65887c5c01839eeb46df4286e4633a96dfa1f83d6f944"),
    ("2026-07-01", "2026-07-31", "0.0994", "4.06", "0.061196", ("18.4", "17.2", "16.6"),
     "2026/06/EFL-7-1-26-RESIDENTIAL-Oncor.pdf",
     "fa15c299771f13f187f5c7fe14e3d23f1f64cbe378d8a269656edfca919685ea"),
    ("2026-08-01", "2026-08-31", "0.1008", "4.06", "0.060295", ("18.4", "17.3", "16.7"),
     "2026/07/EFL-8-1-26-RESIDENTIAL-Oncor.pdf",
     "91be0d9fe8d5f197aa1db1b4b5f18b11b2d714292a0edc3498fef446de28ebb2"),
    ("2026-09-01", "2026-09-30", "0.0944", "4.06", "0.060295", ("17.8", "16.6", "16.1"),
     "2026/08/EFL-9-1-26-RESIDENTIAL-Oncor.pdf",
     "5e3c1d2989f777eb8480a399f6d146f6314b01e521dccda191fa261f4c480541"),
    ("2026-10-01", "2026-10-31", "0.0878", "4.06", "0.068673", ("18.8", "16.8", "16.2"),
     "2026/09/EFL-10-1-26-RESIDENTIAL-Oncor.pdf",
     "916f597e250aed0367c94d27e42a1353f7ec1a2c2fadef5b8be68b8cb7356dc7"),
    ("2026-11-01", "2026-11-19", "0.0778", "4.06", "0.068673", ("17", "15.8", "15.2"),
     "2026/10/EFL-11-1-26-RESIDENTIAL-Oncor.pdf",
     "f231d1ac3eae2f1e34e38f55991a4adc5a2c24a38c1a4461269869358602308c"),
)

# These EFLs disagree with one of their own three published example prices.
# Keep the evidence available for inspection and flag it for callers.
_NEC_EXAMPLE_CONFLICTS = {
    "2025-02-01", "2026-01-01", "2026-09-01", "2026-10-01",
}

NEC_RESIDENTIAL_LABELS = {
    first: {
        "supplier": "NEC Co-op Energy",
        "name": "Residential Plan Variable Price Product",
        "label_date": first,
        "bill_end": last,
        "term_months": 0,
        "monthly": "7.50",
        "per_kwh": energy,
        "delivery_monthly": delivery_monthly,
        "delivery_per_kwh": delivery_energy,
        "average_cents": average_cents,
        "benchmark_matches": first not in _NEC_EXAMPLE_CONFLICTS,
        "source": _NEC_UPLOADS + path,
        "sha256": sha256,
    }
    for first, last, energy, delivery_monthly, delivery_energy, average_cents, path, sha256
    in _NEC_EFLS
}

NEC_RESIDENTIAL_RATES = {
    first: label for first, label in NEC_RESIDENTIAL_LABELS.items() if label["benchmark_matches"]
}
