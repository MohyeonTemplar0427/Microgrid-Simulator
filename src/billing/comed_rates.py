"""Filed residential ComEd composite rates; all money is USD, not cents.

Coverage is by utility BILLING MONTH, not the filing date on each sheet.
See docs/ComEd_Residential_Billing.md and the retained source manifest.
"""
from dataclasses import dataclass, replace
from calendar import monthrange
from datetime import date
from decimal import Decimal as D
from types import MappingProxyType

from .plans import RatePlan, RatePlanIdentity

RATEBOOK_URL = (
    "https://www.comed.com/cdn/assets/v3/assets/blt3ebb3fed6084be2a/"
    "blt86ebee5fe6ed02f8/6ab16afb15d5b73190b00e59/2026_Ratebook.pdf?branch=prod_alias"
)
RATEBOOK_SHA256 = "0e3f2ee2fcd2658e41312bc50afbda08a5830f8efaf761430c83e09abff65de1"


@dataclass(frozen=True)
class DeliveryRates:
    customer: D
    meter: D
    distribution: D
    iedt: D
    revenue_balancing_factor: D


# Informational sheets 64.1 (PDF p848) and 18 (p799).
DELIVERY = MappingProxyType({
    "single_family_non_electric_heat": DeliveryRates(D("13.26"), D("3.52"), D(".05698"), D(".00124"), D(".007668")),
    "multi_family_non_electric_heat": DeliveryRates(D("9.76"), D("3.52"), D(".04354"), D(".00124"), D(".011682")),
    "single_family_electric_heat": DeliveryRates(D("15.09"), D("3.52"), D(".02712"), D(".00124"), D(".069810")),
    "multi_family_electric_heat": DeliveryRates(D("10.57"), D("3.52"), D(".02576"), D(".00124"), D(".064486")),
})

# The 2025 column is corroborated by the January and July 2025 revisions;
# later revisions change 2026/2027 columns, not these 2025 base charges.
DELIVERY_2025 = MappingProxyType({
    "single_family_non_electric_heat": DeliveryRates(D("12.97"), D("3.52"), D(".05269"), D(".00124"), D(0)),
    "multi_family_non_electric_heat": DeliveryRates(D("9.61"), D("3.52"), D(".04025"), D(".00124"), D(0)),
    "single_family_electric_heat": DeliveryRates(D("14.84"), D("3.52"), D(".02523"), D(".00124"), D(0)),
    "multi_family_electric_heat": DeliveryRates(D("10.44"), D("3.52"), D(".02399"), D(".00124"), D(0)),
})
DELIVERY_BY_YEAR = MappingProxyType({2025: DELIVERY_2025, 2026: DELIVERY})

# Valid throughout the composite Sep/Oct 2026 window. Explicitly re-verify
# these factors before adding a version outside that window.
IDUF = D("1.0217")       # sheet 20, p801
DRAF = D(".006785")      # sheet 9, p790: 0.6785%, not 0.6785
EDAF = D("0")            # sheet 62, p845
TPAF = D(".06551")       # sheet 65, p866: 6.551%
DGRA = D(".00062")       # sheet 56, p839
RCA = D(".91")           # .05 + .80 + .06: pp394, 396, 824; CB/POR zero p803
LID_RECOVERY = D("1.35")  # sheet 74, p876 (not the means-tested discount)
CAPACITY = D("10.10121") # sheet 4, p785; already includes uncollectible factors
# BESH uses SYSTEM AVERAGE factors, including system-average distribution loss.
HEC_MULTIPLIER = D("1.0124") * D(".9968") * D("1.0406")  # pp60, 801, 802, 814
COMMON_ENERGY = MappingProxyType({
    "environmental_cost_recovery": (D(".00007"), 789),
    "renewable_portfolio_standard": (D(".00516"), 817),
    "zero_emission_standard": (D(".00069"), 820),
    "energy_efficiency_programs": (D(".00369"), 821),
    "energy_transition_assistance": (D(".00084"), 822),
})


