"""Delmarva Delaware filed complete-calendar intersections, PSC Del. No. 8."""
BOOK_2025 = ("https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/"
             "blt62f3e22e86bbad0a/68bf19565c76c08916ee2704/"
             "2025.09.05_filing_DPL_DE_Electric_Primary_tar.pdf?branch=prod_alias")
BOOK_2026 = ("https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/"
             "blt62f3e22e86bbad0a/6a9889810528b53e0f1e5df6/"
             "2026.08.21_filing_DPL_DE_Electric_Primary_tar_.pdf")
RPCR_TABLE = ("https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/"
              "blt1075ed3a862f315b/6a0f4a312b4519b154cb738a/"
              "RPCR_Table_I-net_posting_eff_June_to_December_.pdf")
TAX_SOURCE = "https://delcode.delaware.gov/title30/c055/"
ASSESSMENT_SOURCE = ("https://depsc.delaware.gov/wp-content/uploads/sites/54/2023/11/"
                     "Consent-Item-1C-Docket-No.-23-1398-Order-10329.pdf")
COVERAGE = (("2025-12-01", "2025-12-31"), ("2026-09-01", "2026-11-30"))
GAPS = (
    ("2025-01-01", "2025-11-30", "Earlier QFCP-RC factors and composite intersections are unverified."),
    ("2026-01-01", "2026-08-31", "Superseded DSIC and transmission versions or July transition allocation are unverified."),
    ("2026-12-01", "2026-12-31", "December 9 interim base-rate transition allocation is unverified."),
)
SOURCES = [BOOK_2025, BOOK_2026, RPCR_TABLE, TAX_SOURCE, ASSESSMENT_SOURCE]


def rates_for_month(month, plan):
    if plan not in ("R", "SGS-ND"):
        raise ValueError("Select Delmarva Delaware R or SGS-ND fixed-price SOS.")
    if not any(start[:7] <= month <= end[:7] for start, end in COVERAGE):
        raise ValueError(f"Delmarva Delaware component intersection is unverified for {month}. "
                         "Select December 2025 or September–November 2026 complete cycles.")
    rs = plan == "R"
    old = month == "2025-12"
    summer = month[5:7] in ("06", "07", "08", "09")
    if old:
        customer, delivery = (13.50, .046594) if rs else (18.77, .062487)
        supply = .094804 if rs else .084689
    else:
        customer, delivery = (14.72, .050660) if rs else (19.79, .070076)
        supply = (.111063 if summer else .114049) if rs else (.103985 if summer else .099489)
    return dict(
        customer=customer, distribution=delivery, supply=supply,
        green_energy=.000356, low_income=.000095,
        renewable_portfolio=.005795 if old else .005172,
        qualified_fuel_cell=.003860 if old else .004042,
        procurement_cost_adjustment=.000957 if old else .004997,
        energy_efficiency=(.000476 if old else .000874) if rs else 0.,
        edit_credit=0., storm_expense=0., ufrc_fraction=0.,
        dsic_fraction=.0532 if old else 0.,
        transmission_per_kw=5.782620 if old else 5.952635,
        public_utility_tax=0. if rs else .0425,
        sources=[BOOK_2025 if old else BOOK_2026, RPCR_TABLE, TAX_SOURCE, ASSESSMENT_SOURCE],
        source_version="de-2025-12" if old else "de-2026-09" if summer else "de-2026-10",
    )
