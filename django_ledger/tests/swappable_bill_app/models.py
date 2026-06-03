from django.db import models

from django_ledger.models.bill import BillModelAbstract


class CustomBillModel(BillModelAbstract):
    custom_marker = models.CharField(max_length=32, default='custom')
    supplier_document_ref = models.CharField(max_length=64, blank=True)

    class Meta(BillModelAbstract.Meta):
        abstract = False
        app_label = 'swappable_bill_app'
