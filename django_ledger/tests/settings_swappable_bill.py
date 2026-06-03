from dev_env.settings import *  # noqa: F403


DJANGO_LEDGER_BILLMODEL_MODEL = 'swappable_bill_app.CustomBillModel'

INSTALLED_APPS = [  # noqa: F405
    *INSTALLED_APPS,
    'django_ledger.tests.swappable_bill_app.apps.SwappableBillAppConfig',
]
