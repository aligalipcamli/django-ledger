from django.db import models

from django_ledger.models.receipt import ReceiptModelAbstract


class CustomReceiptModel(ReceiptModelAbstract):
    custom_marker = models.CharField(max_length=32, default='custom')
    payment_channel = models.CharField(max_length=32, blank=True)

    class Meta(ReceiptModelAbstract.Meta):
        abstract = False
        app_label = 'swappable_receipt_app'
