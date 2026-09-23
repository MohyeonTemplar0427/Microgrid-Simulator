"""Combine already scaled regional communities without averaging their weather."""
from .core import ResidentialError, ResidentialProfile


def combine_regional_profiles(profiles, provenance):
    profiles=list(profiles)
    if not profiles: raise ResidentialError('At least one regional profile required')
    first=profiles[0]
    for p in profiles:
        basis=p.diagnostics.get('population_basis',p.diagnostics.get('training_profile',{}).get('diagnostics',{}).get('population_basis'))
        if basis!='occupied_housing_units':
            raise ResidentialError('Regional combination requires explicit occupied-housing-unit basis')
        if p.timestep_minutes!=first.timestep_minutes or not p.end_uses_kw.index.equals(first.end_uses_kw.index):
            raise ResidentialError('Regional profiles must have identical interval grids')
        if set(p.end_uses_kw)!=set(first.end_uses_kw):
            raise ResidentialError('Regional profiles must expose the same disjoint end uses')
        if p.provenance.release!=first.provenance.release:
            raise ResidentialError('Regional stock releases must match')
    frame=first.end_uses_kw*0
    for p in profiles: frame=frame+p.end_uses_kw[frame.columns]
    return ResidentialProfile(frame,first.timestep_minutes,provenance,
        households=sum(p.households for p in profiles),method='regional_weather_response_sum',
        diagnostics=dict(population_basis='occupied_housing_units',calibration_applied=False,
            regional_profiles=[p.manifest() for p in profiles],
            aggregation='Sum of region-specific loads scaled to represented occupied-home counts'))
