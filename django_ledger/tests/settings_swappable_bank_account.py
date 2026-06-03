from dev_env.settings import *  # noqa: F403


DJANGO_LEDGER_BANKACCOUNTMODEL_MODEL = 'swappable_bank_account_app.CustomBankAccountModel'

INSTALLED_APPS = [  # noqa: F405
    *INSTALLED_APPS,
    'django_ledger.tests.swappable_bank_account_app.apps.SwappableBankAccountAppConfig',
]
