"""
Integration smoke tests for PurchaseOrderModel swapping with adjacent models.
"""

import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
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
from django_ledger.models.entity import EntityModel
from django_ledger.models.estimate import EstimateModel
from django_ledger.models.items import ItemModel, ItemTransactionModel
from django_ledger.models.purchase_order import PurchaseOrderModel
from django_ledger.models.utils import lazy_loader


CUSTOM_PURCHASE_ORDER_SETTING = 'swappable_purchase_order_app.CustomPurchaseOrderModel'
CUSTOM_ITEM_TRANSACTION_SETTING = 'swappable_item_transaction_app.CustomItemTransactionModel'
CUSTOM_ESTIMATE_SETTING = 'swappable_estimate_app.CustomEstimateModel'
CUSTOM_BILL_SETTING = 'swappable_bill_app.CustomBillModel'


class PurchaseOrderSwappableIntegrationMixin:
    @classmethod
    def setUpTestData(cls):
        cls.CustomPurchaseOrderModel = apps.get_model(
            'swappable_purchase_order_app',
            'CustomPurchaseOrderModel',
        )
        cls.admin_user = get_user_model().objects.create_user(
            username=f'{cls.__name__.lower()}_admin',
            email=f'{cls.__name__.lower()}@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_entity_setup(self, name):
        suffix = str(uuid4())[:8]
        entity_model = EntityModel.create_entity(
            name=f'{name} {suffix}',
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=4,
        )
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f'{entity_model.name} CoA',
            commit=True,
            assign_as_default=True,
        )
        cash_account = coa_model.create_account(
            code='1010',
            name=f'{entity_model.name} Cash',
            role=ASSET_CA_CASH,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        prepaid_account = coa_model.create_account(
            code='1310',
            name=f'{entity_model.name} Prepaid',
            role=ASSET_CA_PREPAID,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        payable_account = coa_model.create_account(
            code='2010',
            name=f'{entity_model.name} Payable',
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type='credit',
            active=True,
            is_role_default=True,
        )
        inventory_account = coa_model.create_account(
            code='1410',
            name=f'{entity_model.name} Inventory',
            role=ASSET_CA_INVENTORY,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='4010',
            name=f'{entity_model.name} Income',
            role=INCOME_OPERATIONAL,
            balance_type='credit',
            active=True,
            is_role_default=True,
        )
        expense_account = coa_model.create_account(
            code='6010',
            name=f'{entity_model.name} Expense',
            role=EXPENSE_OPERATIONAL,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='5010',
            name=f'{entity_model.name} COGS',
            role=COGS,
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
            name=f'{entity_model.name} Inventory Item',
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            inventory_account=inventory_account,
            coa_model=coa_model,
            commit=True,
        )
        entity_model.create_item_expense(
            name=f'{entity_model.name} Expense Item',
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            coa_model=coa_model,
            commit=True,
        )
        vendor_model = entity_model.create_vendor(
            {
                'vendor_name': f'{entity_model.name} Vendor',
                'description': f'{entity_model.name} vendor description',
                'active': True,
                'hidden': False,
            },
            commit=True,
        )
        return {
            'cash_account': cash_account,
            'entity_model': entity_model,
            'inventory_item': inventory_item,
            'payable_account': payable_account,
            'prepaid_account': prepaid_account,
            'vendor_model': vendor_model,
        }

    def create_customer(self, entity_model):
        CustomerModel = lazy_loader.get_customer_model()
        customer_model = CustomerModel(
            customer_name=f'{entity_model.name} Customer',
            entity_model=entity_model,
            description=f'{entity_model.name} customer description',
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()
        return customer_model


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_PURCHASEORDERMODEL_MODEL', None) == CUSTOM_PURCHASE_ORDER_SETTING
    and getattr(settings, 'DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL', None) == CUSTOM_ITEM_TRANSACTION_SETTING,
    'requires django_ledger.tests.settings_swappable_purchase_order_item_transaction',
)
class PurchaseOrderItemTransactionSwappableIntegrationAPITest(
    PurchaseOrderSwappableIntegrationMixin,
    TestCase,
):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.CustomItemTransactionModel = apps.get_model(
            'swappable_item_transaction_app',
            'CustomItemTransactionModel',
        )

    def test_combined_custom_purchase_order_itemization_uses_custom_item_transaction(self):
        setup = self.create_entity_setup('API Swappable Purchase Order ItemTx Entity')
        po_model = setup['entity_model'].create_purchase_order(
            po_title='API Swappable Purchase Order ItemTx PO',
            date_draft=date(2026, 4, 15),
            commit=True,
        )
        itemtxs = {
            setup['inventory_item'].item_number: {
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
        item_tx = self.CustomItemTransactionModel.objects.select_related('po_model', 'item_model').get(
            po_model=po_model,
        )

        self.assertIs(lazy_loader.get_purchase_order_model(), self.CustomPurchaseOrderModel)
        self.assertIs(lazy_loader.get_item_transaction_model(), self.CustomItemTransactionModel)
        self.assertEqual(PurchaseOrderModel._meta.swapped, CUSTOM_PURCHASE_ORDER_SETTING)
        self.assertEqual(ItemTransactionModel._meta.swapped, CUSTOM_ITEM_TRANSACTION_SETTING)
        self.assertIs(
            self.CustomItemTransactionModel._meta.get_field('po_model').remote_field.model,
            self.CustomPurchaseOrderModel,
        )
        self.assertEqual(len(itemtxs_batch), 1)
        self.assertIsInstance(item_tx, self.CustomItemTransactionModel)
        self.assertIsInstance(item_tx.po_model, self.CustomPurchaseOrderModel)
        self.assertEqual(item_tx.po_total_amount, Decimal('100.00'))


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_PURCHASEORDERMODEL_MODEL', None) == CUSTOM_PURCHASE_ORDER_SETTING
    and getattr(settings, 'DJANGO_LEDGER_ESTIMATEMODEL_MODEL', None) == CUSTOM_ESTIMATE_SETTING,
    'requires django_ledger.tests.settings_swappable_purchase_order_estimate',
)
class PurchaseOrderEstimateSwappableIntegrationAPITest(PurchaseOrderSwappableIntegrationMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.CustomEstimateModel = apps.get_model('swappable_estimate_app', 'CustomEstimateModel')

    def test_combined_custom_purchase_order_binds_custom_estimate(self):
        setup = self.create_entity_setup('API Swappable Purchase Order Estimate Entity')
        customer_model = self.create_customer(setup['entity_model'])
        estimate_model = setup['entity_model'].create_estimate(
            estimate_title='API Swappable Purchase Order Estimate Contract',
            contract_terms=self.CustomEstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=customer_model,
            date_draft=date(2026, 4, 10),
            commit=True,
        )
        estimate_model.status = self.CustomEstimateModel.CONTRACT_STATUS_APPROVED
        estimate_model.date_approved = date(2026, 4, 12)
        estimate_model.save(update_fields=['status', 'date_approved', 'updated'])

        po_model = setup['entity_model'].create_purchase_order(
            po_title='API Swappable Purchase Order Estimate PO',
            estimate_model=estimate_model,
            date_draft=date(2026, 4, 15),
            commit=True,
        )
        po_model.refresh_from_db()

        self.assertIs(lazy_loader.get_purchase_order_model(), self.CustomPurchaseOrderModel)
        self.assertIs(lazy_loader.get_estimate_model(), self.CustomEstimateModel)
        self.assertEqual(PurchaseOrderModel._meta.swapped, CUSTOM_PURCHASE_ORDER_SETTING)
        self.assertEqual(EstimateModel._meta.swapped, CUSTOM_ESTIMATE_SETTING)
        self.assertIs(self.CustomPurchaseOrderModel._meta.get_field('ce_model').remote_field.model,
                      self.CustomEstimateModel)
        self.assertIsInstance(po_model, self.CustomPurchaseOrderModel)
        self.assertIsInstance(po_model.ce_model, self.CustomEstimateModel)
        self.assertEqual(po_model.ce_model_id, estimate_model.uuid)


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_PURCHASEORDERMODEL_MODEL', None) == CUSTOM_PURCHASE_ORDER_SETTING
    and getattr(settings, 'DJANGO_LEDGER_BILLMODEL_MODEL', None) == CUSTOM_BILL_SETTING,
    'requires django_ledger.tests.settings_swappable_purchase_order_bill',
)
class PurchaseOrderBillSwappableIntegrationAPITest(PurchaseOrderSwappableIntegrationMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.CustomBillModel = apps.get_model('swappable_bill_app', 'CustomBillModel')

    def test_combined_custom_purchase_order_finds_custom_bill(self):
        setup = self.create_entity_setup('API Swappable Purchase Order Bill Entity')
        po_model = setup['entity_model'].create_purchase_order(
            po_title='API Swappable Purchase Order Bill PO',
            date_draft=date(2026, 4, 15),
            commit=True,
        )
        bill_model = setup['entity_model'].create_bill(
            vendor_model=setup['vendor_model'],
            terms=self.CustomBillModel.TERMS_NET_30,
            cash_account=setup['cash_account'],
            prepaid_account=setup['prepaid_account'],
            payable_account=setup['payable_account'],
            date_draft=date(2026, 4, 16),
            commit=True,
        )
        item_tx = lazy_loader.get_item_transaction_model().objects.create(
            po_model=po_model,
            bill_model=bill_model,
            item_model=setup['inventory_item'],
            po_quantity=1,
            po_unit_cost=10,
            quantity=1,
            unit_cost=10,
        )

        bill_qs = po_model.get_po_bill_queryset()

        self.assertIs(lazy_loader.get_purchase_order_model(), self.CustomPurchaseOrderModel)
        self.assertIs(lazy_loader.get_bill_model(), self.CustomBillModel)
        self.assertEqual(PurchaseOrderModel._meta.swapped, CUSTOM_PURCHASE_ORDER_SETTING)
        self.assertEqual(BillModel._meta.swapped, CUSTOM_BILL_SETTING)
        self.assertIsInstance(po_model, self.CustomPurchaseOrderModel)
        self.assertIsInstance(bill_model, self.CustomBillModel)
        self.assertEqual(item_tx.po_model_id, po_model.uuid)
        self.assertIs(bill_qs.model, self.CustomBillModel)
        self.assertTrue(bill_qs.filter(uuid=bill_model.uuid).exists())
