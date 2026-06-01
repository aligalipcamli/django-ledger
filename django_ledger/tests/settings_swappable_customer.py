from dev_env.settings import *  # noqa: F403


DJANGO_LEDGER_CUSTOMERMODEL_MODEL = 'swappable_customer_app.CustomCustomerModel'

INSTALLED_APPS = [  # noqa: F405
    *INSTALLED_APPS,
    'django_ledger.tests.swappable_customer_app.apps.SwappableCustomerAppConfig',
]
