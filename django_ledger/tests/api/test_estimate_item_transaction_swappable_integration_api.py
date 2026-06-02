"""
Integration smoke tests for combined EstimateModel and ItemTransactionModel swapping.
"""

import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import COGS, INCOME_OPERATIONAL
from django_ledger.models.entity import EntityModel
from django_ledger.models.estimate import EstimateModel
from django_ledger.models.items import ItemTransactionModel
from django_ledger.models.utils import lazy_loader


CUSTOM_ESTIMATE_SETTING = 'swappable_estimate_app.CustomEstimateModel'
CUSTOM_ITEM_TRANSACTION_SETTING = 'swappable_item_transaction_app.CustomItemTransactionModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_ESTIMATEMODEL_MODEL', None) == CUSTOM_ESTIMATE_SETTING
    and getattr(settings, 'DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL', None) == CUSTOM_ITEM_TRANSACTION_SETTING,
    'requires django_ledger.tests.settings_swappable_estimate_item_transaction',
)
class EstimateItemTransactionSwappableIntegrationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomEstimateModel = apps.get_model('swappable_estimate_app', 'CustomEstimateModel')
        cls.CustomItemTransactionModel = apps.get_model(
            'swappable_item_transaction_app',
            'CustomItemTransactionModel',
        )
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_estimate_itemtx_admin',
            email='api-swappable-estimate-itemtx-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Estimate Item Transaction Entity'):
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
        customer_model = self.create_customer(entity_model)
        estimate_model = entity_model.create_estimate(
            estimate_title='API Swappable Estimate Item Transaction Contract',
            contract_terms=self.CustomEstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=customer_model,
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        return {
            'estimate_model': estimate_model,
            'service_item': service_item,
        }

    def create_customer(self, entity_model):
        CustomerModel = lazy_loader.get_customer_model()
        customer_model = CustomerModel(
            customer_name=f'{entity_model.name} Customer',
            entity_model=entity_model,
            description=f'{entity_model.name} Customer description',
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()
        return customer_model

    def test_combined_estimate_item_transaction_field_targets_resolve_to_custom_models(self):
        self.assertIs(lazy_loader.get_estimate_model(), self.CustomEstimateModel)
        self.assertIs(lazy_loader.get_item_transaction_model(), self.CustomItemTransactionModel)
        self.assertEqual(EstimateModel._meta.swapped, CUSTOM_ESTIMATE_SETTING)
        self.assertEqual(ItemTransactionModel._meta.swapped, CUSTOM_ITEM_TRANSACTION_SETTING)
        self.assertIs(
            self.CustomItemTransactionModel._meta.get_field('ce_model').remote_field.model,
            self.CustomEstimateModel,
        )

    def test_combined_custom_estimate_itemization_uses_custom_item_transaction(self):
        setup = self.create_accounting_setup()
        estimate_model = setup['estimate_model']
        service_item = setup['service_item']
        itemtxs = {
            service_item.item_number: {
                'quantity': Decimal('2.00'),
                'unit_cost': Decimal('50.00'),
                'unit_revenue': Decimal('75.00'),
                'total_amount': Decimal('150.00'),
            }
        }

        itemtxs_batch = estimate_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=self.CustomEstimateModel.ITEMIZE_REPLACE,
            commit=True,
        )
        estimate_model.refresh_from_db()
        item_tx = self.CustomItemTransactionModel.objects.select_related('ce_model', 'item_model').get(
            ce_model=estimate_model,
        )

        self.assertEqual(len(itemtxs_batch), 1)
        self.assertIsInstance(estimate_model, self.CustomEstimateModel)
        self.assertIsInstance(item_tx, self.CustomItemTransactionModel)
        self.assertEqual(item_tx.ce_model_id, estimate_model.uuid)
        self.assertEqual(item_tx.custom_marker, 'custom')
        self.assertEqual(estimate_model.revenue_estimate, Decimal('150.00'))
