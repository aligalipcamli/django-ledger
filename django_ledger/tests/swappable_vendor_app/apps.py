from django.apps import AppConfig


class SwappableVendorAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    label = 'swappable_vendor_app'
    name = 'django_ledger.tests.swappable_vendor_app'
    verbose_name = 'Django Ledger Swappable Vendor Test App'
