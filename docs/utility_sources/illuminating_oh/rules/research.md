# CEI rules review

Reviewed October 31, 2026. This review owns eligibility and billing rules; the
delivery and supply ledgers establish component coverage. Original downloaded
PDF/HTML hashes, selected excerpts and visual-review receipts are in
[sources.json](sources.json); structured conclusions are in [rules.json](rules.json).

## Ordinary schedules

The Cleveland Electric Illuminating Company, Ohio, P.U.C.O. No. 13, calls the
ordinary schedules **RS Residential Service** (Sheet 10) and **GS General
Service–Secondary** (Sheet 20). The original 2009 schedules are retained in the
2025 book; the first revised schedules apply March 1, 2026. Secondary is at or
below 600 V, assigned by the Company; a selected 120/240 V single-phase model
does not establish real account eligibility.

RS serves one meter per family unit. Mixed commercial/residential use on the
same meter, institutional/commercial premises and common apartment facilities
belong to the appropriate general service schedule. GS has no universal small
load ceiling in Sheet 20. Restricting a study to small measured-demand accounts
is a model scope choice rather than a restatement of the entire schedule.

## GS demand and contract

The measured peak is the **highest thirty-minute integrated import kW**. Billing
demand is the maximum of that peak, **5 kW**, and the documented contract demand.
The up-to-5-kW capacity amount is **one flat monthly amount**, not a per-kW price.
There is no trailing eleven-month demand ratchet in this schedule. Contract
demand is independent of the current month's usage: new/significantly changed
service uses 60% of expected typical monthly peak, older contracts are retained,
and Company review governs changes. Do not infer a zero contract or recalculate
it automatically from PV/battery-reduced imports.

Customers without a demand meter and over 1,000 kWh/month use kWh/200 estimated
demand. The recommended scope excludes this alternative, unmetered service,
optional GSU service, duplicate/premium circuits, special meter fees and
primary-side metering (whose loss adjustment changes from 2% to 1.5%). Reactive
charges apply to three-phase customers only; a confirmed single-phase account
avoids that component. The GS 5-kW/contract floor always applies; no independent
ordinary RS/GS minimum-bill clause was found. Partial Service has separate
minimum/capacity charges and remains outside this scope.

## Dates and supply

Bills are monthly, typically approximately thirty days. Standard seasonal
service is summer June–August and winter September–May, unless a rider says
otherwise. Non-seasonal changes begin with service rendered on their effective
date. No general fixed-charge split/irregular-cycle allocation was established.
Complete calendar cycles are a narrower defensible study scope; a midmonth
component boundary still needs verified allocation before including its whole
calendar month. This finding alone does not establish every rider's date.

SSO uses the ordinary GEN tariff; shopping/CRES, aggregation, CPP/PTR/RTP,
assistance and special arrangements are excluded. Supplier changes normally
occur at a regular meter read; SSO and a certified supplier cannot be split in
one billing month. Retail GEN/riders never come from an LMP series.

## PV and paired storage

Ohio Administrative Code 4901:1-10-28, effective April 8, 2024, requires a
standard net-metering customer's retail structure, components and monthly
charges to match the underlying non-generator tariff. The facility must use
qualifying onsite generation, primarily offset requirements, and be sized to
no more than 120% of requirements determined from three-year average usage or a
utility estimate. Sheet 93 applies the underlying schedule and import-side
measured peak; Sheet 46 excludes NEM-qualifying generation from Partial Service.

The utility's interconnection instructions expressly require storage equipment
on the site plan and one-line diagram, a signed interconnection agreement,
final utility review and permission to operate. That is not automatic approval
of any battery configuration. Require account-specific confirmation for the
exact PV/paired-storage system, ordinary/NEM eligibility, meter and absence of
recurring special charges, with activation before the study. A zero-export,
zero-credit-bank, PV-only-charging study is a conservative subset; no standalone
battery or export settlement is verified. The old filed NEM sheet's requested
cash refund language differs from the current rule's continuing monetary
credit. This implementation must not expose that unresolved settlement.

## Market metadata

PJM's official region table names CEI in **FE-ATSI**, a control area; FirstEnergy
explains that the FE Ohio energy zone combines CEI, Ohio Edison and Toledo
Edison, while transmission/NSPL accounts remain company-specific. Keep the
utility, Ohio jurisdiction, SSO supplier arrangement, PJM zone/control metadata,
wholesale prices and any regional-average carbon series separate.

Selected 2025 and 2026 GS schedule pages were rendered and visually checked.
Poppler produced the images but emitted font-cache warnings; the output was
viewed successfully. No source PDF was modified.
