from django.apps import AppConfig


class SwappableInvoiceAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    label = 'swappable_invoice_app'
    name = 'django_ledger.tests.swappable_invoice_app'
    verbose_name = 'Django Ledger Swappable Invoice Test App'
