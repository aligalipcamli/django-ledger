from django.apps import AppConfig


class SwappableBankAccountAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    label = 'swappable_bank_account_app'
    name = 'django_ledger.tests.swappable_bank_account_app'
    verbose_name = 'Django Ledger Swappable Bank Account Test App'
