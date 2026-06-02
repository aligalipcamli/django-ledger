"""
Schema-level tests for the UnitOfMeasureModel Strategy A FK proof.

These tests require django_ledger.tests.settings_swappable_uom so the custom
unit of measure model is configured before migrations and app loading.
"""

import unittest
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.checks import run_checks
from django.test import TestCase

from django_ledger.io import DEBIT, EXPENSE_OPERATIONAL
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel
from django_ledger.models.utils import lazy_loader


CUSTOM_UOM_SETTING = 'swappable_uom_app.CustomUnitOfMeasureModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_UNITOFMEASUREMODEL_MODEL', None) == CUSTOM_UOM_SETTING,
    'requires django_ledger.tests.settings_swappable_uom',
)
class UOMSwappableSchemaAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomUnitOfMeasureModel = apps.get_model('swappable_uom_app', 'CustomUnitOfMeasureModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_uom_schema_admin',
            email='api-swappable-uom-schema-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_setup(self):
        suffix = str(uuid4())[:8]
        name = f'API Swappable UOM Schema Entity {suffix}'
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
            role=EXPENSE_OPERATIONAL,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        uom_model = entity_model.create_uom(
            name=f'{name} Unit',
            unit_abbr=f'u{suffix[:7]}',
            active=True,
            commit=True,
        )
        return {
            'entity_model': entity_model,
            'expense_account': expense_account,
            'uom_model': uom_model,
        }

    def test_schema_item_uom_fk_resolves_to_custom_uom_model(self):
        field = ItemModel._meta.get_field('uom')

        self.assertIs(field.remote_field.model, self.CustomUnitOfMeasureModel)

    def test_schema_system_checks_do_not_report_swapped_uom_fk_errors(self):
        errors = [error for error in run_checks() if error.id == 'fields.E301']

        self.assertEqual(errors, [])

    def test_schema_item_model_accepts_custom_uom_assignment(self):
        setup = self.create_setup()
        uom_model = setup['uom_model']

        item_model = ItemModel(
            entity=setup['entity_model'],
            name='API Swappable UOM Schema Expense',
            uom=uom_model,
            item_role=ItemModel.ITEM_ROLE_EXPENSE,
            item_type=ItemModel.ITEM_TYPE_OTHER,
            expense_account=setup['expense_account'],
        )

        self.assertIsInstance(uom_model, self.CustomUnitOfMeasureModel)
        self.assertIs(lazy_loader.get_uom_model(), self.CustomUnitOfMeasureModel)
        self.assertIs(item_model.uom, uom_model)

    def test_schema_item_model_persists_custom_uom_rows(self):
        setup = self.create_setup()
        uom_model = setup['uom_model']

        item_model = setup['entity_model'].create_item_expense(
            name='API Swappable UOM Persisted Expense',
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=setup['expense_account'],
            commit=True,
        )

        self.assertEqual(item_model.uom_id, uom_model.uuid)
        self.assertTrue(ItemModel.objects.filter(uom=uom_model).exists())
