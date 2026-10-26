# Alliant Energy Iowa source pack

Retrieved October 25, 2026. Rates belong to Interstate Power and Light (Alliant Iowa), in MISO. Wisconsin Power and Light is a different utility. Neither expands PJM population coverage.

`sources.json` records the source URL, revision/page identification, retrieval method, and SHA-256 of each saved extraction. Most Alliant original PDF bytes returned HTTP 403 to a direct public download; their public search-index PDF text was inspected instead. Their original-file SHA-256 is deliberately null. Historical indexed versions must not be assumed to remain at a mutable current URL. These fact extracts are not complete tariff transcriptions.

The Ottumwa Housing Authority April 2025 study was downloaded successfully (67 pages; original SHA-256 `83ec981babbc0417e5cb8838f08c3dcca36b63f8da58347c37b044150b4dcc9c`). Its attached filed utility sheets, PDF pages 43–47, are saved as exact text extractions. Only those tariff appendices are rate evidence. The consultant's compiled bill/allowance summary omits riders and conflicts with the residential state-tax exemption; it is not an independent complete-bill benchmark. The original PDF remains in the ignored research cache rather than adding a 2.9 MB report to Git.

## Initial 2026 implementation window

This section records the initial June–October 2026 scope. The follow-up below
adds a separate January–December 2025 window; January–May 2026 remains blocked.

Complete June–October 2026 calendar billing months have matching retrieved base rates, EAC, EECR, DRCR, and RTS, with TBR expired. EAC values are tied to a **billing month**, while some rider sheets distinguish their header effective date from the factor application date. Actual partial periods, crossing cycles, and general daily allocation should not be inferred from these tables.

| Component | Rate/application fact |
| --- | --- |
| Base 400/407/427, 600/607 | October 1, 2024 sheets; current posted versions remain those sheets |
| EECR | June 1, 2026 factor application: residential $0.0013/kWh; general service $0.0038/kWh |
| DRCR | June 1, 2026: residential $0.0042/kWh; general service $0.0023/kWh |
| RTS | February 6, 2026: residential $0.04494/kWh; general service $0.03568/kWh; August 1, 2026: $0.04456/$0.03539 |
| EAC | Billing-month factors through October 2026; November/December are blank, not zero |
| RCE | $0.00006/kWh from September 2025 is already included in the EAC billed totals; split for display without double counting |
| TBR | Twelve-month refund began October 2024 and expired before October 2025; no June–October 2026 refund |
| EEBC | Conditional account/program payment, not a universal automatic rider credit |

The selected 600/607 general-service tariff has **no demand charge**. The tariff uses a less-than-20,000 kWh classification criterion over 12 consecutive billing months; section 2.03 says classification generally relates to monthly energy quantity. Preserve utility-confirmed classification and history; do not recast the threshold as an annual energy cap. A conservative example can keep each monthly cycle below 20,000 kWh, without claiming that proves eligibility. An existing enrolled customer may have continuation rights; that is a separate account fact. Larger plans 707/447/487 are outside this first case.

Residential ordinary service is single-family domestic or individually metered apartment use. The daily customer charge, rather than the comparison monthly figure, is the billing quantity. Optional TOD enrollment has a minimum one-year term. Single-phase 120/240 V assumptions avoid unverified alternative-service fees; the explicit incremental three-phase charge still appears in the source facts.

## Initial historical gaps and conflicts

These are the findings from the initial research pass, preserved for context.
The 2025 follow-up below resolves the bounded 2025 factor gaps through
additional primary evidence; its source limitations remain explicit.

