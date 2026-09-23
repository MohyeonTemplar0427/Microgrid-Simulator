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

This is a backend reconciliation component, not complete PG&E solar support.
Annual interval billing needs complete verified dated import/export coverage and
monthly ledger history. Annual dispatch must account for credit value and annual
settlement rather than simply chaining monthly optimizations. Web and desktop
annual controls are not enabled. Existing monthly web studies retain their
explicit pre-true-up restriction.

NEM and NEM2 require their own retail-netting, NBC, minimum-bill, eligibility and
true-up rules; neither is implemented by this NBT component. They remain the
next PG&E work after annual NBT integration, not alternative names for NBT.
