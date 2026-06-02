"""
Integration smoke tests for combined BillModel and EstimateModel swapping.
"""

import unittest
from datetime import date
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, ASSET_CA_PREPAID, EXPENSE_OPERATIONAL, LIABILITY_CL_ACC_PAYABLE
from django_ledger.models.bill import BillModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.estimate import EstimateModel
from django_ledger.models.utils import lazy_loader


CUSTOM_BILL_SETTING = 'swappable_bill_app.CustomBillModel'
CUSTOM_ESTIMATE_SETTING = 'swappable_estimate_app.CustomEstimateModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_BILLMODEL_MODEL', None) == CUSTOM_BILL_SETTING
    and getattr(settings, 'DJANGO_LEDGER_ESTIMATEMODEL_MODEL', None) == CUSTOM_ESTIMATE_SETTING,
    'requires django_ledger.tests.settings_swappable_bill_estimate',
)
class BillEstimateSwappableIntegrationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomBillModel = apps.get_model('swappable_bill_app', 'CustomBillModel')
        cls.CustomEstimateModel = apps.get_model('swappable_estimate_app', 'CustomEstimateModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_bill_estimate_admin',
            email='api-swappable-bill-estimate-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self):
        suffix = str(uuid4())[:8]
        entity_model = EntityModel.create_entity(
            name=f'API Swappable Bill Estimate Entity {suffix}',
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f'{entity_model.name} CoA',
            commit=True,
            assign_as_default=True,
        )
        for code, role, balance_type in (
            ('1010', ASSET_CA_CASH, 'debit'),
            ('1310', ASSET_CA_PREPAID, 'debit'),
            ('2010', LIABILITY_CL_ACC_PAYABLE, 'credit'),
            ('6010', EXPENSE_OPERATIONAL, 'debit'),
        ):
            coa_model.create_account(
                code=code,
                name=f'{entity_model.name} {role}',
                role=role,
                balance_type=balance_type,
                active=True,
                is_role_default=True,
            )
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
        vendor_model = entity_model.create_vendor(
            {
                'vendor_name': f'{entity_model.name} Vendor',
                'description': f'{entity_model.name} vendor description',
                'active': True,
                'hidden': False,
            },
            commit=True,
        )
        estimate_model = entity_model.create_estimate(
            estimate_title='API Swappable Bill Estimate Contract',
            contract_terms=self.CustomEstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=customer_model,
            date_draft=date(2026, 1, 10),
            commit=True,
        )
        estimate_model.status = self.CustomEstimateModel.CONTRACT_STATUS_APPROVED
        estimate_model.date_approved = date(2026, 1, 12)
        estimate_model.save(update_fields=['status', 'date_approved', 'updated'])
        bill_model = entity_model.create_bill(
            vendor_model=vendor_model,
            terms=self.CustomBillModel.TERMS_NET_30,
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        bill_model.bind_estimate(estimate_model=estimate_model, commit=True)
        bill_model.refresh_from_db()
        return {
            'bill_model': bill_model,
            'estimate_model': estimate_model,
        }

    def test_combined_custom_bill_can_bind_custom_estimate(self):
        setup = self.create_accounting_setup()
        bill_model = setup['bill_model']
        estimate_model = setup['estimate_model']

        self.assertIs(lazy_loader.get_bill_model(), self.CustomBillModel)
        self.assertIs(lazy_loader.get_estimate_model(), self.CustomEstimateModel)
        self.assertEqual(BillModel._meta.swapped, CUSTOM_BILL_SETTING)
        self.assertEqual(EstimateModel._meta.swapped, CUSTOM_ESTIMATE_SETTING)
        self.assertIs(self.CustomBillModel._meta.get_field('ce_model').remote_field.model, self.CustomEstimateModel)
        self.assertIsInstance(bill_model, self.CustomBillModel)
        self.assertIsInstance(estimate_model, self.CustomEstimateModel)
        self.assertIsInstance(bill_model.ce_model, self.CustomEstimateModel)
        self.assertEqual(bill_model.ce_model_id, estimate_model.uuid)
