"""
Schema and persistence tests for the BillModel Swapper proof.

These tests require django_ledger.tests.settings_swappable_bill so the custom
bill model is configured before migrations and app loading.
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
    ASSET_CA_PREPAID,
    EXPENSE_OPERATIONAL,
    LIABILITY_CL_ACC_PAYABLE,
)
from django_ledger.models.bill import BillModel
from django_ledger.models.estimate import EstimateModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.items import ItemTransactionModel, ItemModel
from django_ledger.models.purchase_order import PurchaseOrderModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.models.utils import lazy_loader


CUSTOM_BILL_SETTING = 'swappable_bill_app.CustomBillModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_BILLMODEL_MODEL', None) == CUSTOM_BILL_SETTING,
    'requires django_ledger.tests.settings_swappable_bill',
)
class BillSwappableSchemaAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomBillModel = apps.get_model('swappable_bill_app', 'CustomBillModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_bill_schema_admin',
            email='api-swappable-bill-schema-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Bill Schema Entity'):
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
            code='1310',
            name=f'{name} Prepaid',
            role=ASSET_CA_PREPAID,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='2010',
            name=f'{name} Payable',
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type='credit',
            active=True,
            is_role_default=True,
        )
        expense_account = coa_model.create_account(
            code='6010',
            name=f'{name} Expense',
            role=EXPENSE_OPERATIONAL,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        uom_model = entity_model.create_uom(
            name=f'Unit {suffix}',
            unit_abbr=f'u{suffix[:7]}',
            active=True,
            commit=True,
        )
        expense_item = entity_model.create_item_expense(
            name=f'{name} Expense Item',
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            coa_model=coa_model,
            commit=True,
        )
        vendor_model = entity_model.create_vendor(
            {
                'vendor_name': f'{name} Vendor',
                'description': f'{name} vendor description',
                'active': True,
                'hidden': False,
            },
            commit=True,
        )
        bill_model = entity_model.create_bill(
            vendor_model=vendor_model,
            terms=self.CustomBillModel.TERMS_NET_30,
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        bill_model.refresh_from_db()
        return {
            'entity_model': entity_model,
            'vendor_model': vendor_model,
            'bill_model': bill_model,
            'expense_item': expense_item,
        }

    def test_schema_item_transaction_bill_fk_resolves_to_custom_bill_model(self):
        field = ItemTransactionModel._meta.get_field('bill_model')

        self.assertIs(field.remote_field.model, self.CustomBillModel)

    def test_schema_system_checks_do_not_report_swapped_bill_fk_errors(self):
        errors = [error for error in run_checks() if error.id == 'fields.E301']

        self.assertEqual(errors, [])

    def test_schema_other_document_boundaries_remain_fixed_or_independent(self):
        self.assertEqual(BillModel._meta.swapped, CUSTOM_BILL_SETTING)
        self.assertEqual(InvoiceModel._meta.swappable, 'DJANGO_LEDGER_INVOICEMODEL_MODEL')
        self.assertEqual(EstimateModel._meta.swappable, 'DJANGO_LEDGER_ESTIMATEMODEL_MODEL')
        self.assertEqual(ItemTransactionModel._meta.swappable, 'DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL')
        self.assertEqual(PurchaseOrderModel._meta.swappable, 'DJANGO_LEDGER_PURCHASEORDERMODEL_MODEL')
        self.assertIsNone(ReceiptModel._meta.swappable)

    def test_schema_bill_item_m2m_uses_fixed_item_transaction_through_model(self):
        field = self.CustomBillModel._meta.get_field('bill_items')

        self.assertIs(field.remote_field.through, ItemTransactionModel)
        self.assertIs(
            ItemTransactionModel._meta.get_field('bill_model').remote_field.model,
            self.CustomBillModel,
        )

    def test_schema_item_transaction_accepts_custom_bill_assignment(self):
        setup = self.create_accounting_setup()
        bill_model = setup['bill_model']
        expense_item = setup['expense_item']

        item_tx = ItemTransactionModel(
            bill_model=bill_model,
            item_model=expense_item,
            quantity=1,
            unit_cost=10,
        )

        self.assertIsInstance(bill_model, self.CustomBillModel)
        self.assertIs(item_tx.bill_model, bill_model)

    def test_schema_item_transaction_persists_custom_bill_rows(self):
        setup = self.create_accounting_setup(name='API Swappable Bill Persisted Tx Entity')
        bill_model = setup['bill_model']
        expense_item = setup['expense_item']

        item_tx = ItemTransactionModel.objects.create(
            bill_model=bill_model,
            item_model=expense_item,
        )
        item_tx = ItemTransactionModel.objects.select_related('bill_model', 'item_model').get(uuid=item_tx.uuid)

        self.assertEqual(item_tx.bill_model_id, bill_model.uuid)
        self.assertIsInstance(item_tx.bill_model, self.CustomBillModel)

    def test_schema_custom_bill_itemization_lifecycle_and_payment_smoke(self):
        setup = self.create_accounting_setup(name='API Swappable Bill Lifecycle Entity')
        bill_model = setup['bill_model']
        expense_item = setup['expense_item']
        itemtxs = {
            expense_item.item_number: {
                'quantity': Decimal('2.00'),
                'unit_cost': Decimal('50.00'),
                'total_amount': Decimal('100.00'),
            }
        }

        itemtxs_batch = bill_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=self.CustomBillModel.ITEMIZE_REPLACE,
            commit=True,
        )
        bill_model.mark_as_review(commit=True, date_in_review=date(2026, 1, 16))
        bill_model.mark_as_approved(
            entity_slug=setup['entity_model'].slug,
            user_model=self.admin_user,
            date_approved=date(2026, 1, 17),
            commit=True,
        )
        bill_model.mark_as_paid(
            entity_slug=setup['entity_model'].slug,
            user_model=self.admin_user,
            date_paid=date(2026, 1, 18),
            commit=True,
        )
        bill_model.refresh_from_db()
        item_tx = ItemTransactionModel.objects.select_related('bill_model').get(bill_model=bill_model)

        self.assertEqual(len(itemtxs_batch), 1)
        self.assertIsInstance(bill_model, self.CustomBillModel)
        self.assertTrue(bill_model.is_paid())
        self.assertEqual(bill_model.amount_due, Decimal('100.00'))
        self.assertEqual(bill_model.amount_paid, Decimal('100.00'))
        self.assertTrue(bill_model.ledger.locked)
        self.assertEqual(item_tx.bill_model_id, bill_model.uuid)

    def test_schema_custom_bill_presave_sets_number_and_entity(self):
        setup = self.create_accounting_setup(name='API Swappable Bill Number Entity')
        bill_model = setup['bill_model']

        self.assertIsInstance(bill_model, self.CustomBillModel)
        self.assertEqual(bill_model.entity_model_id, setup['entity_model'].uuid)
        self.assertTrue(bill_model.bill_number)

    def test_schema_ledger_wrapper_uses_custom_bill_accessor(self):
        setup = self.create_accounting_setup(name='API Swappable Bill Ledger Wrapper Entity')
        bill_model = setup['bill_model']
        wrapper_info = bill_model.ledger.get_wrapper_info

        self.assertEqual(wrapper_info[self.CustomBillModel], 'custombillmodel')
        self.assertEqual(bill_model.ledger.get_wrapped_model_instance().uuid, bill_model.uuid)

    def test_schema_fixed_purchase_order_finds_custom_bill_through_item_transactions(self):
        setup = self.create_accounting_setup(name='API Swappable Bill PO Entity')
        po_model = setup['entity_model'].create_purchase_order(date_draft=date(2026, 1, 10), commit=True)
        item_tx = ItemTransactionModel.objects.create(
            po_model=po_model,
            bill_model=setup['bill_model'],
            item_model=setup['expense_item'],
            quantity=1,
            unit_cost=10,
            po_quantity=1,
            po_unit_cost=10,
        )

        bill_qs = po_model.get_po_bill_queryset()

        self.assertEqual(item_tx.bill_model_id, setup['bill_model'].uuid)
        self.assertIs(bill_qs.model, self.CustomBillModel)
        self.assertTrue(bill_qs.filter(uuid=setup['bill_model'].uuid).exists())
