"""
Runtime tests for PurchaseOrderModel Swapper integration.

These tests require django_ledger.tests.settings_swappable_purchase_order so
the custom model is configured before Django's app registry is populated.
"""

import unittest
from datetime import date
from uuid import uuid4

import swapper
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_INVENTORY, COGS, EXPENSE_OPERATIONAL, INCOME_OPERATIONAL
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel
from django_ledger.models.purchase_order import PurchaseOrderModel
from django_ledger.models.utils import lazy_loader


CUSTOM_PURCHASE_ORDER_SETTING = 'swappable_purchase_order_app.CustomPurchaseOrderModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_PURCHASEORDERMODEL_MODEL', None) == CUSTOM_PURCHASE_ORDER_SETTING,
    'requires django_ledger.tests.settings_swappable_purchase_order',
)
class PurchaseOrderSwappableRuntimeAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomPurchaseOrderModel = apps.get_model(
            'swappable_purchase_order_app',
            'CustomPurchaseOrderModel',
        )
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_po_admin',
            email='api-swappable-po-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Purchase Order Entity'):
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
        coa_model.create_account(
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
        return {
            'entity_model': entity_model,
            'inventory_item': inventory_item,
        }

    def create_purchase_order(self, setup, title='API Swappable Purchase Order'):
        po_model = setup['entity_model'].create_purchase_order(
            po_title=title,
            date_draft=date(2026, 4, 15),
            commit=True,
        )
        po_model.refresh_from_db()
        return po_model

    def test_runtime_loader_returns_custom_purchase_order_model(self):
        self.assertIs(lazy_loader.get_purchase_order_model(), self.CustomPurchaseOrderModel)
        self.assertIs(
            swapper.load_model('django_ledger', 'PurchaseOrderModel'),
            self.CustomPurchaseOrderModel,
        )
        self.assertEqual(
            swapper.get_model_name('django_ledger', 'PurchaseOrderModel'),
            CUSTOM_PURCHASE_ORDER_SETTING,
        )

    def test_runtime_default_purchase_order_model_remains_importable_but_not_effective(self):
        self.assertEqual(PurchaseOrderModel._meta.label, 'django_ledger.PurchaseOrderModel')
        self.assertIsNot(PurchaseOrderModel, self.CustomPurchaseOrderModel)
        self.assertEqual(PurchaseOrderModel._meta.swapped, CUSTOM_PURCHASE_ORDER_SETTING)
        self.assertIs(lazy_loader.get_purchase_order_model(), self.CustomPurchaseOrderModel)

    def test_runtime_entity_create_purchase_order_uses_custom_model(self):
        setup = self.create_accounting_setup()

        po_model = self.create_purchase_order(setup)

        self.assertIsInstance(po_model, self.CustomPurchaseOrderModel)
        self.assertEqual(po_model.entity_id, setup['entity_model'].uuid)
        self.assertTrue(po_model.po_number)
        self.assertEqual(po_model.custom_marker, 'custom')
        self.assertTrue(self.CustomPurchaseOrderModel.objects.filter(uuid=po_model.uuid).exists())

    def test_runtime_entity_get_purchase_orders_queries_custom_model(self):
        setup = self.create_accounting_setup(name='API Swappable Purchase Order Scoped Entity')
        other_setup = self.create_accounting_setup(name='API Other Swappable Purchase Order Scoped Entity')
        po_model = self.create_purchase_order(setup)
        other_po_model = self.create_purchase_order(other_setup, title='API Other Swappable Purchase Order')

        po_qs = setup['entity_model'].get_purchase_orders()

        self.assertIs(po_qs.model, self.CustomPurchaseOrderModel)
        self.assertTrue(po_qs.filter(uuid=po_model.uuid).exists())
        self.assertFalse(po_qs.filter(uuid=other_po_model.uuid).exists())

    def test_runtime_purchase_order_forms_use_custom_model(self):
        from django_ledger.forms.purchase_order import (
            BasePurchaseOrderModelUpdateForm,
            PurchaseOrderModelCreateForm,
        )

        form = PurchaseOrderModelCreateForm(
            entity_slug='api-swappable-purchase-order-form-entity',
            user_model=self.admin_user,
        )

        self.assertIs(PurchaseOrderModelCreateForm._meta.model, self.CustomPurchaseOrderModel)
        self.assertIs(BasePurchaseOrderModelUpdateForm._meta.model, self.CustomPurchaseOrderModel)
        self.assertIs(form.instance.__class__, self.CustomPurchaseOrderModel)

    def test_runtime_purchase_order_list_view_queryset_uses_custom_model(self):
        from django_ledger.views.purchase_order import PurchaseOrderModelListView

        setup = self.create_accounting_setup(name='API Swappable Purchase Order View Entity')
        po_model = self.create_purchase_order(setup)
        view = PurchaseOrderModelListView()
        view.AUTHORIZED_ENTITY_MODEL = setup['entity_model']
        view.kwargs = {'entity_slug': setup['entity_model'].slug}

        po_qs = view.get_queryset()

        self.assertIs(po_qs.model, self.CustomPurchaseOrderModel)
        self.assertTrue(po_qs.filter(uuid=po_model.uuid).exists())
