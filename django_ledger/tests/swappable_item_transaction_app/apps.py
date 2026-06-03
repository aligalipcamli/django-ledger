from django.apps import AppConfig


class SwappableItemTransactionAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    label = 'swappable_item_transaction_app'
    name = 'django_ledger.tests.swappable_item_transaction_app'
    verbose_name = 'Django Ledger Swappable Item Transaction Test App'
