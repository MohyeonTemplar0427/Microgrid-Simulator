# Potomac Edison Maryland R and bounded G Type I SOS

Reviewed October 26, 2026. This is a shared-backend/local-browser development
adapter, without stable-engine promotion, deployment or actual-account certification.

## Executable scope

The initial common intersection is **September–October 2026**, matching complete
calendar service, billing month and final-day bill date. Schedule R residential
SOS has complete ordinary tariff-component coverage. Schedule G Type I SOS is a
**verified-charge subtotal**, excluding `g_transmission_minimum_capacity_charge`
and `maryland_state_sales_tax`. These amounts are not zero or exemptions and can
change dispatch rankings. A complete G bill or complete-bill optimum is not claimed.
R studies additionally limit imports to 7,500 kWh per cycle to keep larger-account
environmental-cap interpretation outside scope; this is a study limit, not
residential tariff eligibility.

Verified 2025 adjustment history is incomplete. Final January–May 2026 supply
originals and adopted June–August G transmission versions were not recovered.
R's wider June-onward source dates do not extend the common executable scope.
Proposed/redlined alternatives and neighboring utilities do not fill these gaps.
Full-year 2025, earlier 2026, November/December and shifted/partial periods reject.
The October rate table is published; a completed full-October weather study is
not claimed before the end of October.

## Independent account and network facts

Delivery utility, Maryland jurisdiction, SOS supplier, R/G eligibility, tax locality,
USC assignment, prior usage, billing method and interconnection remain separate
confirmations. The initial locality is hypothetical **unincorporated Washington
County, Maryland**, with ordinary tax status, no extra local energy levy and no
special relocation/service surcharge. County and DLS tax inventories support the
absence of an ordinary county energy levy as an inventory-based inference plus
account confirmation, not an express zero-tax certificate. Weather coordinates
39.60 N, 77.73 W establish neither service territory nor jurisdiction.

The utility supplier tariff identifies **APS**; PJM's emergency index uses FE-AP
for the related multi-state control area. This metadata does not select another
state's retail tariff, assign account eligibility or identify a wholesale node.
SOS retail prices already recover their filed supply/transmission obligations;
no PJM LMP, PLC or NSPL is added to them.

One ordinary secondary 120/240-V single-phase meter/service at unity billing PF
is supported. Continuous service for at least 12 months and absence of Monthly
Service adders are explicit account facts. Other voltage/phase arrangements,
reactive charges, short-term service, off-peak contracts, competitive supply,
Type II/hourly SOS, assistance, AGS/standby, special facilities and adjustments
are outside the selected scope.

## R components and cents

R has a $6 monthly fixed distribution charge and $0.02287/kWh distribution.
Generation prices include supply administration: September $0.10824/kWh and
October $0.10209/kWh, including $0.00400/kWh administration. The implementation
shows the decomposition separately without adding administration twice.
Transmission is $0.00396/kWh. ECA, administrative delivery credit, PURPA,
EmPOWER, franchise tax, environmental surcharge and USC remain separate lines.

The selected residential USC is $0.32/month. The 2026 adjustment sheet explicitly
prints accounting `$ -` for every RRC month, normalized to zero with its raw
notation preserved. Published legislative-refund posting months are September
2025 and February 2026, outside this window; no other historical adjustment or
opening bank is assumed. Filed residential service is state sales-tax exempt.

MES is $0.000149/kWh for bills rendered from July 1, 2026. At 1,000 kWh the raw
$0.149 rounds half-up to $0.15. The existing numeric billing framework retains
unrounded lines, individual component cents and a rounding bound. R's complete
component flag does not certify an exact printed invoice or the globally optimal
rounded-cash bill: optimization uses the unrounded expressions. No additional
blanket GRT/Commission gross-up is imposed on already adjusted filed rates.

## G unmetered and minimum-inactive domain

G is a demand/capacity-priced plan. This implementation supports only an
independently utility-approved **connection without a demand meter**, with that
method retained across grid-only, PV-only and PV/storage scenarios. Existing
Type I membership includes prior demand/usage and utility assignment; it is not
inferred from simulated demand. Its thresholds include 30-minute demand of
25 kW, two consecutive non-summer months above 6,000 kWh or one summer month
above 7,500 kWh. The study uses stricter limits without reconstructing eligibility.

