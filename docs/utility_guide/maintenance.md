# Utility guide maintenance and evidence

[Back to the utility guide](../Utility_User_Guide.md)

Review date: October 15, 2026. This is a documentation inventory, not a new runtime or tariff validation report. No test-suite result or release promotion is asserted by this guide.

## Scope and evidence

Official utility, city, and provider pages establish identities, service roles, and regional descriptions. Links appear in each profile. Repository code and implementation notes establish modeled support; utility websites do not prove simulator support. The 19 implemented-provider profiles include six CCA generation providers. Dominion Virginia is a twentieth, separately labeled limited candidate.

Each profile keeps company facts separate from simulator coverage. Suggested study inputs are modeling guidance, not claims of a measured regional load curve. Population totals, customer counts, market-share rankings, and comparative rate claims were deliberately omitted because they are unnecessary for these introductions and need separate dated comparisons.

## Source and coverage checks

Runtime identity and plan checks included `src/billing/services.py`, `la_coverage.py`, `socal.py`, `san_diego.py`, `bay_area_cca.py`, and the utility-specific billing modules. Incomplete LA coverage entries were not counted as implemented. The standalone CPA solar-credit ledger was distinguished from complete account integration.

Newer Southern California solar and shared electrical-replay notes take precedence over older “solar deferred” or “no AC replay” statements in the LA coverage document. Treat any further disagreement as a reason to inspect the actual executable path before expanding claims.

The official ComEd fact sheet linked in its profile is historical and supports only the company identity and northern Illinois geography; no old customer counts or leadership information were carried forward. Some official pages were accessible through search indexing but direct fetches timed out or returned access restrictions (WestLight name-change page and SVP about page). Their matched official search records and existing dated repository evidence support the limited statements used here.

Implementation documents consulted at authoring time are listed below. SHA-256 fingerprints make the review snapshot explicit while other agents continue editing. They do not pin the executable engine.

| Repository document | SHA-256 at guide review |
| --- | --- |
| [Bay_Area_CCA_Billing.md](../Bay_Area_CCA_Billing.md) | `336699488002994a08a92937aad74fdf9ec59d8d51b8a327ee084d1f1aa87d83` |
| [CleanPowerSF.md](../CleanPowerSF.md) | `d97d584c5d048394a130fc1b9da8d0f34a4f226f1c1393998c3e105c80bf8339` |
| [ComEd_Historical_Annual_Inputs.md](../ComEd_Historical_Annual_Inputs.md) | `01683a5d7ae2fa0df563801b4ee081f7a3b7e093e825d0ffaccb2c9bd2be7328` |
| [ComEd_Historical_Rates_and_Billing_Cycles.md](../ComEd_Historical_Rates_and_Billing_Cycles.md) | `0bd6a8f6c88ba33e72c6460d417cc71919c7e2014d0ab512327203e941c17e9d` |
| [ComEd_Simulation_Integration.md](../ComEd_Simulation_Integration.md) | `c290f16469e1b1cdd48f349a78bd090a3f8c9e68e2a051d879cd8ce593b46a45` |
| [Hetch_Hetchy_Power.md](../Hetch_Hetchy_Power.md) | `36c5cd61551a0b1e5b0100ea5df8cec9515a5b18ddd15757241cdaed11ddf514` |
| [LA_County_Utilities.md](../LA_County_Utilities.md) | `dc256d764f4d2795e21d870538cc2b240d0b9544c4a15fe574b9d79b42ad9882` |
| [Microgrid_Backend_Architecture.md](../Microgrid_Backend_Architecture.md) | `fe3bbf08504eec3a5331241bbfd03f16fde5ce47986b55a32af795e61f36fcf7` |
| [Municipal_Utilities.md](../Municipal_Utilities.md) | `fbb53a63e9211db1d62558d80770f5d7f1a3bd68d5afc8a962626ca1dbba9cbc` |
| [PGE_Tariff_Reference.md](../PGE_Tariff_Reference.md) | `1dad21d0e702a74a9f0b75710f76b352580ad8e8d5b1747f830db754ef0748c8` |
| [PJM_Dominion_Candidate.md](../PJM_Dominion_Candidate.md) | `90fa34bdbce9ccca176c9a86fd1b76e4e5d7b26ece9793522634f59dcbf0e3ee` |
| [San_Diego.md](../San_Diego.md) | `cdf95740ec59bff249a4139bba19bd6d2970ad6f041daab135da264d41d9b87d` |
| [Southern_California.md](../Southern_California.md) | `86c327701ea16edd05e87502b6cc03abfb119d1e232fdf4c2993696463c38777` |
| [Utility_Electrical_Validation.md](../Utility_Electrical_Validation.md) | `87e7f329b8ff5d4ed9308fcfdc29593b48210f4751693ea0c2aad709d1827522` |

## Updating a profile

1. Read the current profile, relevant code, official source, and implementation notes before editing. Preserve concurrent work.
2. Keep delivery utility, generation provider, state jurisdiction, tariff eligibility, and wholesale market distinct.
3. Verify changed plan/date support against billing, optimizer, and main-browser paths. A visible option or research record is insufficient.
4. Update the profile, overview row, review date, and evidence record together. Preserve a visible candidate or unsupported designation until acceptance is documented.
5. Check relative links and keep public background sources beside the claims they support. Do not copy numerical rates here; link to the authoritative tariff documentation.
6. For Dominion North Carolina or PSE&G, add accepted profiles only after the implementation handoff establishes exact coverage. Do not treat the earlier requested implementation as completion.
7. These Markdown documents can supply future browser help content, but this documentation task does not install help panels or modify application code.
