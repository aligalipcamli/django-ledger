"""
Schema-level tests for the CustomerModel Strategy A FK proof.

These tests require django_ledger.tests.settings_swappable_customer so the
custom customer model is configured before migrations and app loading.
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

from django_ledger.io import ASSET_CA_CASH, ASSET_CA_RECEIVABLES, CREDIT, DEBIT, INCOME_OPERATIONAL
from django_ledger.io.roles import LIABILITY_CL_DEFERRED_REVENUE
from django_ledger.models import BankAccountModel, InvoiceModel
from django_ledger.models.data_import import ImportJobModel, StagedTransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.estimate import EstimateModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.models.utils import lazy_loader


CUSTOM_CUSTOMER_SETTING = 'swappable_customer_app.CustomCustomerModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_CUSTOMERMODEL_MODEL', None) == CUSTOM_CUSTOMER_SETTING,
    'requires django_ledger.tests.settings_swappable_customer',
)
class CustomerSwappableSchemaAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomCustomerModel = apps.get_model('swappable_customer_app', 'CustomCustomerModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_schema_admin',
            email='api-swappable-schema-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_setup(self):
        suffix = str(uuid4())[:8]
        name = f'API Swappable Schema Entity {suffix}'
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
        receivable_account = coa_model.create_account(
            code='1210',
            name=f'{name} Receivable',
            role=ASSET_CA_RECEIVABLES,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        deferred_account = coa_model.create_account(
            code='2310',
            name=f'{name} Deferred Revenue',
            role=LIABILITY_CL_DEFERRED_REVENUE,
            balance_type=CREDIT,
            active=True,
            is_role_default=True,
        )
        income_account = coa_model.create_account(
            code='4010',
            name=f'{name} Income',
            role=INCOME_OPERATIONAL,
            balance_type=CREDIT,
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
        customer_model = entity_model.create_customer(
            {
                'customer_name': f'{name} Customer',
                'description': f'{name} customer description',
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
            'receivable_account': receivable_account,
            'deferred_account': deferred_account,
            'income_account': income_account,
            'customer_model': customer_model,
            'import_job_model': import_job_model,
        }

    def test_schema_customer_fk_fields_resolve_to_custom_customer_model(self):
        for model_class, field_name in (
                (InvoiceModel, 'customer'),
                (EstimateModel, 'customer'),
                (ReceiptModel, 'customer_model'),
                (StagedTransactionModel, 'customer_model'),
        ):
            with self.subTest(model=model_class._meta.label, field=field_name):
                field = model_class._meta.get_field(field_name)
                self.assertIs(field.remote_field.model, self.CustomCustomerModel)

    def test_schema_system_checks_do_not_report_swapped_customer_fk_errors(self):
        errors = [error for error in run_checks() if error.id == 'fields.E301']

        self.assertEqual(errors, [])

    def test_schema_document_models_accept_custom_customer_assignment(self):
        setup = self.create_setup()
        customer_model = setup['customer_model']

        invoice_model = InvoiceModel(
            customer=customer_model,
            terms=InvoiceModel.TERMS_NET_30,
            cash_account=setup['cash_account'],
            prepaid_account=setup['receivable_account'],
            unearned_account=setup['deferred_account'],
        )
        estimate_model = EstimateModel(
            customer=customer_model,
            entity=setup['entity_model'],
            terms=EstimateModel.CONTRACT_TERMS_FIXED,
            title='API Swappable Schema Estimate',
        )
        receipt_model = ReceiptModel(customer_model=customer_model)
        staged_transaction_model = StagedTransactionModel(
            import_job=setup['import_job_model'],
            customer_model=customer_model,
        )

        self.assertIsInstance(customer_model, self.CustomCustomerModel)
        self.assertIs(lazy_loader.get_customer_model(), self.CustomCustomerModel)
        self.assertIs(invoice_model.customer, customer_model)
        self.assertIs(estimate_model.customer, customer_model)
        self.assertIs(receipt_model.customer_model, customer_model)
        self.assertIs(staged_transaction_model.customer_model, customer_model)

    def test_schema_document_customer_fks_persist_custom_customer_rows(self):
        setup = self.create_setup()
        entity_model = setup['entity_model']
        customer_model = setup['customer_model']

        invoice_model = entity_model.create_invoice(
            customer_model=customer_model,
            terms=InvoiceModel.TERMS_NET_30,
            cash_account=setup['cash_account'],
            prepaid_account=setup['receivable_account'],
            payable_account=setup['deferred_account'],
            commit=True,
        )
        estimate_model = entity_model.create_estimate(
            estimate_title='API Swappable Schema Estimate Persisted',
            contract_terms=EstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=customer_model,
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        receipt_model = ReceiptModel()
        receipt_model.configure(
            entity_model=entity_model,
            receipt_type=ReceiptModel.SALES_RECEIPT,
            amount=Decimal('125.00'),
            receipt_date=date(2026, 1, 15),
            customer_model=customer_model,
            charge_account=setup['cash_account'],
            receipt_account=setup['income_account'],
            commit=True,
        )
        staged_transaction_model = StagedTransactionModel.objects.create(
            import_job=setup['import_job_model'],
            fit_id=f'fit-{str(uuid4())[:8]}',
            date_posted=date(2026, 1, 15),
            amount=Decimal('125.00'),
            name='API Swappable Schema Staged Transaction',
            memo='API swappable schema staged transaction memo',
            account_model=setup['income_account'],
            receipt_type=ReceiptModel.SALES_RECEIPT,
            customer_model=customer_model,
        )

        self.assertEqual(invoice_model.customer_id, customer_model.uuid)
        self.assertEqual(estimate_model.customer_id, customer_model.uuid)
        self.assertEqual(receipt_model.customer_model_id, customer_model.uuid)
        self.assertEqual(staged_transaction_model.customer_model_id, customer_model.uuid)
        self.assertTrue(InvoiceModel.objects.filter(customer=customer_model).exists())
        self.assertTrue(EstimateModel.objects.filter(customer=customer_model).exists())
        self.assertTrue(ReceiptModel.objects.filter(customer_model=customer_model).exists())
        self.assertTrue(StagedTransactionModel.objects.filter(customer_model=customer_model).exists())