@dataclass(frozen=True)
class ComEdVersion:
    tariff_id: str
    effective_start: date
    effective_end: date
    bes_energy: D
    bes_transmission: D
    bes_adjustment: D
    besh_transmission: D
    besh_procurement: D
    besh_adjustment: D | None
    carbon_free_adjustment: D
    coal_to_solar: D
    # A composite owns its applicable factors. Never extend global constants
    # backwards when a new monthly supply sheet is retrieved.
    capacity: D = CAPACITY
    hec_multiplier: D = HEC_MULTIPLIER
    residential_iduf: D = IDUF
    nonresidential_iduf: D = D("1.0042")
    large_iduf: D = D("1.0005")
    environmental_cost_recovery: D = D(".00007")
    zero_emission_standard: D = D(".00069")
    source_references: tuple = ()
    delivery_year: int = 2026
    delivery_reconciliation: D = DRAF
    excess_deferred_income_tax: D = EDAF
    total_plan_adjustment: D = TPAF
    distributed_generation_adjustment: D = DGRA
    residential_assessment: D = RCA
    small_commercial_assessment: D = D("8.50")
    large_commercial_assessment: D = D("337.50")
    residential_lid_recovery: D | None = LID_RECOVERY
    small_commercial_lid_recovery: D | None = D("13.50")
    large_commercial_lid_recovery: D | None = D("506.25")
    renewable_portfolio_standard: D = D(".00516")
    energy_efficiency_programs: D = D(".00369")
    small_commercial_efficiency: D = D(".00876")
    large_commercial_efficiency: D = D(".00482")
    energy_transition_assistance: D = D(".00084")
    # WH, demand, space-heat PECs and nonresidential PSC; dollars, already
    # uplifted on the filed sheets. No month-number-only commercial lookup.
    commercial_supply: tuple = ()
    # Maps logical component pages to dated document IDs and actual pages.
    component_sources: tuple = ()

    def __post_init__(self):
        if self.delivery_year != self.effective_start.year or self.delivery_year not in DELIVERY_BY_YEAR:
            raise ValueError("A composite must explicitly select its verified delivery year.")
        if len(self.commercial_supply) != 4:
            raise ValueError("A composite requires verified commercial supply subgroups.")

    def is_effective_on(self, day: date) -> bool:
        return self.effective_start <= day <= self.effective_end


# Supply: sheets 1..7 (pp782..788); CFRA sheet36.1 (p818); CTS sheet63 (p846).
VERSIONS = (
    # ERM26-082 pp4-9, ERM26-087 pp3-4; CFRA is independently
    # corroborated by the later ratebook p818. Cents divided by 100.
    ComEdVersion("comed_residential_2026_06", date(2026, 6, 1), date(2026, 6, 30),
                 D(".08677"), D(".01722"), D(".00230"), D(".01074"),
                 D(".00134"), D("-.00191"), D("-.01344"), D(".00009"),
                 capacity=D("10.11236"),
                 hec_multiplier=D("1.0124")*D(".9979")*D("1.0406"),
                 residential_iduf=D("1.0206"), nonresidential_iduf=D("1.0054"),
                 large_iduf=D("1.0015"), environmental_cost_recovery=D(".00009"),
                 zero_emission_standard=D(".00087"),
                 commercial_supply=tuple(map(D, (".08702", ".08810", ".07647", ".01703"))),
                 source_references=("ERM26-082", "ERM26-087", "ERM26-086", "2026-ratebook")),
    ComEdVersion("comed_residential_2026_09", date(2026, 9, 1), date(2026, 9, 30),
                 D(".08678"), D(".01723"), D("-.00087"), D(".01073"),
                 D(".00134"), D(".00385"), D("-.01628"), D(".00009"),
                 commercial_supply=tuple(map(D, (".08704", ".08813", ".07649", ".01704")))),
    ComEdVersion("comed_residential_2026_10", date(2026, 10, 1), date(2026, 10, 31),
                 D(".08413"), D(".01690"), D("-.01551"), D(".01075"),
                 D(".00226"), D("-.02296"), D("-.00115"), D(".00008"),
                 commercial_supply=tuple(map(D, (".08433", ".08470", ".08111", ".01672")))),
)


