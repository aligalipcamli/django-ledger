from dev_env.settings import *  # noqa: F403


DJANGO_LEDGER_INVOICEMODEL_MODEL = 'swappable_invoice_app.CustomInvoiceModel'

INSTALLED_APPS = [  # noqa: F405
    *INSTALLED_APPS,
    'django_ledger.tests.swappable_invoice_app.apps.SwappableInvoiceAppConfig',
]
