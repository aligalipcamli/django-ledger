"""
Runtime tests for ReceiptModel Swapper integration.

These tests require django_ledger.tests.settings_swappable_receipt so the custom
receipt model is configured before Django's app registry is populated.
"""

import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

import swapper
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, CREDIT, DEBIT, EXPENSE_OPERATIONAL, INCOME_OPERATIONAL
from django_ledger.models import BankAccountModel
from django_ledger.models.data_import import ImportJobModel, StagedTransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.models.unit import EntityUnitModel
from django_ledger.models.utils import lazy_loader


CUSTOM_RECEIPT_SETTING = 'swappable_receipt_app.CustomReceiptModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_RECEIPTMODEL_MODEL', None) == CUSTOM_RECEIPT_SETTING,
    'requires django_ledger.tests.settings_swappable_receipt',
)
class ReceiptSwappableRuntimeAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomReceiptModel = apps.get_model('swappable_receipt_app', 'CustomReceiptModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_receipt_admin',
            email='api-swappable-receipt-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Receipt Entity'):
        suffix = str(uuid4())[:8]
        name = f'{name} {suffix}'
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=4,
        )
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f'{name} CoA',
            commit=True,
            assign_as_default=True,
        )
        cash_account = coa_model.create_account(
            code='1010',
            name=f'{name} Cash',
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        income_account = coa_model.create_account(
            code='4010',
            name=f'{name} Income',
            role=INCOME_OPERATIONAL,
            balance_type=CREDIT,
            active=True,
            is_role_default=True,
        )
        expense_account = coa_model.create_account(
            code='6010',
            name=f'{name} Expense',
            role=EXPENSE_OPERATIONAL,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        bank_account = BankAccountModel(
            name=f'{name} Bank Account',
            account_model=cash_account,
            account_number='000123456789',
            routing_number='000111000',
            active=True,
        )
        bank_account.configure(entity_slug=entity_model, user_model=self.admin_user, commit=True)
        CustomerModel = lazy_loader.get_customer_model()
        customer_model = CustomerModel.objects.create(
            customer_name=f'{name} Customer',
            entity_model=entity_model,
            active=True,
        )
        VendorModel = lazy_loader.get_vendor_model()
        vendor_model = VendorModel.objects.create(
            vendor_name=f'{name} Vendor',
            entity_model=entity_model,
            active=True,
        )
        unit_model = EntityUnitModel.add_root(
            name=f'{name} Unit',
            slug=f'{name.lower().replace(" ", "-")}-unit',
            entity=entity_model,
            document_prefix='RCU',
            active=True,
        )
        import_job = ImportJobModel.objects.create(
            description=f'{name} Import Job',
            bank_account_model=bank_account,
        )
        import_job.configure(commit=True)
        import_job.refresh_from_db()
        return {
            'entity_model': entity_model,
            'cash_account': cash_account,
            'income_account': income_account,
            'expense_account': expense_account,
            'bank_account': bank_account,
            'customer_model': customer_model,
            'vendor_model': vendor_model,
            'unit_model': unit_model,
            'import_job': import_job,
        }

    def create_sales_receipt(self, setup, *, amount='125.00'):
        receipt_model = self.CustomReceiptModel()
        receipt_model.configure(
            entity_model=setup['entity_model'],
            receipt_type=self.CustomReceiptModel.SALES_RECEIPT,
            amount=Decimal(amount),
            receipt_date=date(2026, 4, 15),
            customer_model=setup['customer_model'],
            charge_account=setup['cash_account'],
            receipt_account=setup['income_account'],
            commit=True,
        )
        receipt_model.refresh_from_db()
        return receipt_model

    def create_expense_receipt(self, setup, *, amount='75.00'):
        receipt_model = self.CustomReceiptModel()
        receipt_model.configure(
            entity_model=setup['entity_model'],
            receipt_type=self.CustomReceiptModel.EXPENSE_RECEIPT,
            amount=Decimal(amount),
            receipt_date=date(2026, 4, 16),
            vendor_model=setup['vendor_model'],
            charge_account=setup['cash_account'],
            receipt_account=setup['expense_account'],
            commit=True,
        )
        receipt_model.refresh_from_db()
        return receipt_model

    def create_staged_receipt_transaction(self, setup):
        staged_tx = StagedTransactionModel.objects.create(
            import_job=setup['import_job'],
            fit_id=f'FIT-RECEIPT-{str(uuid4())[:8]}',
            date_posted=date(2026, 4, 15),
            amount=Decimal('125.00'),
            amount_split=None,
            name='API Swappable Receipt Staged Transaction',
            memo='API swappable receipt staged transaction memo',
            account_model=setup['income_account'],
            unit_model=setup['unit_model'],
            receipt_type=self.CustomReceiptModel.SALES_RECEIPT,
            customer_model=setup['customer_model'],
            bundle_split=True,
        )
        return StagedTransactionModel.objects.get(uuid=staged_tx.uuid)

    def test_runtime_loader_returns_custom_receipt_model(self):
        self.assertIs(lazy_loader.get_receipt_model(), self.CustomReceiptModel)
        self.assertIs(swapper.load_model('django_ledger', 'ReceiptModel'), self.CustomReceiptModel)
        self.assertEqual(swapper.get_model_name('django_ledger', 'ReceiptModel'), CUSTOM_RECEIPT_SETTING)

    def test_runtime_default_receipt_model_remains_importable_but_not_effective(self):
        self.assertEqual(ReceiptModel._meta.label, 'django_ledger.ReceiptModel')
        self.assertEqual(ReceiptModel._meta.swapped, CUSTOM_RECEIPT_SETTING)
        self.assertIsNot(ReceiptModel, self.CustomReceiptModel)
        self.assertIs(lazy_loader.get_receipt_model(), self.CustomReceiptModel)

    def test_runtime_custom_receipt_configure_persists_numbers_and_posts_ledger(self):
        setup = self.create_accounting_setup()

        receipt_model = self.create_sales_receipt(setup)

        self.assertIsInstance(receipt_model, self.CustomReceiptModel)
        self.assertEqual(receipt_model.custom_marker, 'custom')
        self.assertTrue(receipt_model.receipt_number)
        self.assertEqual(receipt_model.ledger_model.entity_id, setup['entity_model'].uuid)
        self.assertTrue(receipt_model.ledger_model.is_posted())
        self.assertTrue(self.CustomReceiptModel.objects.filter(uuid=receipt_model.uuid).exists())

    def test_runtime_entity_get_receipts_queries_custom_receipt_model(self):
        setup = self.create_accounting_setup(name='API Swappable Receipt Scoped Entity')
        other_setup = self.create_accounting_setup(name='API Other Swappable Receipt Scoped Entity')
        receipt_model = self.create_sales_receipt(setup)
        other_receipt_model = self.create_sales_receipt(other_setup)

        receipt_qs = setup['entity_model'].get_receipts()

        self.assertIs(receipt_qs.model, self.CustomReceiptModel)
        self.assertTrue(receipt_qs.filter(uuid=receipt_model.uuid).exists())
        self.assertFalse(receipt_qs.filter(uuid=other_receipt_model.uuid).exists())

    def test_runtime_customer_and_vendor_receipt_paths_use_custom_receipts(self):
        setup = self.create_accounting_setup(name='API Swappable Receipt Counterparty Entity')
        sales_receipt = self.create_sales_receipt(setup)
        expense_receipt = self.create_expense_receipt(setup)
        receipt_qs = self.CustomReceiptModel.objects.for_entity(setup['entity_model'])

        self.assertTrue(receipt_qs.for_customer(setup['customer_model']).filter(uuid=sales_receipt.uuid).exists())
        self.assertFalse(receipt_qs.for_customer(setup['customer_model']).filter(uuid=expense_receipt.uuid).exists())
        self.assertTrue(receipt_qs.for_vendor(setup['vendor_model']).filter(uuid=expense_receipt.uuid).exists())
        self.assertFalse(receipt_qs.for_vendor(setup['vendor_model']).filter(uuid=sales_receipt.uuid).exists())

    def test_runtime_customer_and_vendor_detail_views_query_custom_receipts(self):
        from django_ledger.views.customer import CustomerModelDetailView
        from django_ledger.views.vendor import VendorModelDetailView

        setup = self.create_accounting_setup(name='API Swappable Receipt Detail View Entity')
        sales_receipt = self.create_sales_receipt(setup)
        expense_receipt = self.create_expense_receipt(setup)

        customer_view = CustomerModelDetailView()
        customer_view.object = setup['customer_model']
        customer_view.AUTHORIZED_ENTITY_MODEL = setup['entity_model']
        customer_context = customer_view.get_context_data()

        vendor_view = VendorModelDetailView()
        vendor_view.object = setup['vendor_model']
        vendor_view.AUTHORIZED_ENTITY_MODEL = setup['entity_model']
        vendor_context = vendor_view.get_context_data()

        self.assertIs(customer_context['receipts'].model, self.CustomReceiptModel)
        self.assertTrue(customer_context['receipts'].filter(uuid=sales_receipt.uuid).exists())
        self.assertFalse(customer_context['receipts'].filter(uuid=expense_receipt.uuid).exists())
        self.assertIs(vendor_context['receipts'].model, self.CustomReceiptModel)
        self.assertTrue(vendor_context['receipts'].filter(uuid=expense_receipt.uuid).exists())
        self.assertFalse(vendor_context['receipts'].filter(uuid=sales_receipt.uuid).exists())

    def test_runtime_staged_transaction_migrate_receipt_creates_custom_receipt(self):
        setup = self.create_accounting_setup(name='API Swappable Receipt Staged Entity')
        staged_tx = self.create_staged_receipt_transaction(setup)

        generated_receipt = staged_tx.generate_receipt_model(receipt_date=date(2026, 4, 15), commit=False)
        self.assertIsInstance(generated_receipt, self.CustomReceiptModel)
        self.assertTrue(staged_tx.can_migrate_receipt())

        staged_tx.migrate_receipt(receipt_date=date(2026, 4, 15))
        staged_tx = StagedTransactionModel.objects.get(uuid=staged_tx.uuid)
        receipt_model = staged_tx.receiptmodel

        self.assertIsInstance(receipt_model, self.CustomReceiptModel)
        self.assertEqual(receipt_model.staged_transaction_model_id, staged_tx.uuid)
        self.assertEqual(receipt_model.customer_model_id, setup['customer_model'].uuid)
        self.assertEqual(receipt_model.receipt_account_id, setup['income_account'].uuid)
        self.assertIsNotNone(staged_tx.transaction_model_id)
        self.assertTrue(StagedTransactionModel.objects.filter(receiptmodel__uuid=receipt_model.uuid).exists())
        self.assertTrue(self.CustomReceiptModel.objects.filter(uuid=receipt_model.uuid).exists())