# Immutable historical revisions. The public ICC "currentbooks" URL and the
# bare Contentstack Ratebook.pdf changed to 2026 when downloaded; neither
# search snippets nor their former 2025 contents establish historical rates.
def _book(revision):
    return ("https://www.comed.com/cdn/assets/v3/assets/blt3ebb3fed6084be2a/"
            "blt86ebee5fe6ed02f8/" + revision + "/2025_Ratebook.pdf?branch=prod_alias")


DOCUMENTS = MappingProxyType({
    "2026-ratebook": (RATEBOOK_URL, RATEBOOK_SHA256),
    "2025-january": (_book("678aca912c996f726133ec1e"), "c21cff91a15fca94ba0e550337b882f3548c79d6f773ae885c83fa1f54818b5e"),
    "2025-july": (_book("6866e86afa0c450033ffa359"), "4f0c86402a10a21e85207b5e437539fc262344d6cebc7f997bc2b04ecaccb899"),
    "2025-december": (_book("694b1d0b094e9c8247157ab7"), "fecd978ca0a0a2dba8f84800888ba93fa9fffb56ed078c2dcd215fb3baba8716"),
    "2025-pea-history": ("https://www.comed.com/cdn/assets/v3/assets/blt3ebb3fed6084be2a/bltd0031ae7271bf238/682c9fe866e148d5541a49fe/2025_PEA_record_for_rate_book.pdf?branch=prod_alias", "c688268ee23a1d0678971a606b3bc6a9746572d1ac00477d57c0c342a61042ca"),
    "2026-pea-history": ("https://www.comed.com/cdn/assets/v3/assets/blt3ebb3fed6084be2a/bltd0031ae7271bf238/6ac685e1ff666ce7a12a40f7/2026_PEA_record_for_rate_book.pdf?branch=prod_alias", "13a9dc7e16a56b7ff58fdcd6f7d2ec7fd4f7a86e2afe9f9fdf3c9a2572a4b31c"),
    "ICC-price-history": ("https://icc.illinois.gov/downloads/public/pluginillinois/HistoricalPriceToCompare.pdf", "c40f0f1e58482a4cc52b561ce6c2bccd431aa981a8c7538f42fbabfcb6f72f18"),
    "ERM25-131": ("https://www.icc.illinois.gov/downloads/public/filing/4/393526.pdf", "036ece98dcb4024eb333c1eb2160ac52cfea4c319ef71279f990b7ed45be5ac1"),
    "2025-November-DRAF": ("https://www.icc.illinois.gov/downloads/public/filing/4/394253.pdf", "07350de5a74e58c5ba0a4db25e0a692f5c58f01ebae9ecb15aea8502df205fb3"),
    "2025-November-EDAF": ("https://www.icc.illinois.gov/downloads/public/filing/4/394254.pdf", "52e1bfa9864e1cc3f958736e9eb52e07f807a77216848c2dc2719c1424ddca36"),
    "ERM25-015": ("https://icc.illinois.gov/downloads/public/filing/4/388714.pdf", "e03c9bb814f9c1c8f08d894b65f986afde06d0e16fce173d0853796db1b708d4"),
    "ERM25-033": ("https://icc.illinois.gov/downloads/public/filing/4/389486.pdf", "18f401faa710133bd189c34673ba9e91153bbbe7902da1a3705a5b02b61eabf0"),
    "ERM25-056": ("https://icc.illinois.gov/downloads/public/filing/4/390849.pdf", "3d79ce8a3c5b53d6a7dfbec862325f232ce37160dd235d5fa1e4051f6c431c4b"),
    "ERM25-047": ("https://icc.illinois.gov/downloads/public/filing/4/390605.pdf", "eeeabacebf4e5383b030fa232f7181ed03f329a64b06a92939e372fd7c40d1b9"),
    "ERM25-026": ("https://icc.illinois.gov/downloads/public/filing/4/389292.pdf", "1ccad3dc39bdacc967b6c7c42dba82af91e54f10feb4d918e8e93e9b96eb2cae"),
    "ERM25-027": ("https://icc.illinois.gov/downloads/public/filing/4/389302.pdf", "4ec8341af8bbb1c2fc932684853425f94cd3a47a22daae2f0c18e78f1483a913"),
    "ERM25-031": ("https://icc.illinois.gov/downloads/public/filing/4/389345.pdf", "bd0d37479419eec0410ba2927d9222bc6b797975e865039f1cf7c90b35108326"),
    "ERM25-121": ("https://icc.illinois.gov/downloads/public/filing/4/393256.pdf", "55a7a42ec74854224a4c00e7155c0389f11e6c88cafe043117f062a6b15f1dca"),
    "ERM25-132": ("https://icc.illinois.gov/downloads/public/filing/4/393564.pdf", "c91eee8f5651cde18aef267d587e3a023ee961f6e230422c3cb3a241ae9a6b89"),
    "ERM25-154": ("https://icc.illinois.gov/downloads/public/filing/4/393873.pdf", "e7918a6d3f8370f0118a5b42a80793dda537eb630063247ea1522b57aab87e8c"),
    "ERM25-166": ("https://icc.illinois.gov/downloads/public/filing/4/394224.pdf", "03f4085e7337a1c36e530346be680617058d1f92bce20fa4f8e5a8e2a49fd353"),
    "ERM26-068": ("https://icc.illinois.gov/downloads/public/filing/4/398491.pdf", "c68da57127d185d4174f9112c5a14e1b6e5c5e6415108dda93d7e8f2209e1f19"),
    "ERM26-063": ("https://icc.illinois.gov/downloads/public/filing/4/398278.pdf", "fcd1edaeea1138ff4b8eae74c6b5ee833f1469860d2cea4f4ab6277c97dd6392"),
    "ERM26-059": ("https://icc.illinois.gov/downloads/public/filing/4/398271.pdf", "f093bc7201cddbbd787907373eb8daf066dde773b80c09d21a4ac4481d2dbc89"),
    "ERM26-058": ("https://icc.illinois.gov/downloads/public/filing/4/398254.pdf", "e1e7214fa5c9f7c418baacbe8b96373e42cdcb7c3d5595d64de6b5550e07e958"),
    "ERM26-039": ("https://icc.illinois.gov/downloads/public/filing/4/396796.pdf", "98bd5c3dd70547e4bc67c100a5dd4bca6ad2852a59f844b02f8ee8d38719e3a4"),
    "ERM26-037": ("https://icc.illinois.gov/downloads/public/filing/4/396728.pdf", "5a969053c8cb834a6333b4280bd36234e2c2b9c8a95e3f51a35a2eaaad182d57"),
    "ERM26-034": ("https://icc.illinois.gov/downloads/public/filing/4/396598.pdf", "0105dc3c62a793e55c4894b53407a67ea47a08b89b874d41ceaab1993f059fa2"),
    "ERM26-033": ("https://icc.illinois.gov/downloads/public/filing/4/396597.pdf", "709ef0ff790abd436e01ad65ff4c070da5ede3a70c12792bac1914a842d04b4b"),
    "ERM26-031": ("https://icc.illinois.gov/downloads/public/filing/4/396435.pdf", "910f93f286456d51d11102378cc0e583ddae497cfc878e26ef73c1503151c793"),
    "ERM26-020": ("https://icc.illinois.gov/downloads/public/filing/4/395863.pdf", "4ec896883c4f95fbc9f48b65fee199a2b8b64bd564fe58b39644ef853a8f6b98"),
    "ERM26-019": ("https://icc.illinois.gov/downloads/public/filing/4/395844.pdf", "9b2ed61d2edc1813dfe2a6974e71e4530f724111d5a1be1e08a631b5ab66070c"),
    "ERM26-008": ("https://icc.illinois.gov/downloads/public/filing/4/395230.pdf", "9a75e7a3eba1afc6f194c0664699fa6b29c99c1583669aefb79218d541bc7277"),
    "ERM26-007": ("https://icc.illinois.gov/downloads/public/filing/4/395227.pdf", "7a601c03be1ee5124b0d6de23ee9d07b84ac40b9a1371396e4a1a99acd397d0f"),
    "ERM26-005": ("https://icc.illinois.gov/downloads/public/filing/4/395199.pdf", "b9aaba8da6ad404b9f467bb145d4f1f7636e14312247438b2ea9724a3692984e"),
})