The ordinary G fixed distribution charge is $4.85/month and energy is
$0.02243/kWh. Published current-distribution examples independently give $21.22
for 5 kW/730 kWh and $42.90 for 10 kW/1,460 kWh. They establish the ordinary
branch and disprove routinely adding $1.70 times minimum kW to every bill.
They do not establish a floor-active formula or resolve transmission minima.
Only the below-7.5-kW ordinary branch is executable here.

The tariff defines unmetered minimum capacity from current monthly imported kWh,
not less than half the highest imported kWh in the previous 12 months, divided
by 250 hours. The scope preserves exactly 12 ordered, consecutive prior calendar
observations, at most 6,000 kWh each, ending immediately before the first study
cycle. Each scenario rolls its own history forward; PV does not reset history.
A separate source identifies the initial history and utility approval.

Let `C = max(current_import_kWh, 0.5 * prior_12_month_max_kWh) / 250`.
Because exact minimum placement and the application of half-kW rounding are
not independently benchmarked, numeric acceptance requires both:

- Actual 30-minute import peak is strictly below 7.5 kW and `C + 0.25 <= 7.5 kW`.
- Regular distribution energy charge is at least `1.70 * (C + 0.25)`.

The extra 0.25 kW conservatively covers either no rounding or nearest-half-kW
rounding. This is an acceptance bound, not an invented billed rounding rule.
It makes plausible distribution minimum placements and excess-capacity charges
inactive. Zero/low-import or high-history cases can reject even when a real bill
would be calculable under additional verified rules.

The optimizer uses the regular component expressions without artificial lower
bounds on imports. If the resulting schedule fails numeric acceptance, the study
fails; it does not purchase extra energy just to enter the accepted domain.
Upward minimum adjustments can be relaxed as lower bounds, and an accepted
minimum-inactive schedule reconciles to those modeled distribution charges.
No active-minimum computation or general metered/assessed G implementation is
claimed.

G supply has a 700-kWh block: September $0.13108/$0.06067 per kWh and October
$0.15064/$0.06977, each including $0.00550/kWh supply administration. The numeric
and symbolic expressions share the exact decreasing-block arithmetic. Verified
transmission energy is $0.00440/$0.00214 per kWh, first 700/excess. The tariff's
$0.34 monthly minimum and $0.19/minimum-kW combination/rounding remain unresolved
and are explicitly excluded, not charged as invented additive amounts. Capacity
above 7.5 kW is outside the accepted domain. State sales tax remains excluded
pending an independent compound-base/statutory-bracket benchmark.

The selected G USC is **$1.84/month**, from independently assigned prior-calendar-
year distribution band $175–$1,299, retained throughout 2026. Do not copy another
utility's $1.85 or invent a first-quarter update clock. The optimizer does not
recompute this assigned account fact.

## Calendar, PV/storage and validation

Generation, ECA and administrative credit use their filed service-rendered clocks;
MES/USC/franchise can use bill-rendered dates. Matching complete calendar cycles
and final-day bill dates keep the selected intersection explicit. G's transmission
leaf is effective September 1, even though its generation table lists June–
September. It is not backdated to June. No unverified crossing allocation is used.

PV/storage requires approved ordinary NEM-account service with zero exports and
no AGS/standby/special charges. The NEM clause preserves ordinary energy, capacity,
monthly and minimum rules and does not grant special capacity reductions. With
zero exports, net energy equals imports; unmetered method and prior history must
remain utility-approved. This is conditional account scope, not a general NEM
finding. No opening bank, export credit settlement or standalone storage is
modeled. The implementation caps combined PV/storage nameplate at 25 kW without
claiming size establishes approval. The absent-DER counterfactual removes DER
assertions while retaining tariff, supplier, USC, method and original history.

Shared regional billing math, dispatch, immutable workers, PV/weather, saved
CSV/ZIP and representative OpenDSS remain unchanged. Under the targeted policy,
new-utility tests and directly affected consumers are selected; no full-release
pass is implied. Sources, hashes, physical pages and rejected material are in
[the source ledger](utility_sources/potomac_edison_md/README.md). Candidate identity,
selected checks and acceptance limitations are recorded in
[implementation validation](Potomac_Edison_Maryland_Implementation_Validation.md).
