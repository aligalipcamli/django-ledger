"""
Runtime-only tests for the UnitOfMeasureModel Swapper integration.

These tests require django_ledger.tests.settings_swappable_uom so the custom
model is configured before Django's app registry is populated.
"""

import unittest
from uuid import uuid4

import swapper
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import DEBIT, EXPENSE_OPERATIONAL
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import UnitOfMeasureModel
from django_ledger.models.utils import lazy_loader


CUSTOM_UOM_SETTING = 'swappable_uom_app.CustomUnitOfMeasureModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_UNITOFMEASUREMODEL_MODEL', None) == CUSTOM_UOM_SETTING,
    'requires django_ledger.tests.settings_swappable_uom',
)
class UOMSwappableRuntimeAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomUnitOfMeasureModel = apps.get_model('swappable_uom_app', 'CustomUnitOfMeasureModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_uom_admin',
            email='api-swappable-uom-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable UOM Entity'):
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
            role=EXPENSE_OPERATIONAL,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        return {
            'entity_model': entity_model,
            'coa_model': coa_model,
            'expense_account': expense_account,
        }

    def create_uom(self, entity_model, *, name='API Swappable UOM', active=True):
        return entity_model.create_uom(
            name=name,
            unit_abbr=f'u{str(uuid4())[:7]}',
            active=active,
            commit=True,
        )

    def test_runtime_loader_returns_custom_uom_model(self):
        self.assertIs(lazy_loader.get_uom_model(), self.CustomUnitOfMeasureModel)
        self.assertIs(swapper.load_model('django_ledger', 'UnitOfMeasureModel'), self.CustomUnitOfMeasureModel)
        self.assertEqual(swapper.get_model_name('django_ledger', 'UnitOfMeasureModel'), CUSTOM_UOM_SETTING)

    def test_runtime_default_uom_model_remains_importable_but_not_effective(self):
        self.assertEqual(UnitOfMeasureModel._meta.label, 'django_ledger.UnitOfMeasureModel')
        self.assertIsNot(UnitOfMeasureModel, self.CustomUnitOfMeasureModel)
        self.assertIs(lazy_loader.get_uom_model(), self.CustomUnitOfMeasureModel)

    def test_runtime_entity_create_uom_uses_custom_uom_model(self):
        setup = self.create_accounting_setup()

        uom_model = self.create_uom(setup['entity_model'])

        self.assertIsInstance(uom_model, self.CustomUnitOfMeasureModel)
        self.assertEqual(uom_model.entity_id, setup['entity_model'].uuid)
        self.assertEqual(uom_model.custom_marker, 'custom')
        self.assertTrue(self.CustomUnitOfMeasureModel.objects.filter(uuid=uom_model.uuid).exists())

    def test_runtime_entity_get_uom_all_queries_custom_uom_model(self):
        setup = self.create_accounting_setup(name='API Swappable UOM Scoped Entity')
        other_setup = self.create_accounting_setup(name='API Other Swappable UOM Scoped Entity')
        active_uom = self.create_uom(setup['entity_model'], name='API Active Swappable UOM')
        inactive_uom = self.create_uom(setup['entity_model'], name='API Inactive Swappable UOM', active=False)
        other_uom = self.create_uom(other_setup['entity_model'], name='API Other Swappable UOM')

        uom_qs = setup['entity_model'].get_uom_all()

        self.assertIs(uom_qs.model, self.CustomUnitOfMeasureModel)
        self.assertTrue(uom_qs.filter(uuid=active_uom.uuid).exists())
        self.assertTrue(uom_qs.filter(uuid=inactive_uom.uuid).exists())
        self.assertFalse(uom_qs.filter(uuid=other_uom.uuid).exists())

    def test_runtime_item_forms_use_custom_uom_model(self):
        from django_ledger.forms.item import ExpenseItemCreateForm, UnitOfMeasureModelCreateForm

        setup = self.create_accounting_setup(name='API Swappable UOM Form Entity')
        uom_model = self.create_uom(setup['entity_model'])

        form = ExpenseItemCreateForm(entity_slug=setup['entity_model'].slug, user_model=self.admin_user)

        self.assertIs(UnitOfMeasureModelCreateForm._meta.model, self.CustomUnitOfMeasureModel)
        self.assertIs(form.fields['uom'].queryset.model, self.CustomUnitOfMeasureModel)
        self.assertTrue(form.fields['uom'].queryset.filter(uuid=uom_model.uuid).exists())
