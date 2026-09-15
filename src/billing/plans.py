"""Rate plans and their versions over time.

A **plan** is what a customer chooses and stays on: "PG&E E-1 bundled,
income tier 3". A **version** is what that plan's rates were between two
dates. PG&E refiled residential rates seven times during 2024 alone, so a
study of a single year touches many versions of one plan, and a study of a
single month can touch two.

:mod:`src.billing.tariffs` already describes one version -- a
:class:`TariffDefinition` carries an effective window and refuses a date
outside it. This module adds the layer above: which versions belong to the
same plan, whether they tile the requested dates without gaps or overlaps,
and which one applies on a given local service date.

Nothing here computes money. Billing across a timeline lives in
:mod:`src.billing.charges`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from .tariffs import TariffDefinition, TariffError


class PlanError(TariffError):
    """Raised when a plan's versions cannot answer the question asked."""


@dataclass(frozen=True)
class RatePlanIdentity:
    """What the customer is on, independent of what the rates were.

    Every field is a property of the *account*, not of any one filed rate
    document, which is why the identity survives a refiling while the
    versions under it do not.
    """

    utility: str
    schedule: str          # "E-1", "E-TOU-D", ...
    service_type: str      # bundled / cca / direct_access
    customer_class: str
    #: Free-form discriminator for options that split one schedule into
    #: separately-priced variants -- PG&E's income tiers, a voltage class, a
    #: phase count. Two plans that differ here are different plans.
    variant: str = ""

    @property
    def plan_id(self) -> str:
        parts = [
            self.utility,
            self.schedule,
            self.customer_class,
            self.service_type,
            self.variant,
        ]
        return "|".join(part for part in parts if part)

    def describe(self) -> str:
        variant = f", {self.variant}" if self.variant else ""
        return (
            f"{self.utility} {self.schedule} "
            f"({self.service_type}{variant})"
        )


@dataclass(frozen=True)
class RatePlan:
    """One plan and every filed version of it, in effective-date order."""

    identity: RatePlanIdentity
    versions: tuple[TariffDefinition, ...]

    def __post_init__(self) -> None:
        if not self.versions:
            raise PlanError(
                f"Plan {self.identity.plan_id!r} has no versions."
            )

        ordered = sorted(self.versions, key=lambda v: v.effective_start)
        object.__setattr__(self, "versions", tuple(ordered))

        for earlier, later in zip(ordered, ordered[1:]):
            if earlier.effective_end is None:
                raise PlanError(
                    f"Plan {self.identity.plan_id!r}: version "
                    f"{earlier.tariff_id!r} is open-ended but "
                    f"{later.tariff_id!r} starts after it. Only the newest "
                    f"version may be open-ended."
                )

            if earlier.effective_end >= later.effective_start:
                raise PlanError(
                    f"Plan {self.identity.plan_id!r}: versions "
                    f"{earlier.tariff_id!r} "
                    f"({earlier.effective_start}..{earlier.effective_end}) "
                    f"and {later.tariff_id!r} "
                    f"({later.effective_start}..{later.effective_end}) "
                    f"overlap. Effective windows are inclusive and must not "
                    f"share a date."
                )

    def describe_windows(self) -> str:
        return ", ".join(
            f"{v.tariff_id} ({v.effective_start}.."
            f"{v.effective_end if v.effective_end else 'open'})"
            for v in self.versions
        )

    def version_on(self, service_date: date) -> TariffDefinition:
        """The version effective on one local service date."""

        for version in self.versions:
            if version.is_effective_on(service_date):
                return version

        raise PlanError(
            f"Plan {self.identity.plan_id!r} has no filed version covering "
            f"{service_date}. Available windows: {self.describe_windows()}. "
            f"Rates for an uncovered date must be transcribed from the filed "
            f"document, never inferred from a neighbouring version."
        )

    def coverage_gap(
        self,
        first: date,
        last: date,
    ) -> date | None:
        """The first date in ``first..last`` no version covers, if any."""

        day = first

        while day <= last:
            if not any(v.is_effective_on(day) for v in self.versions):
                return day

            day += timedelta(days=1)

        return None

    def require_coverage(self, first: date, last: date) -> None:
        gap = self.coverage_gap(first, last)

        if gap is not None:
            raise PlanError(
                f"Plan {self.identity.plan_id!r} has no filed version "
                f"covering {gap} (requested {first}..{last}). Available "
                f"windows: {self.describe_windows()}."
            )

    def segments_for(
        self,
        timestamps: pd.DatetimeIndex,
    ) -> tuple[tuple[TariffDefinition, tuple[date, ...]], ...]:
        """Group the horizon's local service dates by the version that bills them.

        Dates come from the timestamps themselves, so a daylight-saving day
        is one service date like any other and is counted exactly once.
        Returned in chronological order, one entry per contiguous run of
        dates under one version.
        """

        if len(timestamps) == 0:
            raise PlanError("A billing timeline needs at least one interval.")

        service_dates = sorted(
            {stamp.date() for stamp in pd.DatetimeIndex(timestamps)}
        )

        self.require_coverage(service_dates[0], service_dates[-1])

        segments: list[tuple[TariffDefinition, list[date]]] = []

        for service_date in service_dates:
            version = self.version_on(service_date)

            if segments and segments[-1][0].tariff_id == version.tariff_id:
                segments[-1][1].append(service_date)
            else:
                segments.append((version, [service_date]))

        return tuple(
            (version, tuple(dates)) for version, dates in segments
        )


PLAN_REGISTRY: dict[str, RatePlan] = {}


def register_plan(plan: RatePlan) -> RatePlan:
    plan_id = plan.identity.plan_id

    if plan_id in PLAN_REGISTRY:
        raise PlanError(f"Plan {plan_id!r} is already registered.")

    PLAN_REGISTRY[plan_id] = plan
    return plan


def get_plan(plan_id: str) -> RatePlan:
    if plan_id not in PLAN_REGISTRY:
        raise PlanError(
            f"Unknown plan {plan_id!r}. Registered plans: "
            f"{sorted(PLAN_REGISTRY)}."
        )

    return PLAN_REGISTRY[plan_id]


def supported_plans() -> tuple[str, ...]:
    return tuple(sorted(PLAN_REGISTRY))
