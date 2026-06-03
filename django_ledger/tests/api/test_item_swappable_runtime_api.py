"""
Runtime-only tests for the ItemModel Swapper integration.

These tests require django_ledger.tests.settings_swappable_item so the custom
model is configured before Django's app registry is populated.
"""

import unittest
from uuid import uuid4

import swapper
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel
from django_ledger.models.utils import lazy_loader


CUSTOM_ITEM_SETTING = 'swappable_item_app.CustomItemModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_ITEMMODEL_MODEL', None) == CUSTOM_ITEM_SETTING,
    'requires django_ledger.tests.settings_swappable_item',
)
class ItemSwappableRuntimeAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomItemModel = apps.get_model('swappable_item_app', 'CustomItemModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_item_admin',
            email='api-swappable-item-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Item Entity'):
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
        expense_account = coa_model.create_account(
            code='6010',
            name=f'{name} Expense',
            role='ex_regular',
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        inventory_account = coa_model.create_account(
            code='1510',
            name=f'{name} Inventory',
            role='asset_ca_inv',
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        cogs_account = coa_model.create_account(
            code='5010',
            name=f'{name} COGS',
            role='cogs_regular',
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        earnings_account = coa_model.create_account(
            code='4010',
            name=f'{name} Earnings',
            role='in_operational',
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
        return {
            'entity_model': entity_model,
            'coa_model': coa_model,
            'expense_account': expense_account,
            'inventory_account': inventory_account,
            'cogs_account': cogs_account,
            'earnings_account': earnings_account,
            'uom_model': uom_model,
        }

    def create_expense_item(self, setup, *, name='API Swappable Expense Item'):
        return setup['entity_model'].create_item_expense(
            name=name,
            expense_type=self.CustomItemModel.ITEM_TYPE_OTHER,
            uom_model=setup['uom_model'],
            expense_account=setup['expense_account'],
            coa_model=setup['coa_model'],
            commit=True,
        )

    def test_runtime_loader_returns_custom_item_model(self):
        self.assertIs(lazy_loader.get_item_model(), self.CustomItemModel)
        self.assertIs(swapper.load_model('django_ledger', 'ItemModel'), self.CustomItemModel)
        self.assertEqual(swapper.get_model_name('django_ledger', 'ItemModel'), CUSTOM_ITEM_SETTING)

    def test_runtime_default_item_model_remains_importable_but_not_effective(self):
        self.assertEqual(ItemModel._meta.label, 'django_ledger.ItemModel')
        self.assertIsNot(ItemModel, self.CustomItemModel)
        self.assertIs(lazy_loader.get_item_model(), self.CustomItemModel)

    def test_runtime_entity_create_item_uses_custom_item_model(self):
        setup = self.create_accounting_setup()

        item_model = self.create_expense_item(setup)

        self.assertIsInstance(item_model, self.CustomItemModel)
        self.assertEqual(item_model.entity_id, setup['entity_model'].uuid)
        self.assertEqual(item_model.custom_marker, 'custom')
        self.assertTrue(item_model.item_number)
        self.assertTrue(self.CustomItemModel.objects.filter(uuid=item_model.uuid).exists())

    def test_runtime_entity_get_items_all_queries_custom_item_model(self):
        setup = self.create_accounting_setup(name='API Swappable Item Scoped Entity')
        other_setup = self.create_accounting_setup(name='API Other Swappable Item Scoped Entity')
        item_model = self.create_expense_item(setup, name='API Scoped Swappable Item')
        other_item_model = self.create_expense_item(other_setup, name='API Other Scoped Swappable Item')

        item_qs = setup['entity_model'].get_items_all()

        self.assertIs(item_qs.model, self.CustomItemModel)
        self.assertTrue(item_qs.filter(uuid=item_model.uuid).exists())
        self.assertFalse(item_qs.filter(uuid=other_item_model.uuid).exists())

    def test_runtime_item_forms_use_custom_item_model(self):
        from django_ledger.forms.item import (
            ExpenseItemCreateForm,
            InventoryItemCreateForm,
            ProductCreateForm,
            ServiceCreateForm,
        )

        setup = self.create_accounting_setup(name='API Swappable Item Form Entity')
        form = ExpenseItemCreateForm(entity_slug=setup['entity_model'].slug, user_model=self.admin_user)

        self.assertIs(ExpenseItemCreateForm._meta.model, self.CustomItemModel)
        self.assertIs(ProductCreateForm._meta.model, self.CustomItemModel)
        self.assertIs(ServiceCreateForm._meta.model, self.CustomItemModel)
        self.assertIs(InventoryItemCreateForm._meta.model, self.CustomItemModel)
        self.assertIs(form.instance.__class__, self.CustomItemModel)

    def test_runtime_document_item_querysets_use_custom_item_model(self):
        from django_ledger.models.bill import BillModel

        setup = self.create_accounting_setup(name='API Swappable Item Bill Query Entity')
        item_model = self.create_expense_item(setup)
        bill_model = BillModel()
        ledger_model = setup['entity_model'].create_ledger(
            name='API Swappable Item Query Ledger',
            commit=True,
        )
        bill_model.ledger = ledger_model

        item_qs = bill_model.get_item_model_qs()

        self.assertIs(item_qs.model, self.CustomItemModel)
        self.assertTrue(item_qs.filter(uuid=item_model.uuid).exists())
