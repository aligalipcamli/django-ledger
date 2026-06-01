from django.db import models

from django_ledger.models.customer import CustomerModelAbstract


class CustomCustomerModel(CustomerModelAbstract):
    custom_marker = models.CharField(max_length=32, default='custom')

    class Meta(CustomerModelAbstract.Meta):
        abstract = False
        app_label = 'swappable_customer_app'