def _sources_2025(month):
    # Logical pages are the existing 2026 component identifiers used by the
    # bill adapters. Each is translated to the *actual* document and page.
    pages = {60: ("2025-july", 58), 394: ("2025-july", 382),
             396: ("2025-july", 384), 799: ("2025-january", 743),
             802: ("2025-july", 750), 814: ("2025-january", 758),
             821: ("2025-december", 805), 822: ("2025-december", 806),
             824: ("2025-december", 808), 839: ("2025-july", 787),
             848: ("2025-july", 796), 850: ("2025-july", 798),
             852: ("2025-july", 800), 854: ("2025-july", 802),
             864: ("2025-july", 812), 865: ("2025-july", 813),
             866: ("2025-december", 850), 803: ("2025-july", 751),
             26: ("2025-july", 25), 58: ("2025-july", 56),
             174: ("2025-july", 165), 24: ("2025-july", 23),
             27: ("2025-july", 26), 178: ("2025-july", 169),
             257: ("2025-july", 245), 258: ("2025-july", 246)}
    if month in range(1, 10):
        pages.update({p: ("2025-july", q) for p, q in {
            782:730, 783:731, 785:733, 786:734, 787:735, 789:737,
            790:738, 801:749, 820:768, 845:793}.items()})
        pages[817] = ("2025-january", 761) if month < 6 else ("2025-july", 765)
        pages[818] = ("2025-january", 762) if month < 6 else ("2025-july", 766)
        pages[846] = ("2025-january", 790) if month < 6 else ("2025-july", 794)
        pages[784] = pages[788] = ("2025-pea-history", 1) if month < 6 else ("2025-july", 732)
        if month >= 6:
            pages[788] = ("2025-july", 736)
        if month == 1:
            # Pre-February revisions already show the same 2025 base column.
            pages.update({p: ("2025-january", q) for p, q in
                          {848:792,850:794,852:796,854:798}.items()})
        if month >= 8:
            pages.update({789: ("2025-december", 773), 784: ("ICC-price-history", 1),
                          818: ("2025-december", 802)})
            if month == 9:
                pages.update({p: ("ERM25-131", q) for p, q in
                              {782:3,783:4,785:5,786:6,787:7,801:8}.items()})
                pages[820] = ("2025-december", 804)
    elif month in (10, 11, 12):
        pages.update({p: ("2025-december", q) for p, q in {
            394:390,396:392,782:766,783:767,784:768,785:769,786:770,787:771,
            788:772,789:773,790:774,801:785,802:786,803:787,817:801,818:802,
            820:804,839:823,845:829,846:830}.items()})
        if month != 12:
            pages.update({784: ("ICC-price-history", 1),
                          790: ("2025-November-DRAF", 3),
                          845: ("2025-November-EDAF", 3)})
    else:
        raise ValueError("No complete verified historical composite for this month.")
    if month in (3, 4, 5):
        # Each spring CFRA sheet explicitly gives the complete CFR+CFRMR
        # total for its billing month. ERM25-047 corroborates Jan-May supply,
        # not the June forecasts on that same sheet (later superseded).
        pages.update({p: ("ERM25-047", q) for p, q in
                      {782:4,783:5,785:6,786:7,787:8}.items()})
        pages.update({818: ({3:"ERM25-015",4:"ERM25-033",5:"ERM25-056"}[month], 3),
                      789: ("ERM25-026", 2), 790: ("ERM25-027", 3),
                      846: ("ERM25-031", 3)})
    if month in (8, 9, 10, 11):
        filing = {8:"ERM25-121",9:"ERM25-132",10:"ERM25-154",11:"ERM25-166"}[month]
        pages.update({784: (filing, 3), 788: (filing, 4)})
    return tuple((logical, doc, page) for logical, (doc, page) in pages.items())


