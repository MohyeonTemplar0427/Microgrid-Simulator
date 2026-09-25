# PG&E solar true-up development

PG&E is the active scope; other Bay Area and LA solar programs remain deferred.

## Implemented: NBT annual statement reconciliation

`src/billing/pge_true_up.py` reconciles annual statement aggregates independently
of monthly simulation. It keeps generation and delivery credit banks separate,
applies net-surplus recoupment, uses remaining banked credits against eligible
previously paid charges, computes NSC, and preserves ACC Plus separately.
A negative adjustment is a bill credit, not an automatic cash payment.

The replay requires confirmed ordinary bundled NBT continued service, annual
import/export totals, unused component banks, remaining offsettable paid charges,
a source reference, and (for net surplus) the exact true-up month's generation
and delivery recoupment factors and NSC rate. Do not supply gross paid bills as
remaining offsettable charges; already credited amounts must be excluded.
Missing rates and wrong-month factors are rejected. The source kind distinguishes
statement transcription from hypothetical fixtures; a reference does not itself
authenticate a user-supplied document. No production NSC rate table is invented.

The result exposes bonus availability separately from the adjustment. Its
`adjustment_if_all_bonus_applied` is an alternative presentation, not an additional
charge to add to `adjustment_before_bonus`. Unused restricted generation/delivery
credit remains restricted. These values are not automatically payouts.

Rule verification covers true-up dates February 15, 2024–September 21, 2026.
The input must represent a confirmed full annual period (330–400 service days);
shortened periods, termination, RAA, opt-out, CCA and special arrangements remain
excluded. This duration check is a validation envelope, not a published PG&E
billing-period length rule.

Run from the repository root with:

```
/usr/local/bin/python3 -m tools.solar_export.reconcile_pge_true_up INPUT.json
```

JSON keys match the keyword arguments of `reconcile_nbt`; `bank` is an object
with generation/delivery/bonus, `offsettable_paid` has generation/delivery, and
`rates` has month, generation_recoupment_per_kwh, delivery_recoupment_per_kwh,
nsc_per_kwh, source_reference and evidence_kind. Rates can be null for a net
consumer because no NSC/recoupment rates are used.

## Twelve-cycle statement replay

`src/billing/pge_annual_replay.py` connects twelve contiguous, documented
monthly NBT records to the true-up calculation. It rolls separate generation,
delivery and ACC Plus balances forward, totals metered import/export kWh, checks
the remaining eligible charges paid after monthly credits, and passes the
derived annual totals and closing bank to `reconcile_nbt`. Optional stated
monthly electricity amounts due and closing balances can be checked within two
cents. The result reports each month's amount due, the pre-true-up bank, the
separate true-up adjustment, and the next-period bank **before any optional
application of remaining ACC Plus**. A negative adjustment is a bill credit,
not necessarily an immediate refund.

Run a JSON replay with:

```
/usr/local/bin/python3 -m tools.solar_export.replay_pge_annual INPUT.json
```

The annual replay has no setup control on the main browser study page; a
separate setup is planned. The CLI and dedicated local endpoint
`POST /api/v1/pge/annual-studies` remain available. The endpoint accepts schema
version 7 and uses the durable study queue. Existing replay results remain in
ordinary study history with an annual summary, a twelve-cycle credit ledger, a
true-up component table, and downloadable CSV files. Saved input settings can
still be downloaded, but cannot be loaded into the main simulation form. This
replay does not turn the ordinary monthly solar comparison into a full-year
simulation.

The CLI JSON has `account_confirmed`, `records` (exactly twelve) and `rates`
(the existing `TrueUpRates` fields, or `null` for a net consumer). The browser
JSON editor/import accepts `records` and `rates`; its separate name and account
confirmation controls supply those remaining request fields. Each
record has `period_start`, `period_end`, `import_kwh`, `export_kwh`, `charges`
(`generation`, `delivery`, `protected`), `credits_earned` (`generation`,
`delivery`, `bonus`), `offsettable_paid` (`generation`, `delivery`),
`source_reference`, and `evidence_kind` (`statement_transcription` or
`hypothetical`). Optional `stated_amount_due` and `stated_closing_balance` allow
monthly statement reconciliation. `offsettable_paid` is the remaining eligible
paid amount after *all* monthly credits, including ACC Plus; it cannot be
reconstructed from an undifferentiated bill total. This first replay starts with
zero prior-period credit and covers ordinary continued bundled service only.

The records supply billed dollar components from verified statements or clearly
marked hypothetical fixtures. The general `PGE_E_ELEC_PLAN_TIER3` already has
dated total time-of-use import prices for all of 2025 and January–February 2026.
The solar adapter additionally needs the dated generation/delivery/protected
charge split, export-credit values by application vintage, and true-up-month
factors. It currently has those import components only for its June–September
2026 window and its bundled export dataset only for 2026. The general E-ELEC
plan also has an explicit March–May 2026 coverage gap. This replay does **not**
infer any missing component from a total rate, derive annual hourly export
credits, authenticate a user-entered source reference, or optimize battery
dispatch over a year. It is an annual statement replay, not a full annual
simulation.

## Independent reference case

[PG&E Solar Billing Plan Guide, printed page 27](https://www.pge.com/assets/pge/localized/en/docs/clean-energy/solar/pge-solar-billing-plan-guide.pdf)
contains a hypothetical example with 3,000 kWh imports and 5,000 kWh exports.
The test uses its banks, eligible paid-charge balances and illustrative factors:
$80 generation recoupment, $20 delivery recoupment, $59.30 NSC and $1.05 bonus.
It reproduces the published **-$66.35** adjustment and retains $52.94 of unused
generation credit. These illustrative factors are NOT registered utility rates.

Rules: [NBT special conditions 2 and 5](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_NBT.pdf).
Regression fixtures additionally cover net consumers, debit larger than the bank,
missing evidence, wrong-month rates, negative/nonfinite inputs and partial periods.

## Still unfinished

This is a saved statement reconciliation workflow, not complete PG&E solar support.
Annual interval billing needs a complete verified dated solar component split
and export-credit coverage in addition to the existing total import rates;
the twelve-cycle replay accepts documented monthly bill components instead.
Annual dispatch must account for credit value and annual settlement rather than
simply chaining monthly optimizations. Existing monthly web studies retain their
explicit pre-true-up restriction; the annual control requires twelve separately
documented monthly records.

NEM and NEM2 require their own retail-netting, NBC, minimum-bill, eligibility and
true-up rules; neither is implemented by this NBT component. They remain future
PG&E work, not alternative names for NBT.
