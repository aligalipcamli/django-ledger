from django.apps import AppConfig


class SwappableItemAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    label = 'swappable_item_app'
    name = 'django_ledger.tests.swappable_item_app'
    verbose_name = 'Django Ledger Swappable Item Test App'
