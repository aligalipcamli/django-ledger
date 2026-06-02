from django.db import models

from django_ledger.models.items import ItemTransactionModelAbstract


class CustomItemTransactionModel(ItemTransactionModelAbstract):
    custom_marker = models.CharField(max_length=32, default='custom')
    line_tax_total = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    class Meta(ItemTransactionModelAbstract.Meta):
        abstract = False
        app_label = 'swappable_item_transaction_app'
