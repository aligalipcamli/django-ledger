from dev_env.settings import *  # noqa: F403


DJANGO_LEDGER_UNITOFMEASUREMODEL_MODEL = 'swappable_uom_app.CustomUnitOfMeasureModel'

INSTALLED_APPS = [  # noqa: F405
    *INSTALLED_APPS,
    'django_ledger.tests.swappable_uom_app.apps.SwappableUOMAppConfig',
]
