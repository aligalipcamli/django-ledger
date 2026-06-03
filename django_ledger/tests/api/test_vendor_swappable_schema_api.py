"""
Schema-level tests for the VendorModel Strategy A FK proof.

These tests require django_ledger.tests.settings_swappable_vendor so the
custom vendor model is configured before migrations and app loading.
"""

import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.checks import run_checks
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, ASSET_CA_PREPAID, CREDIT, DEBIT, EXPENSE_OPERATIONAL
from django_ledger.io.roles import LIABILITY_CL_ACC_PAYABLE
from django_ledger.models import BankAccountModel, BillModel
from django_ledger.models.data_import import ImportJobModel, StagedTransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.models.utils import lazy_loader


CUSTOM_VENDOR_SETTING = 'swappable_vendor_app.CustomVendorModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_VENDORMODEL_MODEL', None) == CUSTOM_VENDOR_SETTING,
    'requires django_ledger.tests.settings_swappable_vendor',
)
class VendorSwappableSchemaAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomVendorModel = apps.get_model('swappable_vendor_app', 'CustomVendorModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_vendor_schema_admin',
            email='api-swappable-vendor-schema-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_setup(self):
        suffix = str(uuid4())[:8]
        name = f'API Swappable Vendor Schema Entity {suffix}'
        entity_model = EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
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
        prepaid_account = coa_model.create_account(
            code='1310',
            name=f'{name} Prepaid',
            role=ASSET_CA_PREPAID,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        payable_account = coa_model.create_account(
            code='2010',
            name=f'{name} Payable',
            role=LIABILITY_CL_ACC_PAYABLE,
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
        )
        bank_account = BankAccountModel(
            name=f'{name} Bank',
            account_model=cash_account,
            account_number='000123456789',
            routing_number='000111000',
            active=True,
        )
        bank_account.configure(entity_slug=entity_model, user_model=self.admin_user, commit=True)
        vendor_model = entity_model.create_vendor(
            {
                'vendor_name': f'{name} Vendor',
                'description': f'{name} vendor description',
                'active': True,
                'hidden': False,
            }
        )
        import_job_model = ImportJobModel.objects.create(
            description=f'{name} Import Job',
            bank_account_model=bank_account,
        )
        import_job_model.configure(commit=True)
        import_job_model.refresh_from_db()
        return {
            'entity_model': entity_model,
            'cash_account': cash_account,
            'prepaid_account': prepaid_account,
            'payable_account': payable_account,
            'expense_account': expense_account,
            'vendor_model': vendor_model,
            'import_job_model': import_job_model,
        }

    def test_schema_vendor_fk_fields_resolve_to_custom_vendor_model(self):
        for model_class, field_name in (
                (BillModel, 'vendor'),
                (ReceiptModel, 'vendor_model'),
                (StagedTransactionModel, 'vendor_model'),
        ):
            with self.subTest(model=model_class._meta.label, field=field_name):
                field = model_class._meta.get_field(field_name)
                self.assertIs(field.remote_field.model, self.CustomVendorModel)

    def test_schema_system_checks_do_not_report_swapped_vendor_fk_errors(self):
        errors = [error for error in run_checks() if error.id == 'fields.E301']

        self.assertEqual(errors, [])

    def test_schema_document_models_accept_custom_vendor_assignment(self):
        setup = self.create_setup()
        vendor_model = setup['vendor_model']

        bill_model = BillModel(
            vendor=vendor_model,
            terms=BillModel.TERMS_NET_30,
            cash_account=setup['cash_account'],
            prepaid_account=setup['prepaid_account'],
            unearned_account=setup['payable_account'],
        )
        receipt_model = ReceiptModel(vendor_model=vendor_model)
        staged_transaction_model = StagedTransactionModel(
            import_job=setup['import_job_model'],
            vendor_model=vendor_model,
        )

        self.assertIsInstance(vendor_model, self.CustomVendorModel)
        self.assertIs(lazy_loader.get_vendor_model(), self.CustomVendorModel)
        self.assertIs(bill_model.vendor, vendor_model)
        self.assertIs(receipt_model.vendor_model, vendor_model)
        self.assertIs(staged_transaction_model.vendor_model, vendor_model)

    def test_schema_document_vendor_fks_persist_custom_vendor_rows(self):
        setup = self.create_setup()
        entity_model = setup['entity_model']
        vendor_model = setup['vendor_model']

        bill_model = entity_model.create_bill(
            vendor_model=vendor_model,
            terms=BillModel.TERMS_NET_30,
            cash_account=setup['cash_account'],
            prepaid_account=setup['prepaid_account'],
            payable_account=setup['payable_account'],
            commit=True,
        )
        receipt_model = ReceiptModel()
        receipt_model.configure(
            entity_model=entity_model,
            receipt_type=ReceiptModel.EXPENSE_RECEIPT,
            amount=Decimal('125.00'),
            receipt_date=date(2026, 1, 15),
            vendor_model=vendor_model,
            charge_account=setup['cash_account'],
            receipt_account=setup['expense_account'],
            commit=True,
        )
        staged_transaction_model = StagedTransactionModel.objects.create(
            import_job=setup['import_job_model'],
            fit_id=f'fit-{str(uuid4())[:8]}',
            date_posted=date(2026, 1, 15),
            amount=Decimal('125.00'),
            name='API Swappable Vendor Schema Staged Transaction',
            memo='API swappable vendor schema staged transaction memo',
            account_model=setup['expense_account'],
            receipt_type=ReceiptModel.EXPENSE_RECEIPT,
            vendor_model=vendor_model,
        )

        self.assertEqual(bill_model.vendor_id, vendor_model.uuid)
        self.assertEqual(receipt_model.vendor_model_id, vendor_model.uuid)
        self.assertEqual(staged_transaction_model.vendor_model_id, vendor_model.uuid)
        self.assertTrue(BillModel.objects.filter(vendor=vendor_model).exists())
        self.assertTrue(ReceiptModel.objects.filter(vendor_model=vendor_model).exists())
        self.assertTrue(StagedTransactionModel.objects.filter(vendor_model=vendor_model).exists())
        self.assertTrue(ReceiptModel.objects.for_vendor(vendor_model).filter(uuid=receipt_model.uuid).exists())
