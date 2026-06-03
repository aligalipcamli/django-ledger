from django.db import models

from django_ledger.models.bank_account import BankAccountModelAbstract


class CustomBankAccountModel(BankAccountModelAbstract):
    custom_marker = models.CharField(max_length=32, default='custom')

    class Meta(BankAccountModelAbstract.Meta):
        abstract = False
        app_label = 'swappable_bank_account_app'
