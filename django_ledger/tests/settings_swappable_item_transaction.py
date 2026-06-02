from dev_env.settings import *  # noqa: F403


DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL = 'swappable_item_transaction_app.CustomItemTransactionModel'

INSTALLED_APPS = [  # noqa: F405
    *INSTALLED_APPS,
    'django_ledger.tests.swappable_item_transaction_app.apps.SwappableItemTransactionAppConfig',
]
