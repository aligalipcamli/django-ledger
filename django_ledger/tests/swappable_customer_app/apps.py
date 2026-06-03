from django.apps import AppConfig


class SwappableCustomerAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    label = 'swappable_customer_app'
    name = 'django_ledger.tests.swappable_customer_app'
    verbose_name = 'Django Ledger Swappable Customer Test App'
