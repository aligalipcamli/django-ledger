from django.apps import AppConfig


class SwappablePurchaseOrderAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_ledger.tests.swappable_purchase_order_app'
    label = 'swappable_purchase_order_app'
