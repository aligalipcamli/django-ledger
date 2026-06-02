"""
Schema and persistence tests for the InvoiceModel Swapper proof.

These tests require django_ledger.tests.settings_swappable_invoice so the custom
invoice model is configured before migrations and app loading.
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

from django_ledger.io import (
    ASSET_CA_CASH,
    ASSET_CA_RECEIVABLES,
    COGS,
    INCOME_OPERATIONAL,
    LIABILITY_CL_DEFERRED_REVENUE,
)
from django_ledger.models.bill import BillModel
from django_ledger.models.estimate import EstimateModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.items import ItemTransactionModel
from django_ledger.models.purchase_order import PurchaseOrderModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.models.utils import lazy_loader


CUSTOM_INVOICE_SETTING = 'swappable_invoice_app.CustomInvoiceModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_INVOICEMODEL_MODEL', None) == CUSTOM_INVOICE_SETTING,
    'requires django_ledger.tests.settings_swappable_invoice',
)
class InvoiceSwappableSchemaAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomInvoiceModel = apps.get_model('swappable_invoice_app', 'CustomInvoiceModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_invoice_schema_admin',
            email='api-swappable-invoice-schema-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Invoice Schema Entity'):
        suffix = str(uuid4())[:8]
        name = f'{name} {suffix}'
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
        coa_model.create_account(
            code='1010',
            name=f'{name} Cash',
            role=ASSET_CA_CASH,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='1210',
            name=f'{name} Receivable',
            role=ASSET_CA_RECEIVABLES,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='2310',
            name=f'{name} Deferred Revenue',
            role=LIABILITY_CL_DEFERRED_REVENUE,
            balance_type='credit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='5010',
            name=f'{name} COGS',
            role=COGS,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='4010',
            name=f'{name} Income',
            role=INCOME_OPERATIONAL,
            balance_type='credit',
            active=True,
            is_role_default=True,
        )
        uom_model = entity_model.create_uom(
            name=f'Unit {suffix}',
            unit_abbr=f'u{suffix[:7]}',
            active=True,
            commit=True,
        )
        service_item = entity_model.create_item_service(
            name=f'{name} Service Item',
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )
        CustomerModel = lazy_loader.get_customer_model()
        customer_model = CustomerModel(
            customer_name=f'{name} Customer',
            entity_model=entity_model,
            description=f'{name} Customer description',
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()
        invoice_model = entity_model.create_invoice(
            customer_model=customer_model,
            terms=self.CustomInvoiceModel.TERMS_NET_30,
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        invoice_model.refresh_from_db()
        return {
            'entity_model': entity_model,
            'customer_model': customer_model,
            'invoice_model': invoice_model,
            'service_item': service_item,
        }

    def test_schema_item_transaction_invoice_fk_resolves_to_custom_invoice_model(self):
        field = ItemTransactionModel._meta.get_field('invoice_model')

        self.assertIs(field.remote_field.model, self.CustomInvoiceModel)

    def test_schema_system_checks_do_not_report_swapped_invoice_fk_errors(self):
        errors = [error for error in run_checks() if error.id == 'fields.E301']

        self.assertEqual(errors, [])

    def test_schema_item_transaction_and_other_documents_remain_fixed(self):
        self.assertEqual(ItemTransactionModel._meta.label, 'django_ledger.ItemTransactionModel')
        self.assertIsNone(ItemTransactionModel._meta.swappable)

        for model_class in (BillModel, EstimateModel, PurchaseOrderModel, ReceiptModel):
            with self.subTest(model=model_class.__name__):
                self.assertIsNone(model_class._meta.swappable)

    def test_schema_invoice_item_m2m_uses_fixed_item_transaction_through_model(self):
        field = self.CustomInvoiceModel._meta.get_field('invoice_items')

        self.assertIs(field.remote_field.through, ItemTransactionModel)
        self.assertIs(
            ItemTransactionModel._meta.get_field('invoice_model').remote_field.model,
            self.CustomInvoiceModel,
        )

    def test_schema_item_transaction_accepts_custom_invoice_assignment(self):
        setup = self.create_accounting_setup()
        invoice_model = setup['invoice_model']
        service_item = setup['service_item']

        item_tx = ItemTransactionModel(
            invoice_model=invoice_model,
            item_model=service_item,
            quantity=1,
            unit_cost=10,
        )

        self.assertIsInstance(invoice_model, self.CustomInvoiceModel)
        self.assertIs(item_tx.invoice_model, invoice_model)

    def test_schema_item_transaction_persists_custom_invoice_rows(self):
        setup = self.create_accounting_setup(name='API Swappable Invoice Persisted Tx Entity')
        invoice_model = setup['invoice_model']
        service_item = setup['service_item']

        item_tx = ItemTransactionModel.objects.create(
            invoice_model=invoice_model,
            item_model=service_item,
        )
        item_tx = ItemTransactionModel.objects.select_related('invoice_model', 'item_model').get(uuid=item_tx.uuid)

        self.assertEqual(item_tx.invoice_model_id, invoice_model.uuid)
        self.assertIsInstance(item_tx.invoice_model, self.CustomInvoiceModel)

    def test_schema_custom_invoice_itemization_and_lifecycle_smoke(self):
        setup = self.create_accounting_setup(name='API Swappable Invoice Itemization Entity')
        invoice_model = setup['invoice_model']
        service_item = setup['service_item']
        itemtxs = {
            service_item.item_number: {
                'quantity': Decimal('2.00'),
                'unit_cost': Decimal('50.00'),
                'total_amount': Decimal('100.00'),
            }
        }

        itemtxs_batch = invoice_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=self.CustomInvoiceModel.ITEMIZE_REPLACE,
            commit=True,
        )
        invoice_model.mark_as_review(commit=True, date_in_review=date(2026, 1, 16))
        invoice_model.refresh_from_db()
        item_tx = ItemTransactionModel.objects.select_related('invoice_model').get(invoice_model=invoice_model)

        self.assertEqual(len(itemtxs_batch), 1)
        self.assertIsInstance(invoice_model, self.CustomInvoiceModel)
        self.assertTrue(invoice_model.is_review())
        self.assertEqual(invoice_model.amount_due, Decimal('100.00'))
        self.assertEqual(item_tx.invoice_model_id, invoice_model.uuid)
        self.assertIsInstance(item_tx.invoice_model, self.CustomInvoiceModel)

    def test_schema_custom_invoice_presave_sets_number_and_entity(self):
        setup = self.create_accounting_setup(name='API Swappable Invoice Number Entity')
        invoice_model = setup['invoice_model']

        self.assertIsInstance(invoice_model, self.CustomInvoiceModel)
        self.assertEqual(invoice_model.entity_model_id, setup['entity_model'].uuid)
        self.assertTrue(invoice_model.invoice_number)

    def test_schema_ledger_wrapper_uses_custom_invoice_accessor(self):
        setup = self.create_accounting_setup(name='API Swappable Invoice Ledger Wrapper Entity')
        invoice_model = setup['invoice_model']
        wrapper_info = invoice_model.ledger.get_wrapper_info

        self.assertEqual(wrapper_info[self.CustomInvoiceModel], 'custominvoicemodel')
        self.assertEqual(invoice_model.ledger.get_wrapped_model_instance().uuid, invoice_model.uuid)

    def test_schema_query_shape_custom_header_field_lives_on_invoice_table(self):
        field = self.CustomInvoiceModel._meta.get_field('e_document_status')
        invoice_qs = self.CustomInvoiceModel._base_manager.only(
            'uuid',
            'invoice_number',
            'e_document_status',
        )

        self.assertIs(field.model, self.CustomInvoiceModel)
        self.assertFalse(invoice_qs.query.select_related)
        self.assertIn('e_document_status', {field.name for field in self.CustomInvoiceModel._meta.concrete_fields})
        self.assertNotEqual(self.CustomInvoiceModel._meta.db_table, InvoiceModel._meta.db_table)
