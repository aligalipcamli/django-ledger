from django.apps import AppConfig


class SwappableUOMAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    label = 'swappable_uom_app'
    name = 'django_ledger.tests.swappable_uom_app'
    verbose_name = 'Django Ledger Swappable UOM Test App'
