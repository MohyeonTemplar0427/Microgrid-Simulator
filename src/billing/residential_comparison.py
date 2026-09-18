"""Bounded import-only E-1/E-TOU-C comparison on actual account billing cycles.

This study adapter is not a dispatch tariff and does not infer marginal prices
from exported COST columns. Account discounts, taxes, climate credits, export,
and minimum-delivery-bill cases are outside its scope.
"""
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from .baseline import BaselineAllowance
from .pge_common import PGE_SEASONS
from .tariffs import get_tariff, TariffError

ARCHIVE = 'https://www.pge.com/assets/rates/tariffs/'
MARCH_FILING = 'https://www.pge.com/tariffs/assets/pdf/adviceletter/ELEC_7846-E.pdf'


@dataclass(frozen=True)
class ComparisonRates:
    start: date
    end: date
    e1_id: str
    summer_peak: float
    summer_off_peak: float
    winter_peak: float
    winter_off_peak: float
    baseline_credit: float
    customer_daily: float
    minimum_daily: float
    source: str


# Historical workbook E-TOU-C rows H11:I14 (2025), H7:I10 (Jan 2026).
# March filing sheets 61096-E and 61125-E; current workbook corroborates
# unchanged energy/base rates through the verification date. June filing
# 7921-E changes climate-credit timing, which is excluded from this comparison.
RATES = (
    ComparisonRates(date(2025,3,1), date(2025,8,31), 'pge_e1_residential_bundled_2025_03_01',
                    .62569,.50269,.50086,.47086,.10301,0,.40317,ARCHIVE+'Res_Inclu_TOU_250301-250831.xlsx'),
    ComparisonRates(date(2025,9,1), date(2025,12,31), 'pge_e1_residential_bundled_2025_09_01',
                    .61457,.49157,.48974,.45974,.10084,0,.40317,ARCHIVE+'Res_Inclu_TOU_250901-251231.xlsx'),
    ComparisonRates(date(2026,1,1), date(2026,2,28), 'pge_e1_residential_bundled_2026_01_01',
                    .58943,.46643,.46460,.43460,.09566,0,.40317,ARCHIVE+'Res_Inclu_TOU_260101-260228.xlsx'),
    ComparisonRates(date(2026,3,1), date(2026,9,17), '',
                    .52240,.39940,.39757,.36757,.08140,.79343,0,MARCH_FILING),
)


def rates_on(day):
    matches = [r for r in RATES if r.start <= day <= r.end]
    if len(matches) != 1:
        raise TariffError(f'No verified residential comparison rates for {day}.')
    return matches[0]


def compare_cycle(usage: pd.Series, baseline: BaselineAllowance) -> dict:
    """Compare one complete billing cycle, with explicit baseline eligibility.

    ``usage`` is interval energy (kWh), indexed at hourly interval starts in
    America/Los_Angeles. Refuse missing hours, DST ambiguity, and negative net
    energy. Rate-refiling segments each accrue their own baseline: an explicit
    study approximation, consistent with the existing timeline billing path.
    """
    idx = usage.index
    if not isinstance(idx, pd.DatetimeIndex) or str(idx.tz) != 'America/Los_Angeles':
        raise ValueError('Supply timezone-aware America/Los_Angeles hourly usage.')
    if len(idx) == 0 or idx.has_duplicates or not idx.is_monotonic_increasing:
        raise ValueError('Usage must be nonempty, ordered, and unique.')
    expected = pd.date_range(idx[0].normalize(), idx[-1].normalize()+pd.DateOffset(days=1),freq='h',inclusive='left')
    if not idx.equals(expected):
        raise ValueError('Supply every hour of the complete billing cycle; no filling is permitted.')
    values = usage.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Import energy must be finite and nonnegative; net export is unsupported.')
    versions = [rates_on(day) for day in idx.date]
    e1 = tou = fixed = minimum = allowance_total = 0.0
    for rate in dict.fromkeys(versions):
        mask = np.array([v == rate for v in versions])
        sub = idx[mask]; energy = values[mask]
        allowance = baseline.allowance_kWh(sub, PGE_SEASONS)
        allowance_total += allowance
        total = float(energy.sum())
        if rate.e1_id:
            tiers = get_tariff(rate.e1_id).energy_tiers
            low, high = tiers[0].rate_per_kWh, tiers[1].rate_per_kWh
        else:
            # Filed March 1 values, not a backward extension of June registry data.
            low, high = .32561, .40702
        e1 += min(total,allowance)*low + max(0,total-allowance)*high
        summer = np.isin(sub.month,[6,7,8,9]); peak = (sub.hour>=16)&(sub.hour<21)
        prices = np.where(summer,np.where(peak,rate.summer_peak,rate.summer_off_peak),
                          np.where(peak,rate.winter_peak,rate.winter_off_peak))
        tou += float(energy @ prices) - min(total,allowance)*rate.baseline_credit
        days = len(sub.normalize().unique())
        fixed += days*rate.customer_daily
        minimum += days*rate.minimum_daily
    # Report energy + base charges only. Delivery-component minimum-bill
    # adjustments are excluded rather than approximated by a bundled floor.
    return dict(usage_kWh=float(values.sum()), baseline_kWh=allowance_total,
                e1_energy=e1,tou_c_energy=tou,base_charge=fixed,
                e1_subtotal=e1+fixed,tou_c_subtotal=tou+fixed,
                delivery_minimum_not_evaluated=bool(minimum),
                tou_c_savings=e1-tou,rate_segments=len(set(versions)),
                sources='; '.join(dict.fromkeys(r.source for r in versions)))
