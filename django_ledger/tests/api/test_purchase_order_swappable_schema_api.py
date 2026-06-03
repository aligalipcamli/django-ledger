"""
Schema and persistence tests for the PurchaseOrderModel Swapper proof.

These tests require django_ledger.tests.settings_swappable_purchase_order so
the custom purchase order model is configured before migrations and app
loading.
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
    ASSET_CA_INVENTORY,
    ASSET_CA_PREPAID,
    COGS,
    EXPENSE_OPERATIONAL,
    INCOME_OPERATIONAL,
    LIABILITY_CL_ACC_PAYABLE,
)
from django_ledger.models.bill import BillModel
from django_ledger.models.data_import import ImportJobModel, StagedTransactionModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.estimate import EstimateModel
from django_ledger.models.items import ItemModel, ItemTransactionModel
from django_ledger.models.purchase_order import PurchaseOrderModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.models.utils import lazy_loader


CUSTOM_PURCHASE_ORDER_SETTING = 'swappable_purchase_order_app.CustomPurchaseOrderModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_PURCHASEORDERMODEL_MODEL', None) == CUSTOM_PURCHASE_ORDER_SETTING,
    'requires django_ledger.tests.settings_swappable_purchase_order',
)
class PurchaseOrderSwappableSchemaAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomPurchaseOrderModel = apps.get_model(
            'swappable_purchase_order_app',
            'CustomPurchaseOrderModel',
        )
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_po_schema_admin',
            email='api-swappable-po-schema-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Purchase Order Schema Entity'):
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
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        prepaid_account = coa_model.create_account(
            code='1310',
            name=f'{name} Prepaid',
            role=ASSET_CA_PREPAID,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        payable_account = coa_model.create_account(
            code='2010',
            name=f'{name} Payable',
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type='credit',
            active=True,
            is_role_default=True,
        )
        inventory_account = coa_model.create_account(
            code='1410',
            name=f'{name} Inventory',
            role=ASSET_CA_INVENTORY,
            balance_type='debit',
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
        inventory_item = entity_model.create_item_inventory(
            name=f'{name} Inventory Item',
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            inventory_account=inventory_account,
            coa_model=coa_model,
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
        po_model = entity_model.create_purchase_order(
            po_title=f'{name} PO',
            date_draft=date(2026, 4, 15),
            commit=True,
        )
        bill_model = entity_model.create_bill(
            vendor_model=vendor_model,
            terms=BillModel.TERMS_NET_30,
            cash_account=cash_account,
            prepaid_account=prepaid_account,
            payable_account=payable_account,
            date_draft=date(2026, 4, 16),
            commit=True,
        )
        return {
            'entity_model': entity_model,
            'inventory_item': inventory_item,
            'expense_item': expense_item,
            'po_model': po_model,
            'bill_model': bill_model,
        }

    def test_schema_item_transaction_po_fk_resolves_to_custom_purchase_order_model(self):
        field = ItemTransactionModel._meta.get_field('po_model')

        self.assertIs(field.remote_field.model, self.CustomPurchaseOrderModel)

    def test_schema_system_checks_do_not_report_swapped_purchase_order_fk_errors(self):
        errors = [error for error in run_checks() if error.id == 'fields.E301']

        self.assertEqual(errors, [])

    def test_schema_other_model_boundaries_remain_fixed_or_independent(self):
        self.assertEqual(PurchaseOrderModel._meta.swapped, CUSTOM_PURCHASE_ORDER_SETTING)
        self.assertEqual(BillModel._meta.swappable, 'DJANGO_LEDGER_BILLMODEL_MODEL')
        self.assertEqual(EstimateModel._meta.swappable, 'DJANGO_LEDGER_ESTIMATEMODEL_MODEL')
        self.assertEqual(ItemTransactionModel._meta.swappable, 'DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL')

        self.assertEqual(ReceiptModel._meta.swappable, 'DJANGO_LEDGER_RECEIPTMODEL_MODEL')
        self.assertIs(lazy_loader.get_receipt_model(), ReceiptModel)

        for model_class in (ImportJobModel, StagedTransactionModel):
            with self.subTest(model=model_class.__name__):
                self.assertIsNone(model_class._meta.swappable)

    def test_schema_purchase_order_item_m2m_uses_fixed_item_transaction_through_model(self):
        field = self.CustomPurchaseOrderModel._meta.get_field('po_items')

        self.assertIs(field.remote_field.through, ItemTransactionModel)
        self.assertIs(
            ItemTransactionModel._meta.get_field('po_model').remote_field.model,
            self.CustomPurchaseOrderModel,
        )

    def test_schema_item_transaction_accepts_custom_purchase_order_assignment(self):
        setup = self.create_accounting_setup()
        po_model = setup['po_model']
        inventory_item = setup['inventory_item']

        item_tx = ItemTransactionModel(
            po_model=po_model,
            item_model=inventory_item,
            po_quantity=1,
            po_unit_cost=10,
        )

        self.assertIsInstance(po_model, self.CustomPurchaseOrderModel)
        self.assertIs(item_tx.po_model, po_model)

    def test_schema_item_transaction_persists_custom_purchase_order_rows(self):
        setup = self.create_accounting_setup(name='API Swappable Purchase Order Persisted Tx Entity')
        po_model = setup['po_model']
        inventory_item = setup['inventory_item']

        item_tx = ItemTransactionModel.objects.create(
            po_model=po_model,
            item_model=inventory_item,
            po_quantity=1,
            po_unit_cost=10,
        )
        item_tx = ItemTransactionModel.objects.select_related('po_model', 'item_model').get(uuid=item_tx.uuid)

        self.assertEqual(item_tx.po_model_id, po_model.uuid)
        self.assertIsInstance(item_tx.po_model, self.CustomPurchaseOrderModel)

    def test_schema_custom_purchase_order_itemization_review_and_approval_smoke(self):
        setup = self.create_accounting_setup(name='API Swappable Purchase Order Lifecycle Entity')
        po_model = setup['po_model']
        inventory_item = setup['inventory_item']
        itemtxs = {
            inventory_item.item_number: {
                'quantity': Decimal('2.00'),
                'unit_cost': Decimal('50.00'),
                'total_amount': Decimal('100.00'),
            }
        }

        itemtxs_batch = po_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=self.CustomPurchaseOrderModel.ITEMIZE_REPLACE,
            commit=True,
        )
        po_model.mark_as_review(commit=True, date_in_review=date(2026, 4, 16))
        po_model.mark_as_approved(commit=True, date_approved=date(2026, 4, 17))
        po_model.refresh_from_db()
        item_tx = ItemTransactionModel.objects.select_related('po_model').get(po_model=po_model)

        self.assertEqual(len(itemtxs_batch), 1)
        self.assertIsInstance(po_model, self.CustomPurchaseOrderModel)
        self.assertTrue(po_model.is_approved())
        self.assertEqual(po_model.po_amount, Decimal('100.00'))
        self.assertEqual(item_tx.po_model_id, po_model.uuid)
        self.assertEqual(item_tx.po_item_status, ItemTransactionModel.STATUS_NOT_ORDERED)

    def test_schema_custom_purchase_order_presave_sets_number(self):
        setup = self.create_accounting_setup(name='API Swappable Purchase Order Number Entity')

        po_model = self.CustomPurchaseOrderModel.objects.create(
            entity=setup['entity_model'],
            po_title='API Swappable Direct Purchase Order',
            date_draft=date(2026, 4, 20),
        )

        self.assertTrue(po_model.po_number)
        self.assertTrue(po_model.po_number.startswith('PO-'))

    def test_schema_custom_purchase_order_finds_bills_through_item_transactions(self):
        setup = self.create_accounting_setup(name='API Swappable Purchase Order Bill Entity')
        po_model = setup['po_model']
        bill_model = setup['bill_model']
        item_tx = ItemTransactionModel.objects.create(
            po_model=po_model,
            bill_model=bill_model,
            item_model=setup['inventory_item'],
            po_quantity=1,
            po_unit_cost=10,
            quantity=1,
            unit_cost=10,
            po_item_status=ItemTransactionModel.STATUS_RECEIVED,
        )

        bill_qs = po_model.get_po_bill_queryset()

        self.assertEqual(item_tx.po_model_id, po_model.uuid)
        self.assertIs(bill_qs.model, BillModel)
        self.assertTrue(bill_qs.filter(uuid=bill_model.uuid).exists())

    def test_schema_inventory_pipeline_finds_custom_purchase_order_rows(self):
        setup = self.create_accounting_setup(name='API Swappable Purchase Order Inventory Entity')
        po_model = setup['po_model']
        po_model.po_status = self.CustomPurchaseOrderModel.PO_STATUS_APPROVED
        po_model.date_approved = date(2026, 4, 17)
        po_model.save(update_fields=['po_status', 'date_approved', 'updated'])
        item_tx = ItemTransactionModel.objects.create(
            po_model=po_model,
            bill_model=setup['bill_model'],
            item_model=setup['inventory_item'],
            po_quantity=3,
            po_unit_cost=20,
            quantity=3,
            unit_cost=20,
            po_item_status=ItemTransactionModel.STATUS_RECEIVED,
        )

        pipeline_qs = ItemTransactionModel.objects.inventory_pipeline(setup['entity_model'])

        self.assertTrue(pipeline_qs.filter(uuid=item_tx.uuid).exists())
        self.assertIsInstance(item_tx.po_model, self.CustomPurchaseOrderModel)
