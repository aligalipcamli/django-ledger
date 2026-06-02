from django.db import models

from django_ledger.models.estimate import EstimateModelAbstract


class CustomEstimateModel(EstimateModelAbstract):
    custom_marker = models.CharField(max_length=32, default='custom')
    external_quote_ref = models.CharField(max_length=64, blank=True)

    class Meta(EstimateModelAbstract.Meta):
        abstract = False
        app_label = 'swappable_estimate_app'
