from dev_env.settings import *  # noqa: F403


DJANGO_LEDGER_UNITOFMEASUREMODEL_MODEL = 'swappable_uom_app.CustomUnitOfMeasureModel'
DJANGO_LEDGER_ITEMMODEL_MODEL = 'swappable_item_app.CustomItemModel'

INSTALLED_APPS = [  # noqa: F405
    *INSTALLED_APPS,
    'django_ledger.tests.swappable_uom_app.apps.SwappableUOMAppConfig',
    'django_ledger.tests.swappable_item_app.apps.SwappableItemAppConfig',
]