def _historical_2025(month, *, supply, pea, hpea, cfra, cts, capacity,
                     iduf, isuf, ecr, zea, draf, edaf):
    return ComEdVersion(
        f"comed_residential_2025_{month:02}", date(2025, month, 1),
        date(2025, month, monthrange(2025, month)[1]),
        D(supply[0]), D(supply[1]), D(pea), D(supply[6]), D(supply[7]),
        D(hpea) if hpea is not None else None, D(cfra), D(cts), capacity=D(capacity),
        hec_multiplier=D("1.0114") * D(isuf) * D("1.0470"),
        residential_iduf=D(iduf[0]), nonresidential_iduf=D(iduf[1]), large_iduf=D(iduf[2]),
        environmental_cost_recovery=D(ecr), zero_emission_standard=D(zea),
        delivery_year=2025, delivery_reconciliation=D(draf), excess_deferred_income_tax=D(edaf),
        # TPAF's first reconciliation is filed Dec 2025 for Jan 2026; the
        # initial LID informational sheets likewise begin Jan 2026.
        total_plan_adjustment=D(0), distributed_generation_adjustment=D(".00043"),
        residential_assessment=D(".75"), small_commercial_assessment=D("6.90"),
        large_commercial_assessment=D("277.50"), residential_lid_recovery=None,
        small_commercial_lid_recovery=None, large_commercial_lid_recovery=None,
        renewable_portfolio_standard=D(".00502"), energy_efficiency_programs=D(".00376"),
        small_commercial_efficiency=D(".00835"), large_commercial_efficiency=D(".00444"),
        energy_transition_assistance=D(".00072"), commercial_supply=tuple(map(D, supply[2:6])),
        component_sources=_sources_2025(month),
        source_references=tuple(sorted({s[1] for s in _sources_2025(month)})),
    )


