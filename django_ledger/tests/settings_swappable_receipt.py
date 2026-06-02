from dev_env.settings import *  # noqa: F403


DJANGO_LEDGER_RECEIPTMODEL_MODEL = 'swappable_receipt_app.CustomReceiptModel'

INSTALLED_APPS = [  # noqa: F405
    *INSTALLED_APPS,
    'django_ledger.tests.swappable_receipt_app.apps.SwappableReceiptAppConfig',
]
