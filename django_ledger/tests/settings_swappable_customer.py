from dev_env.settings import *  # noqa: F403


DJANGO_LEDGER_CUSTOMERMODEL_MODEL = 'swappable_customer_app.CustomCustomerModel'

INSTALLED_APPS = [  # noqa: F405
    *INSTALLED_APPS,
    'django_ledger.tests.swappable_customer_app.apps.SwappableCustomerAppConfig',
]

# Phase 1b deliberately leaves existing Django Ledger FKs pointing at the
# built-in customer model; these checks belong to later FK/migration work.
SILENCED_SYSTEM_CHECKS = [
    *globals().get('SILENCED_SYSTEM_CHECKS', []),
    'fields.E301',
]