1. **2025 TBR/EAC ordering resolved:** the detailed EAC table's TBR component is a dash, and the standalone TBR sheet promises its separate refund. Alliant's official March 2025 residential bill guide makes the treatment explicit: a January 2–February 3 sample bill charges $0.0102/kWh Energy Cost **and separately credits −$0.00789/kWh TBR**. Therefore add the separately applicable TBR credit in its stated window rather than assuming the EAC summary includes it. RCE is different: the EAC summary explicitly includes RCE starting September 2025. The sample uses residential optional-demand 507, so its demand/energy base charges are not a benchmark for 400/407/427, but its shared residential riders reconcile the ordering.
2. **RTS mid-2025 history:** the actual attached January 1, 2025 sheet establishes $0.04077/kWh residential and $0.03217/kWh general service. It does not establish unchanged rates throughout 2025. The utility RTS explanation mentions a September 2025 refund adjustment; the superseding factor sheet is not yet recovered.
3. **Pre-June 17, 2025 DRCR:** historical substitute seventh sheet establishes $0.0048/$0.0028 starting June 17, 2025. The preceding factor sheet remains missing.
4. **EECR history:** the actual appendix establishes $0.0009/$0.0014 beginning August 1, 2024; historical substitute thirtieth sheet gives $0.0006/$0.0032 beginning June 17, 2025. Header effective dates differ from these body factor dates; do not silently use the header for factor allocation.
5. **Early 2026 RTS:** a third substitute twenty-fifth sheet has factors starting February 6, 2026. A public utility Q&A loosely labels those values January–July. Do not extend the filed February factor back to January on that basis.
6. **TOU clock:** filed sheets explicitly say **CST**, while the utility's business explanation says **CT**. A literal fixed-standard-time implementation must identify that reading and retain the original timezone-aware interval timestamps. A definitive meter-clock clarification would remove this discrepancy. The only holiday named in 407/427/607 energy periods is Independence Day; an observed-day substitution is not stated in the selected sheets.

At that initial stage, the remaining historical factor gaps blocked full-year
2025 billing. They did not justify borrowing another utility's or neighboring
period's rates. The follow-up below documents the evidence subsequently used
for the bounded 2025 reconstruction.

## Taxes and location are separate facts