_EARLY_2025 = dict(supply=(".05015", ".01537", ".05046", ".05096", ".04922", ".01528", ".00982", ".00058"),
                   cts="0", capacity=".91048", iduf=("1.0056", "1.0017", "1.0005"),
                   isuf="1.0033", ecr=".00002", zea=".00195", draf=".172495", edaf="-.0359")
_SUMMER_2025 = dict(supply=(".08261", ".01767", ".08304", ".08416", ".07578", ".01757", ".01101", ".00073"),
                    cts=".00005", capacity="8.33100", iduf=("1.0084", "1.0041", "1.0003"),
                    isuf="1.0014", ecr=".00007", zea=".00195", draf=".170696", edaf="-.0380")
_HISTORICAL_VERSIONS = (
    _historical_2025(1, pea="-.00542", hpea="-.01140", cfra=".00377", **_EARLY_2025),
    _historical_2025(2, pea="-.00089", hpea=".00708", cfra=".00475", **_EARLY_2025),
    _historical_2025(3, pea=".00031", hpea=".00256", cfra=".00803", **_EARLY_2025),
    *(_historical_2025(month, pea=pea, hpea=hpea, cfra=cfra,
                       **{**_EARLY_2025, "ecr": ".00007", "draf": ".170696", "edaf": "-.0380"})
      for month, pea, hpea, cfra in ((4, "-.00335", ".00139", ".00810"),
                                    (5, ".01965", ".02664", "-.00522"))),
    _historical_2025(6, pea=".00527", hpea=".00648", cfra="-.01703", **_SUMMER_2025),
    _historical_2025(7, pea="-.00446", hpea="-.01437", cfra="-.00893", **_SUMMER_2025),
    _historical_2025(8, pea="-.00029", hpea=".00628", cfra="-.00781",
                     **{**_SUMMER_2025, "ecr": ".00010"}),
    _historical_2025(9, supply=(".08260", ".01767", ".08304", ".08416", ".07578", ".01757", ".01099", ".00073"),
                     pea=".00022", hpea="-.00538", cfra="-.01031", cts=".00005", capacity="8.31935",
                     iduf=("1.0091", "1.0064", "1.0014"), isuf="1.0000", ecr=".00010",
                     zea=".00189", draf=".170696", edaf="-.0380"),
    *(_historical_2025(month, supply=(".07873", ".01816", ".07914", ".07946", ".07567", ".01805", ".01088", ".00063"),
                      pea=pea, hpea=hpea, cfra=cfra, cts=".00007", capacity="8.31935",
                      iduf=("1.0091", "1.0064", "1.0014"), isuf="1.0000", ecr=".00010",
                      zea=".00189", draf=draf, edaf=edaf)
      for month, pea, hpea, cfra, draf, edaf in (
          (10, "-.01469", ".02498", "-.00088", ".170696", "-.0380"),
          (11, "-.01721", "-.04214", "-.00847", ".108072", "-.0291"))),
    _historical_2025(12, supply=(".07873", ".01816", ".07914", ".07946", ".07567", ".01805", ".01088", ".00063"),
                     pea="-.00849", hpea=".00474", cfra="-.00276", cts=".00007", capacity="8.31935",
                     iduf=("1.0091", "1.0064", "1.0014"), isuf="1.0000", ecr=".00010",
                     zea=".00189", draf=".140883", edaf="-.0327"),
)
_SUMMER_2026 = tuple(replace(
    VERSIONS[0], tariff_id=f"comed_residential_2026_{month:02}",
    effective_start=date(2026, month, 1), effective_end=date(2026, month, 31),
    bes_adjustment=D(pea), besh_adjustment=D(hpea), carbon_free_adjustment=D(cfra),
    environmental_cost_recovery=D(ecr),
    component_sources=((784, "2026-pea-history", 1), (788, "2026-pea-history", 1)),
    source_references=("ERM26-082", "2026-pea-history", "2026-ratebook"),
) for month, pea, hpea, cfra, ecr in (
    (7, ".00247", ".00690", "-.01228", ".00009"),
    (8, "-.00142", "-.00376", "-.00690", ".00007"),
))


