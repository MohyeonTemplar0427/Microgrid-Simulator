# ComEd cost-neutral battery cycling refinement

The primary objective remains the filed ComEd subtotal before final line-cent
rounding, plus battery wear only when explicitly selected. Primary optimality
must be proven. Throughput refinement then minimizes charge-plus-discharge kWh
under the existing primary cost bound (`optimum + $0.000001`). The same native
load, PV availability, tariff components, demand measurements, battery limits,
continuous SOC across billing cycles and terminal energy apply throughout.

## Selection and proof scope

1. Save independent copies of the proven primary dispatch. Remove dominated
   positive-price simultaneous pairs using the existing SOC-preserving rule.
2. If negative-price mode variables exist, solve a small auxiliary LP with
   their primary values replaced by numeric constants. This can remove extra
   cycling at the same primary cost. Its proof applies only to those fixed
   negative-price mode choices; it does not prove the global minimum throughput.
3. Solve an outer continuous relaxation with the negative-price modes in
   `[0, 1]`. Two valid physical bounds strengthen it: an interval cannot charge
   more than its starting empty battery space, or discharge more than its
   starting stored energy (after efficiency and interval-length conversion).
   These bounds hold for every exclusive physical schedule. The relaxed
   schedule is not automatically executable: simultaneous flows remain invalid.
   Only an `optimal` relaxation supplies a lower bound. When an independently
   validated incumbent matches it within the reported numerical tolerance,
   global minimum throughput is certified and the full search is unnecessary.
4. Otherwise solve the original full secondary MILP, keeping every original mode choice
   free. The validated incumbent supplies a throughput upper bound; every global
   minimum remains in the feasible set. No monthly decomposition, altered SOC
   boundaries, rounded prices or weighted replacement objective is used.
5. Independently validate every candidate's finite values, power balance,
   exclusivity, power limits, PV curtailment, SOC transitions/bounds/endpoints,
   primary objective and throughput. Keep independent copies before another
   solve can overwrite mutable CVXPY variable values.
6. If a matching relaxation bound or the full secondary solve proves optimality
   and the selected dispatch passes these checks, report global minimum
   throughput. Otherwise retain the best validated
   cost-neutral incumbent and report the limited proof scope. An unproven
   secondary result never makes the primary bill optimum unproven.

An interrupted secondary search may supply a physically valid improved incumbent;
it can be retained after the same independent checks. A relaxed result with
simultaneous charging/discharging is rejected even if its objective is lower.
The existing negative-marginal-price binary formulation is preserved. If the
full search fails, a valid relaxation lower bound is retained. Its difference
from selected throughput bounds the possible further reduction, in kWh of
charge plus discharge; it is not promised savings or a dollar estimate.
Inaccurate/interrupted LP objectives and inconsistent or missing bounds never
establish proof. The tolerance remains `max(0.00001 kWh, throughput * 1e-8)`;
no bill-cost tolerance or battery constraint is relaxed.

Both primary and secondary stages have a bounded solver budget: 60 seconds for
one cycle and 60 seconds per linked cycle, capped at 300 seconds. The auxiliary
LP and relaxation each use at most 10 seconds of the same secondary budget.
The full search receives only the remainder. Model construction and
postprocessing add overhead outside the solver's time limit. These limits do
not reduce the optimality standard. See the official
[SciPy MILP status, gap and time-limit definitions](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html).

## Shared browser and desktop results

Schema-10 comparison tables show selected throughput, its reduction relative to
the current primary solution, refinement status, and a nullable
`minimum_throughput_proven` flag. Result manifests retain `throughput_refinement`
under each scenario's optimization metadata:

- `status`: `optimal`, `improved_unproven`, `retained_primary` or `not_applicable`.
- `selected_solution`: primary, fixed-mode refinement, feasible global incumbent
  or proven global minimum.
- `fixed_mode_status` and `global_status`: independent solver outcomes.
- `relaxation_status`, `proof_method` and `global_lower_bound_source` distinguish
  a matched outer bound, full mixed-integer proof, and an unproven result.
- Primary/selected throughput and reduction, in charge-plus-discharge kWh.
- Global throughput lower bound and absolute gap, when the solver supplies a
  finite consistent bound; unavailable bounds remain null.
- Budget and elapsed time. No battery means proof is not applicable, not true.

The default browser/modern desktop comparison additionally shows the remaining
cycling-gap bound and proof method; detailed tables include the lower bound.
Old result tables without these fields continue to render as before.
`throughput_tie_break_status` describes the global secondary outcome for older
consumers; `optimal` can now be established by a matched relaxation bound without
running the full MILP. Warnings explicitly distinguish cost optimality from unproven
minimum cycling. Older saved results lack the new fields and retain their
original data and proof status. Both modern desktop and local browser consume
the same worker/manifest/table path. Candidate development does not promote a
stable engine or enable hosted ComEd data downloads.

## Offline reproduction

Reuse complete private historical studies rather than retrieving providers:

```sh
/usr/local/bin/python3 tools/run_comed_cycling_validation.py \
  --source .cache/comed_actual_2025_equivalent \
  --output .cache/comed_cycling_refinement_2025
```

Use a new empty output directory. The tool verifies cached weather checksums,
re-registers those bytes under a new immutable engine, and submits the saved
residential/commercial 2025 inputs through the independent worker. It performs
the existing independent annual tariff, monthly demand, DST, bill-component,
SOC, exclusivity and OpenDSS audit. It verifies byte-derived input provenance
and exact normalized-input equality against the source studies. It also records
changes in throughput and rounded modeled subtotals, including the declared
rounding bounds; cost-neutral before rounding need not make every independently
rounded bill line identical.

Price-derived schedules, figures and audit reports remain in the private ignored
output store under the existing PJM usage restrictions. The tool loads no
credentials and makes no live API requests. It preserves all original engine
pins, studies and source data. Numerical outcomes and any remaining global
cycling-proof gap belong in that private validation report.
