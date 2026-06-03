from django.apps import AppConfig


class SwappableEstimateAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    label = 'swappable_estimate_app'
    name = 'django_ledger.tests.swappable_estimate_app'
    verbose_name = 'Django Ledger Swappable Estimate Test App'