def _sources_early_2026(month):
    if month not in range(1, 6):
        raise ValueError("Only January-May 2026 components were verified here.")
    # Annual delivery bases, RBAF, DGRA, EE, ETAC and TPAF explicitly cover
    # 2026. Monthly UF/REA/ZEA tables come from their earlier dated revisions.
    annual = (24, 26, 27, 58, 60, 174, 178, 257, 258, 394, 396, 799,
              802, 814, 821, 822, 824, 839, 845, 848, 850, 852, 854, 864, 865, 866)
    pages = {p: ("2026-ratebook", p) for p in annual}
    pages.update({801: ("2025-december", 785), 803: ("2025-december", 787),
                  817: ("2025-december", 801), 820: ("2025-december", 804),
                  790: ("ERM26-031", 3)})
    pages.update({p: ("ERM26-068", q) for p, q in
                  {782:4, 783:5, 785:6, 786:7, 787:8}.items()})
    adjustment = {1:"ERM26-005", 2:"ERM26-005", 3:"ERM26-019",
                  4:"ERM26-037", 5:"ERM26-058"}[month]
    pages.update({784: (adjustment, 3), 788: (adjustment, 4),
                  818: ({1:"ERM26-008", 2:"ERM26-008", 3:"ERM26-020",
                         4:"ERM26-039", 5:"ERM26-059"}[month], 3),
                  876: ("ERM26-007" if month <= 3 else "ERM26-033", 4),
                  846: ("ERM26-034" if month <= 4 else "ERM26-063", 3),
                  789: ("2025-december", 773) if month <= 3 else ("2026-ratebook", 789)})
    return tuple((logical, doc, page) for logical, (doc, page) in pages.items())


_EARLY_2026 = tuple(ComEdVersion(
    f"comed_residential_2026_{month:02}", date(2026, month, 1),
    date(2026, month, monthrange(2026, month)[1]),
    D(".07841"), D(".01819"), D(pea), D(".01083"), D(".00062"),
    D(hpea), D(cfra), D(cts), capacity=D("8.32925"),
    hec_multiplier=D("1.0124") * D("1.0002") * D("1.0406"),
    residential_iduf=D("1.0090"), nonresidential_iduf=D("1.0065"), large_iduf=D("1.0014"),
    environmental_cost_recovery=D(".00010" if month <= 3 else ".00009"),
    zero_emission_standard=D(".00189"), renewable_portfolio_standard=D(".00502"),
    delivery_reconciliation=D("0" if month <= 3 else ".006785"),
    residential_lid_recovery=D(lid), small_commercial_lid_recovery=D(lid_small),
    large_commercial_lid_recovery=D(lid_large),
    commercial_supply=tuple(map(D, (".07870", ".07899", ".07565", ".01805"))),
    component_sources=_sources_early_2026(month),
    source_references=tuple(sorted({s[1] for s in _sources_early_2026(month)})),
) for month, pea, hpea, cfra, cts, lid, lid_small, lid_large in (
    (1, ".00357", ".00743", "-.02381", ".00007", "1.17", "11.70", "438.75"),
    (2, ".00889", "-.00189", "-.02182", ".00007", "1.22", "12.20", "457.50"),
    (3, "-.00151", "-.01528", "-.04110", ".00007", "1.22", "12.20", "457.50"),
    (4, ".01159", ".01773", "-.03186", ".00006", "1.35", "13.50", "506.25"),
    (5, ".08166", ".08032", "-.06414", ".00009", "1.35", "13.50", "506.25"),
))
VERSIONS = tuple(sorted(VERSIONS + _SUMMER_2026 + _HISTORICAL_VERSIONS + _EARLY_2026,
                        key=lambda v: v.effective_start))


