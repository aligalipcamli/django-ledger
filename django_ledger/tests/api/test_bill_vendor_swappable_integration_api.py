"""
Integration smoke tests for combined BillModel and VendorModel swapping.
"""

import unittest
from datetime import date
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, ASSET_CA_PREPAID, EXPENSE_OPERATIONAL, LIABILITY_CL_ACC_PAYABLE
from django_ledger.models.entity import EntityModel
from django_ledger.models.utils import lazy_loader


CUSTOM_BILL_SETTING = 'swappable_bill_app.CustomBillModel'
CUSTOM_VENDOR_SETTING = 'swappable_vendor_app.CustomVendorModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_BILLMODEL_MODEL', None) == CUSTOM_BILL_SETTING
    and getattr(settings, 'DJANGO_LEDGER_VENDORMODEL_MODEL', None) == CUSTOM_VENDOR_SETTING,
    'requires django_ledger.tests.settings_swappable_bill_vendor',
)
class BillVendorSwappableIntegrationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomBillModel = apps.get_model('swappable_bill_app', 'CustomBillModel')
        cls.CustomVendorModel = apps.get_model('swappable_vendor_app', 'CustomVendorModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_bill_vendor_admin',
            email='api-swappable-bill-vendor-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_entity_with_accounts(self):
        suffix = str(uuid4())[:8]
        entity_model = EntityModel.create_entity(
            name=f'API Swappable Bill Vendor Entity {suffix}',
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
        return entity_model

    def test_combined_custom_bill_uses_custom_vendor(self):
        entity_model = self.create_entity_with_accounts()
        vendor_model = entity_model.create_vendor(
            {
                'vendor_name': f'{entity_model.name} Vendor',
                'description': f'{entity_model.name} vendor description',
                'active': True,
                'hidden': False,
            },
            commit=True,
        )

        bill_model = entity_model.create_bill(
            vendor_model=vendor_model,
            terms=self.CustomBillModel.TERMS_NET_30,
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        bill_model.refresh_from_db()

        self.assertIs(lazy_loader.get_bill_model(), self.CustomBillModel)
        self.assertIs(lazy_loader.get_vendor_model(), self.CustomVendorModel)
        self.assertIs(self.CustomBillModel._meta.get_field('vendor').remote_field.model, self.CustomVendorModel)
        self.assertIsInstance(vendor_model, self.CustomVendorModel)
        self.assertIsInstance(bill_model, self.CustomBillModel)
        self.assertIsInstance(bill_model.vendor, self.CustomVendorModel)
        self.assertEqual(bill_model.vendor.custom_marker, 'custom')
