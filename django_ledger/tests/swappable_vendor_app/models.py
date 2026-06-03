from django.db import models

from django_ledger.models.vendor import VendorModelAbstract


class CustomVendorModel(VendorModelAbstract):
    custom_marker = models.CharField(max_length=32, default='custom')

    class Meta(VendorModelAbstract.Meta):
        abstract = False
        app_label = 'swappable_vendor_app'
