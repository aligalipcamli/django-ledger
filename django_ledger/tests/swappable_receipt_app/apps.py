from django.apps import AppConfig


class SwappableReceiptAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    label = 'swappable_receipt_app'
    name = 'django_ledger.tests.swappable_receipt_app'
    verbose_name = 'Swappable Receipt Test App'
