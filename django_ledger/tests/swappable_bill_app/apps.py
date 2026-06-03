from django.apps import AppConfig


class SwappableBillAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_ledger.tests.swappable_bill_app'
    label = 'swappable_bill_app'
