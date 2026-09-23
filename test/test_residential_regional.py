"""Regional weighting and checked weather replacement tests; no network."""
from dataclasses import replace
import numpy as np
import pandas as pd
import pytest
from src.profiles.residential import ResidentialProfile,Provenance,ResidentialError
from src.profiles.residential.regional_model import combine_regional_profiles
from src.profiles.residential.regional_weather import fill_from_backup
from tools.build_alameda_regional_year import partition_population


def series():
    index=pd.date_range('2024-01-01','2025-01-01',freq='h',inclusive='left',tz='UTC')
    backup=pd.Series(15+np.sin(np.arange(len(index))*.2),index=index)
    local=index.tz_convert('America/Los_Angeles')
    primary=backup+local.month*.1+local.hour*.05
    return primary,backup


def test_backup_recovers_month_hour_offset_and_preserves_observations():
    primary,backup=series();expected=primary.copy()
    primary.iloc[400:424]=np.nan
    filled,audit,diagnostics=fill_from_backup(primary,backup)
    np.testing.assert_allclose(filled,expected)
    pd.testing.assert_series_equal(filled[primary.notna()],primary.dropna())
    assert (audit.weather_quality=='backup_bias_adjusted').sum()==24
    assert diagnostics['held_out_rmse_c']<1e-12


def test_validation_does_not_train_on_held_out_days():
    primary,backup=series()
    held=primary.index.tz_convert('America/Los_Angeles').day.isin([10,11])
    primary.loc[held]+=10
    _,_,diagnostics=fill_from_backup(primary,backup)
    assert diagnostics['held_out_rmse_c']==pytest.approx(10)
    assert diagnostics['held_out_bias_c']==pytest.approx(-10)


def test_backup_missing_when_primary_missing_fails():
    primary,backup=series();primary.iloc[400]=np.nan;backup.iloc[400]=np.nan
    with pytest.raises(ResidentialError,match='Backup unavailable'):
        fill_from_backup(primary,backup)


def test_sparse_pairing_and_grid_mismatch_rejected():
    primary,backup=series()
    with pytest.raises(ResidentialError,match='Insufficient'):
        fill_from_backup(primary.iloc[:48],backup.iloc[:48])
    with pytest.raises(ResidentialError,match='grids'):
        fill_from_backup(primary,backup.iloc[1:])


def test_combination_sums_scaled_energy_not_equal_region_means():
    index=pd.date_range('2024-01-01',periods=24,tz='UTC',freq='h')
    provenance=Provenance('coast','release','weather','fixture','America/Los_Angeles')
    coast=ResidentialProfile(pd.DataFrame({'base':86.,'cooling':0.},index=index),60,provenance,households=86,diagnostics={"population_basis":"occupied_housing_units"})
    inland=ResidentialProfile(pd.DataFrame({'base':14.,'cooling':28.},index=index),60,replace(provenance,region='inland'),households=14,diagnostics={"population_basis":"occupied_housing_units"})
    result=combine_regional_profiles([coast,inland],replace(provenance,region='county'))
    assert result.households==100
    assert result.native_load_kw.eq(128).all()
    assert result.energy_kwh().sum()==coast.energy_kwh().sum()+inland.energy_kwh().sum()
    with pytest.raises(ResidentialError,match='interval grids'):
        combine_regional_profiles([coast,replace(inland,end_uses_kw=inland.end_uses_kw.iloc[1:])],provenance)


def test_partition_uses_climate_zone_and_rejects_vacancy():
    stock=pd.DataFrame({'in.cec_climate_zone':['3','12','3'],'in.vacancy_status':['Occupied']*3,'weight':[10,20,30]})
    groups=partition_population(stock)
    assert groups['3'].weight.sum()==40
    assert groups['12'].weight.sum()==20
    stock.loc[0,'in.vacancy_status']='Vacant'
    with pytest.raises(ValueError,match='Vacant'):
        partition_population(stock)