def build_comed_residential_plans() -> tuple[RatePlan[ComEdVersion], ...]:
    """Eight account choices; use version_on with the confirmed billing month.

    Kept separate from the generic service-date tariff registry: neither raw
    LMP nor monthly ComEd adjustments fit a generic flat energy tariff.
    """
    return tuple(
        RatePlan(RatePlanIdentity("ComEd", supply, "bundled", "residential", delivery),
                 tuple(v for v in VERSIONS if supply == "BES" or v.besh_adjustment is not None))
        for supply in ("BES", "BESH") for delivery in DELIVERY
    )


def line_sources(version, name, pages):
    """References identify the document as well as its one-based pages."""
    component_sources = {logical: (doc, page) for logical, doc, page in version.component_sources}
    historical = version.effective_start < date(2026, 6, 1)
    if historical or any(page in component_sources for page in pages):
        grouped = {}
        for logical in pages:
            if logical not in component_sources:
                if historical:
                    raise ValueError(f"No historical provenance for {name}, component {logical}.")
                doc_key, actual, url, sha = "2026-ratebook", logical, RATEBOOK_URL, RATEBOOK_SHA256
            else:
                doc_key, actual = component_sources[logical]
                url, sha = DOCUMENTS[doc_key]
            grouped.setdefault(doc_key, {"url": url, "sha256": sha, "pdf_pages": []})
            if actual not in grouped[doc_key]["pdf_pages"]:
                grouped[doc_key]["pdf_pages"].append(actual)
        return list(grouped.values())
    document = {"url": RATEBOOK_URL, "sha256": RATEBOOK_SHA256, "pdf_pages": pages}
    if version.effective_start == date(2026, 6, 1):
        filed = {"electricity_supply": ("399143", 4), "transmission_services": ("399143", 5),
                 "capacity": ("399143", 6), "miscellaneous_procurement": ("399143", 8),
                 "purchased_electricity_adjustment": ("399174", 3),
                 "carbon_free_resource_adjustment": ("399171", 3)}
        if name in filed:
            ident, page = filed[name]
            if name == "transmission_services" and pages == [786]:
                page = 7
            if name == "purchased_electricity_adjustment" and pages == [788]:
                page = 4
            sha = {"399143": "825a7bc953cead4944ad74c73eca2f351ff1a3ee15ce218c036a228a26288ad1",
                   "399174": "df2b629ffab80a46b260b6d76b5fd373a33c7b0e65e32ea7741f4e6bbf65f385",
                   "399171": "0c6cc3a264c15dae1e91a182567bfffaf1083a08e0825c9328030d5d06bc7a23"}[ident]
            document = {"url": f"https://www.icc.illinois.gov/downloads/public/filing/4/{ident}.pdf",
                        "sha256": sha, "pdf_pages": [page]}
    return [document]


def primary_source(version):
    """The summary source; per-line references remain authoritative."""
    if version.delivery_year == 2025:
        key = "2025-january" if version.effective_start.month < 6 else "2025-july" if version.effective_start.month < 10 else "2025-december"
        url, sha = DOCUMENTS[key]
        return {"ratebook_url": url, "ratebook_sha256": sha}
    return {"ratebook_url": RATEBOOK_URL, "ratebook_sha256": RATEBOOK_SHA256}


def cycle_source(cycle, version):
    if cycle is None:
        return None
    documents = line_sources(version, "billing_cycle_rules", [24, 27, 174, 178, 257, 258])
    return {**cycle.public(), "rules_pdf_pages": documents[0]["pdf_pages"],
            "rules_source_documents": documents}
