"""Explicit regional account facts, independent of weather and wholesale nodes."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RegionalAccount:
    distribution_utility: str
    state_jurisdiction: str
    retail_supplier: str
    customer_class: str
    tariff: str
    grid_operator: str
    transmission_zone: str
    wholesale_pricing_location: dict | None
    utility_verification: dict

    def validate_dominion(self):
        expected = dict(distribution_utility="dominion_energy_virginia", state_jurisdiction="VA",
                        retail_supplier="dominion_bundled", customer_class="commercial",
                        tariff="dominion_gs2t", grid_operator="PJM", transmission_zone="DOM")
        if any(getattr(self, k) != v for k, v in expected.items()):
            raise ValueError("This candidate supports Dominion Virginia bundled commercial GS-2T only.")
        evidence = self.utility_verification
        if not isinstance(evidence, dict) or evidence.get("kind") not in ("electricity_bill", "utility_confirmation", "hypothetical_case") or not isinstance(evidence.get("reference"), str) or not evidence["reference"].strip():
            raise ValueError("Supply explicit utility/account verification or a labeled hypothetical case; location and pricing nodes do not establish service.")
        location = self.wholesale_pricing_location
        if location is not None:
            if not isinstance(location, dict) or set(location) != {"pnode_id", "pnode_name", "zone", "source"} or not str(location["pnode_id"]).isdigit() or not all(isinstance(location[k], str) and location[k].strip() for k in ("pnode_name", "zone", "source")):
                raise ValueError("A pricing location needs its explicit numeric ID, name, zone and verification source.")
            if location["zone"] != self.transmission_zone:
                raise ValueError("The candidate requires an explicitly verified DOM pricing location; no hub substitution is allowed.")
        return self