[Alliant Rider TAX](https://www.alliantenergy.com/-/media/alliant/documents/accountandbilling/ratesandtariffs/iowaelectricrates/ridertaxtaxadjustmentclause.pdf?hash=C322882BF894A3E416066B107F3B23F6&sc_lang=en) passes applicable taxes through only in the actual taxing jurisdiction. [Iowa DOR](https://revenue.iowa.gov/taxes/frequently-asked-questions/local-option-sales-tax-lost) distinguishes state tax exemption for residential energy, the 1% local residential energy excise in LOST jurisdictions, and exemption from LOST where electricity has a franchise/user fee. Ordinary nonresidential state sales tax is 6%.

[Linn County's official results](https://www.linncountyiowa.gov/1593/Local-Option-Sales-Tax-Referendum) establish a 1% local option tax in the unincorporated county through June 30, 2034. For an explicitly confirmed ordinary unincorporated Linn account, the bounded model may use residential 1% local energy excise or ordinary commercial 6% state plus 1% local, with no franchise fee. A weather coordinate near Cedar Rapids does not establish an unincorporated account address. Cedar Rapids has a distinct 4% franchise fee authorized July 1, 2025; do not mix it with the unincorporated case.

## PV, storage and market boundaries

[The filed Inflow–Outflow tariff](https://www.alliantenergy.com/-/media/alliant/documents/accountandbilling/ratesandtariffs/iowaelectricrates/inflowoutflowtariff.pdf?hash=86C5A123994D30ED6F8002639C67266E&la=en&sc_lang=en) preserves the eligible ordinary schedule's charges and riders on each 15-minute net inflow. It defines separate outflow credits, annual forfeiture, capacity/production limits and interconnection requirements. This first implementation can remain explicitly **non-export**, using the ordinary import charge with zero outflow and confirmed interconnection assumptions; it does not thereby implement IO export settlement or establish customer eligibility.

RTS for the selected rates is a retail per-kWh rider. Do not add hypothetical customer PLC/NSPL or wholesale MISO capacity/transmission charges on top. Wholesale LMP location and carbon-data scope remain separate from utility service, eligibility and retail billing.


## 2025 follow-up retrieval and evidence status

The follow-up keeps the first 27 records unchanged and adds separate records
for newly recovered original documents and archived official utility pages.
Original PDFs and HTML now downloaded successfully with a standard public
browser user-agent and verified TLS; their actual SHA-256 values are recorded.
The old indexed records are not relabeled as if binary originals had been
available during the first research pass. Raw documents and visual checks
remain in ignored `.cache/alliant_2025_research/`; only factual or redacted
extracts are checked in.

Recovered evidence now establishes:

- All twelve **2025 billing-month EAC** totals, identical for residential and
  general service. The AEP/fuel/RCE components reconcile exactly. The downloaded
  current EAC PDF is the substitute revision issued October 20, 2026; its
  retained historical 2025 rows agree with the earlier indexed copy. Its
  October 2026 component allocation differs, while the total remains equal.
- **TBR** credits of minus $0.00789/kWh residential and minus $0.00592/kWh GS.
  The official utility outlook confirms expiration on October 1, 2025.
  This supports January–September complete calendar billing months, with no
  October–December credit. A primary government-published Sep19–Oct21 GS600
  cycle confirms 11/32 of whole-cycle kWh receives the pre-expiry credit, while
  all kWh use October EAC. Arbitrary shifted cycles still require a separately
  implemented and tested date-allocation contract.
- **RCE** of $0.00006/kWh for bills rendered in September 2025 onward is
  already included in EAC. The August 8 sheet-header date is not its customer
  billing-month start.
- **RTS** of $0.04077/$0.03217 per kWh residential/GS in January–August 2025,
  then $0.04055/$0.03196 from September 1. The September refund is included
  already. Archived official utility pages provide the dated table; the
  January filed sheet is also retained in the public-authority appendix.
- **EECR/DRCR** new factors with an explicit June 17, 2025 application date
  in the historical official indexed sheets. A primary government-published
  GS600 May–June bill verifies whole-cycle kWh weighted by 27/30 old-rate days
  and 3/30 new-rate days. The 2024 GS600 crossing bill independently shows
  the previous August 1 transition using the same day-fraction pattern.
- Actual original official residential and small-business bill guides verify
  separate TBR treatment and the early-2025 rider values. The corrected
  government-published December 2025 bill is retained as corrected evidence;
  the superseded erroneous factor must not establish tariff applicability.

The exact preceding **sixth DRCR tariff sheet** remains unrecovered, so its
original 2024 start date is not asserted. The bounded 2025 reconstruction uses
multiple utility-issued 2025 bill guides showing residential factors of
$0.0009/kWh EECR and $0.0031/kWh DRCR; government-published GS600 bills spanning
year-start and successive early-2025 cycles show $0.0014/kWh EECR and
$0.0023/kWh DRCR. The new seventh DRCR sheet explicitly supersedes substitute
sixth with the June 17, 2025 factor change. These mutually consistent primary
records establish the preceding 2025 factor window without inventing a rate
or extrapolating a later factor backward. The source limitation remains visible
separately from the executable scope and validation results.

The official **Night Owl Rate 427** guide explicitly applies the old residential
EECR/DRCR factors to that price code in its illustrated January-February 2025
cycle. The standard 400 and Summer Saver 407 guides corroborate the same class
factors. This resolves the older EECR sheet's omission of newly introduced 427
from its printed price-code list. Guide prose does not override filed TOU
windows; in particular, Night Owl's inconsistent prose clock is not used to
define super-off-peak timing. Illustrative guide dates and EAC factors also do
not define billing-month assignment. No third-party customer-bill upload is
required for these rider/class conclusions. The executable catalog and its
validation artifacts remain authoritative for supported simulations.
