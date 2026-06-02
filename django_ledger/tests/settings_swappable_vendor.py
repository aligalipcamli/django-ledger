from dev_env.settings import *  # noqa: F403


DJANGO_LEDGER_VENDORMODEL_MODEL = 'swappable_vendor_app.CustomVendorModel'

INSTALLED_APPS = [  # noqa: F405
    *INSTALLED_APPS,
    'django_ledger.tests.swappable_vendor_app.apps.SwappableVendorAppConfig',
]
