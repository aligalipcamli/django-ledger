from django.db import models

from django_ledger.models.invoice import InvoiceModelAbstract


class CustomInvoiceModel(InvoiceModelAbstract):
    custom_marker = models.CharField(max_length=32, default='custom')
    e_document_status = models.CharField(max_length=32, blank=True)

    class Meta(InvoiceModelAbstract.Meta):
        abstract = False
        app_label = 'swappable_invoice_app'
