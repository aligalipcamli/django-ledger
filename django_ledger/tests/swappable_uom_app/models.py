from django.db import models

from django_ledger.models.items import UnitOfMeasureModelAbstract


class CustomUnitOfMeasureModel(UnitOfMeasureModelAbstract):
    custom_marker = models.CharField(max_length=32, default='custom')

    class Meta(UnitOfMeasureModelAbstract.Meta):
        abstract = False
        app_label = 'swappable_uom_app'
