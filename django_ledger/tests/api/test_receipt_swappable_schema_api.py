"""
Schema tests for ReceiptModel Swapper integration.

These tests require django_ledger.tests.settings_swappable_receipt so the custom
receipt model is configured before migrations and app loading.
"""

import unittest

from django.apps import apps
from django.conf import settings
from django.core.checks import run_checks
from django.test import TestCase

from django_ledger.models.customer import CustomerModel
from django_ledger.models.data_import import ImportJobModel, StagedTransactionModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.models.utils import lazy_loader
from django_ledger.models.vendor import VendorModel


CUSTOM_RECEIPT_SETTING = 'swappable_receipt_app.CustomReceiptModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_RECEIPTMODEL_MODEL', None) == CUSTOM_RECEIPT_SETTING,
    'requires django_ledger.tests.settings_swappable_receipt',
)
class ReceiptSwappableSchemaAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomReceiptModel = apps.get_model('swappable_receipt_app', 'CustomReceiptModel')

    def test_schema_receipt_model_is_swapped_out(self):
        self.assertEqual(ReceiptModel._meta.label, 'django_ledger.ReceiptModel')
        self.assertEqual(ReceiptModel._meta.swapped, CUSTOM_RECEIPT_SETTING)
        self.assertIs(lazy_loader.get_receipt_model(), self.CustomReceiptModel)

    def test_schema_customer_vendor_fks_resolve_to_effective_counterparty_models(self):
        customer_field = self.CustomReceiptModel._meta.get_field('customer_model')
        vendor_field = self.CustomReceiptModel._meta.get_field('vendor_model')

        self.assertIs(customer_field.remote_field.model, CustomerModel)
        self.assertIs(vendor_field.remote_field.model, VendorModel)

    def test_schema_staged_transaction_fk_uses_fixed_staged_model_with_stable_reverse_name(self):
        field = self.CustomReceiptModel._meta.get_field('staged_transaction_model')

        self.assertIs(field.remote_field.model, StagedTransactionModel)
        self.assertEqual(field.remote_field.get_accessor_name(), 'receiptmodel')
        self.assertEqual(field.related_query_name(), 'receiptmodel')

    def test_schema_import_job_and_staged_transaction_remain_fixed(self):
        self.assertIsNone(ImportJobModel._meta.swappable)
        self.assertIsNone(StagedTransactionModel._meta.swappable)
        self.assertIs(lazy_loader.get_staged_txs_model(), StagedTransactionModel)

    def test_schema_system_checks_do_not_report_swapped_receipt_fk_errors(self):
        errors = [error for error in run_checks() if error.id == 'fields.E301']

        self.assertEqual(errors, [])
