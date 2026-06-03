from django.db import models

from django_ledger.models.purchase_order import PurchaseOrderModelAbstract


class CustomPurchaseOrderModel(PurchaseOrderModelAbstract):
    custom_marker = models.CharField(max_length=32, default='custom')
    supplier_order_ref = models.CharField(max_length=64, blank=True)

    class Meta(PurchaseOrderModelAbstract.Meta):
        abstract = False
        app_label = 'swappable_purchase_order_app'
