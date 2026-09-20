"""Research/implementation coverage, separate from executable tariff records.

An official schedule's existence does not imply that billing it is supported.
Do not turn these entries into plans until billing and dispatch reconcile.
"""
VERSION = 'la-county-coverage-2026-09-19.1'

PROVIDERS = [
    dict(id='gwp', role='bundled_utility', status='bounded_import_support',
         reason='L-1-A/B, L-2-A/B and LD-2-A; 2025-01-01 through 2026-09-19. Ordinary secondary imports only; no solar settlement.',
         source='https://glendaleca.primegov.com/Portal/Meeting?meetingTemplateId=39969'),
    dict(id='pwp', role='bundled_utility', status='incomplete',
         reason='Billing disabled pending verified street-light tax exemption allocation, restructuring/meter-transition rules, and demand rounding/power-factor implementation.',
         source='https://pwp.cityofpasadena.net/water-and-electric-rates/'),
    dict(id='bwp', role='bundled_utility', status='incomplete',
         reason='Billing disabled pending full adopted schedule/rider rules. Commercial demand is kVA; kW-only dispatch cannot substitute for apparent demand.',
         source='https://www.burbankwaterandpower.com/documents/d/guest/Summary-of-Electric-Rates-by-Customer-Type_Commercial_all'),
    dict(id='alw', role='bundled_utility', status='incomplete',
         reason='Billing disabled pending dated base/PCA/PBC integration, minimum-charge treatment, declining-block optimization and demand rounding/ratchet support.',
         source='https://www.azusaca.gov/553/Rates-Regulations'),
    dict(id='vpu', role='bundled_utility', status='source_incomplete',
         reason='Residential and commercial schedules are listed officially; filed coefficients and complete rider rules have not been retrieved and verified.',
         source='https://www.cityofvernonca.gov/government/public-utilities/electric-rate-schedule'),
    dict(id='ipu', role='bundled_utility', status='source_incomplete',
         reason='Partial-city electric service only. Rate book and account-specific terms remain unverified; no SCE assignment by exclusion.',
         source='https://www.cityofindustry.org/191/Electric'),
    dict(id='ceu', role='generation', delivery_utility='sce', status='source_incomplete',
         reason='Enrollment needs utility acceptance; residential onsite generation/storage is excluded. Generation agreement rates and separate SCE delivery billing remain unimplemented.',
         source='https://www.cerritos.gov/media/ugmlrene/cerritos-electric-service-application.pdf'),
    *[dict(id=identifier, role='generation', delivery_utility='sce', status='incomplete',
           reason='Availability does not establish enrollment. Generation products, SCE unbundled delivery, PCIA vintage, GMS and other applicable CCA-CRS components are not yet jointly verified/implemented.',
           source=source)
      for identifier, source in (
          ('cpa', 'https://cleanpoweralliance.org/residential-rate/'),
          ('lancaster', 'https://www.lancasterenergy.com/'),
          ('pico_prime', 'https://www.poweredbyprime.org/residential-rates'),
          ('pomona', 'https://pomonachoiceenergy.org/'),
          ('epic', 'https://www.palmdaleepicenergy.com/'),
      )],
]


def coverage():
    return dict(version=VERSION, reviewed_on='2026-09-19',
                scope='LA County only; no enrollment inferred from geography',
                providers=[dict(p) for p in PROVIDERS])
