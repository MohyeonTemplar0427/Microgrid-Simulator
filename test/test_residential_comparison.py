from datetime import date
import pandas as pd
import pytest
from src.billing.baseline import BaselineAllowance,BaselineTerritory,BaselineCode
from src.billing.residential_comparison import compare_cycle,rates_on

BASE=BaselineAllowance(BaselineTerritory.T,BaselineCode.BASIC)


def usage(start,end,power=1):
    return pd.Series(power,index=pd.date_range(start,pd.Timestamp(end)+pd.DateOffset(days=1),
                    freq='h',inclusive='left',tz='America/Los_Angeles'))


def test_september_hand_calculation():
    bill=compare_cycle(usage('2025-09-01','2025-09-30'),BASE)
    allowance=30*6.5
    assert bill['e1_subtotal']==pytest.approx(allowance*.39834+(720-allowance)*.49918)
    assert bill['tou_c_subtotal']==pytest.approx(30*(5*.61457+19*.49157)-allowance*.10084)
    assert bill['base_charge']==0


def test_march_filed_rates_and_base_charge():
    bill=compare_cycle(usage('2026-04-01','2026-04-30'),BASE)
    assert bill['e1_subtotal']==pytest.approx(225*.32561+495*.40702+30*.79343)
    assert bill['tou_c_subtotal']==pytest.approx(30*(5*.39757+19*.36757)-225*.0814+30*.79343)


def test_cycle_is_not_split_at_calendar_month():
    bill=compare_cycle(usage('2025-09-18','2025-10-19'),BASE)
    assert bill['baseline_kWh']==pytest.approx(13*6.5+19*7.5)
    assert bill['rate_segments']==1
    assert bill['tou_c_subtotal']==pytest.approx(13*(5*.61457+19*.49157)+19*(5*.48974+19*.45974)-(13*6.5+19*7.5)*.10084)


def test_refiling_uses_each_segments_rates_and_allowance():
    bill=compare_cycle(usage('2025-08-19','2025-09-17'),BASE)
    assert bill['rate_segments']==2
    a=compare_cycle(usage('2025-08-19','2025-08-31'),BASE)
    b=compare_cycle(usage('2025-09-01','2025-09-17'),BASE)
    assert bill['e1_subtotal']==pytest.approx(a['e1_subtotal']+b['e1_subtotal'])


def test_complete_dst_index_counts_days_not_24_hours():
    series=usage('2025-11-02','2025-11-02',10)
    assert len(series)==25
    assert compare_cycle(series,BASE)['baseline_kWh']==7.5
    with pytest.raises(ValueError,match='every hour'):
        compare_cycle(series.drop(series.index[2]),BASE)


@pytest.mark.parametrize('day',[date(2025,2,28),date(2026,9,18)])
def test_no_rate_extrapolation(day):
    with pytest.raises(ValueError,match='No verified'):rates_on(day)


def test_negative_or_missing_values_rejected():
    s=usage('2025-09-01','2025-09-01').astype(float)
    for value in [-1,float('nan')]:
        s.iloc[3]=value
        with pytest.raises(ValueError,match='finite and nonnegative'):compare_cycle(s,BASE)
