"""Definitions shared by every PG&E schedule, commercial and residential.

Kept separate so the two rate families can live in their own modules without
either importing the other.
"""

from .tariffs import SeasonDefinition

# Summer is June 1 through September 30; winter is October 1 through May 31.
# The same seasons apply to the B-series and to the residential schedules.
PGE_SEASONS = SeasonDefinition(summer_months=frozenset({6, 7, 8, 9}))
