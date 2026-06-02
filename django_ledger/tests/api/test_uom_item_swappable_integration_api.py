"""
Integration smoke tests for combined UnitOfMeasureModel and ItemModel swapping.

These tests require django_ledger.tests.settings_swappable_uom_item so both
custom models are configured before Django's app registry is populated.
"""

import unittest
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemTransactionModel
from django_ledger.models.utils import lazy_loader


CUSTOM_UOM_SETTING = 'swappable_uom_app.CustomUnitOfMeasureModel'
CUSTOM_ITEM_SETTING = 'swappable_item_app.CustomItemModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_UNITOFMEASUREMODEL_MODEL', None) == CUSTOM_UOM_SETTING
    and getattr(settings, 'DJANGO_LEDGER_ITEMMODEL_MODEL', None) == CUSTOM_ITEM_SETTING,
    'requires django_ledger.tests.settings_swappable_uom_item',
)
class UOMItemSwappableIntegrationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomUnitOfMeasureModel = apps.get_model('swappable_uom_app', 'CustomUnitOfMeasureModel')
        cls.CustomItemModel = apps.get_model('swappable_item_app', 'CustomItemModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_uom_item_admin',
            email='api-swappable-uom-item-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable UOM Item Entity'):
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
        uom_model = entity_model.create_uom(
            name=f'Unit {suffix}',
            unit_abbr=f'u{suffix[:7]}',
            active=True,
            commit=True,
        )
        item_model = entity_model.create_item_expense(
            name=f'{name} Expense Item',
            expense_type=self.CustomItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            coa_model=coa_model,
            commit=True,
        )
        return {
            'entity_model': entity_model,
            'uom_model': uom_model,
            'item_model': item_model,
        }

    def test_combined_loaders_and_field_targets_resolve_to_custom_models(self):
        UnitOfMeasureModel = lazy_loader.get_uom_model()
        ItemModel = lazy_loader.get_item_model()

        self.assertIs(UnitOfMeasureModel, self.CustomUnitOfMeasureModel)
        self.assertIs(ItemModel, self.CustomItemModel)
        self.assertIs(ItemModel._meta.get_field('uom').remote_field.model, self.CustomUnitOfMeasureModel)
        self.assertIs(
            ItemTransactionModel._meta.get_field('item_model').remote_field.model,
            self.CustomItemModel,
        )

    def test_combined_custom_uom_item_and_fixed_item_transaction_persist(self):
        setup = self.create_accounting_setup()
        uom_model = setup['uom_model']
        item_model = setup['item_model']

        self.assertIsInstance(uom_model, self.CustomUnitOfMeasureModel)
        self.assertIsInstance(item_model, self.CustomItemModel)
        self.assertEqual(item_model.uom_id, uom_model.uuid)

        item_tx = ItemTransactionModel.objects.create(item_model=item_model)
        item_tx = ItemTransactionModel.objects.select_related('item_model', 'item_model__uom').get(
            uuid=item_tx.uuid,
        )

        self.assertEqual(item_tx.item_model_id, item_model.uuid)
        self.assertIsInstance(item_tx.item_model, self.CustomItemModel)
        self.assertEqual(item_tx.item_model.uom_id, uom_model.uuid)
        self.assertIsInstance(item_tx.item_model.uom, self.CustomUnitOfMeasureModel)
