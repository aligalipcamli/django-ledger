"""
Runtime tests for the EstimateModel Swapper proof.

These tests require django_ledger.tests.settings_swappable_estimate so the custom
estimate model is configured before migrations and app loading.
"""

import unittest
from datetime import date
from uuid import uuid4

import swapper
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.forms.estimate import BaseEstimateModelUpdateForm, EstimateModelCreateForm
from django_ledger.io import COGS, INCOME_OPERATIONAL
from django_ledger.models.entity import EntityModel
from django_ledger.models.estimate import EstimateModel
from django_ledger.models.utils import lazy_loader
from django_ledger.views.estimate import EstimateModelListView


CUSTOM_ESTIMATE_SETTING = 'swappable_estimate_app.CustomEstimateModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_ESTIMATEMODEL_MODEL', None) == CUSTOM_ESTIMATE_SETTING,
    'requires django_ledger.tests.settings_swappable_estimate',
)
class EstimateSwappableRuntimeAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomEstimateModel = apps.get_model('swappable_estimate_app', 'CustomEstimateModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_estimate_runtime_admin',
            email='api-swappable-estimate-runtime-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Estimate Runtime Entity'):
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
            code='4010',
            name=f'{name} Income',
            role=INCOME_OPERATIONAL,
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
        return {
            'entity_model': entity_model,
            'customer_model': customer_model,
            'service_item': service_item,
        }

    def create_estimate(self, setup):
        estimate_model = setup['entity_model'].create_estimate(
            estimate_title='API Swappable Estimate Runtime Contract',
            contract_terms=self.CustomEstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=setup['customer_model'],
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        estimate_model.refresh_from_db()
        return estimate_model

    def test_runtime_loader_returns_custom_estimate_model(self):
        self.assertIs(lazy_loader.get_estimate_model(), self.CustomEstimateModel)
        self.assertIs(swapper.load_model('django_ledger', 'EstimateModel'), self.CustomEstimateModel)

    def test_runtime_default_estimate_model_remains_importable_but_not_effective(self):
        self.assertEqual(EstimateModel._meta.label, 'django_ledger.EstimateModel')
        self.assertEqual(EstimateModel._meta.swapped, CUSTOM_ESTIMATE_SETTING)
        self.assertIsNot(lazy_loader.get_estimate_model(), EstimateModel)

    def test_runtime_entity_create_and_get_estimates_use_custom_estimate_model(self):
        setup = self.create_accounting_setup()
        estimate_model = self.create_estimate(setup)

        estimate_qs = setup['entity_model'].get_estimates()

        self.assertIsInstance(estimate_model, self.CustomEstimateModel)
        self.assertEqual(estimate_model.custom_marker, 'custom')
        self.assertTrue(estimate_model.estimate_number)
        self.assertTrue(self.CustomEstimateModel.objects.filter(uuid=estimate_model.uuid).exists())
        self.assertEqual(estimate_qs.model, self.CustomEstimateModel)
        self.assertTrue(estimate_qs.filter(uuid=estimate_model.uuid).exists())

    def test_runtime_estimate_forms_use_custom_estimate_model(self):
        self.assertIs(EstimateModelCreateForm._meta.model, self.CustomEstimateModel)
        self.assertIs(BaseEstimateModelUpdateForm._meta.model, self.CustomEstimateModel)

    def test_runtime_estimate_list_view_queryset_uses_custom_estimate_model(self):
        setup = self.create_accounting_setup(name='API Swappable Estimate Runtime View Entity')
        estimate_model = self.create_estimate(setup)
        view = EstimateModelListView()
        view.AUTHORIZED_ENTITY_MODEL = setup['entity_model']
        view.kwargs = {'entity_slug': setup['entity_model'].slug}

        estimate_qs = view.get_queryset()

        self.assertEqual(estimate_qs.model, self.CustomEstimateModel)
        self.assertTrue(estimate_qs.filter(uuid=estimate_model.uuid).exists())
