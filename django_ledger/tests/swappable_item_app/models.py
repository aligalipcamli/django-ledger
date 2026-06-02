from django.db import models

from django_ledger.models.items import ItemModelAbstract


class CustomItemModel(ItemModelAbstract):
    custom_marker = models.CharField(max_length=32, default='custom')

    class Meta(ItemModelAbstract.Meta):
        abstract = False
        app_label = 'swappable_item_app'
