"""
Runtime tests for BillModel Swapper integration.

These tests require django_ledger.tests.settings_swappable_bill so the custom
model is configured before Django's app registry is populated.
"""

import unittest
from datetime import date
from uuid import uuid4

import swapper
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import (
    ASSET_CA_CASH,
    ASSET_CA_PREPAID,
    EXPENSE_OPERATIONAL,
    LIABILITY_CL_ACC_PAYABLE,
)
from django_ledger.models.bill import BillModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemModel
from django_ledger.models.utils import lazy_loader


CUSTOM_BILL_SETTING = 'swappable_bill_app.CustomBillModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_BILLMODEL_MODEL', None) == CUSTOM_BILL_SETTING,
    'requires django_ledger.tests.settings_swappable_bill',
)
class BillSwappableRuntimeAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomBillModel = apps.get_model('swappable_bill_app', 'CustomBillModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_bill_admin',
            email='api-swappable-bill-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Bill Entity'):
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
            code='1010',
            name=f'{name} Cash',
            role=ASSET_CA_CASH,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='1310',
            name=f'{name} Prepaid',
            role=ASSET_CA_PREPAID,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='2010',
            name=f'{name} Payable',
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type='credit',
            active=True,
            is_role_default=True,
        )
        expense_account = coa_model.create_account(
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
        expense_item = entity_model.create_item_expense(
            name=f'{name} Expense Item',
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            coa_model=coa_model,
            commit=True,
        )
        vendor_model = entity_model.create_vendor(
            {
                'vendor_name': f'{name} Vendor',
                'description': f'{name} vendor description',
                'active': True,
                'hidden': False,
            },
            commit=True,
        )
        return {
            'entity_model': entity_model,
            'vendor_model': vendor_model,
            'expense_item': expense_item,
        }

    def create_bill(self, setup):
        bill_model = setup['entity_model'].create_bill(
            vendor_model=setup['vendor_model'],
            terms=self.CustomBillModel.TERMS_NET_30,
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        bill_model.refresh_from_db()
        return bill_model

    def test_runtime_loader_returns_custom_bill_model(self):
        self.assertIs(lazy_loader.get_bill_model(), self.CustomBillModel)
        self.assertIs(swapper.load_model('django_ledger', 'BillModel'), self.CustomBillModel)
        self.assertEqual(swapper.get_model_name('django_ledger', 'BillModel'), CUSTOM_BILL_SETTING)

    def test_runtime_default_bill_model_remains_importable_but_not_effective(self):
        self.assertEqual(BillModel._meta.label, 'django_ledger.BillModel')
        self.assertIsNot(BillModel, self.CustomBillModel)
        self.assertIs(lazy_loader.get_bill_model(), self.CustomBillModel)

    def test_runtime_entity_create_bill_uses_custom_bill_model(self):
        setup = self.create_accounting_setup()

        bill_model = self.create_bill(setup)

        self.assertIsInstance(bill_model, self.CustomBillModel)
        self.assertEqual(bill_model.entity_model_id, setup['entity_model'].uuid)
        self.assertTrue(bill_model.bill_number)
        self.assertEqual(bill_model.custom_marker, 'custom')
        self.assertTrue(self.CustomBillModel.objects.filter(uuid=bill_model.uuid).exists())
        self.assertEqual(BillModel._meta.swapped, CUSTOM_BILL_SETTING)

    def test_runtime_entity_get_bills_queries_custom_bill_model(self):
        setup = self.create_accounting_setup(name='API Swappable Bill Scoped Entity')
        other_setup = self.create_accounting_setup(name='API Other Swappable Bill Scoped Entity')
        bill_model = self.create_bill(setup)
        other_bill_model = self.create_bill(other_setup)

        bill_qs = setup['entity_model'].get_bills()

        self.assertIs(bill_qs.model, self.CustomBillModel)
        self.assertTrue(bill_qs.filter(uuid=bill_model.uuid).exists())
        self.assertFalse(bill_qs.filter(uuid=other_bill_model.uuid).exists())

    def test_runtime_bill_forms_use_custom_bill_model(self):
        from django_ledger.forms.bill import BaseBillModelUpdateForm, BillModelCreateForm

        setup = self.create_accounting_setup(name='API Swappable Bill Form Entity')
        form = BillModelCreateForm(entity_model=setup['entity_model'])

        self.assertIs(BillModelCreateForm._meta.model, self.CustomBillModel)
        self.assertIs(BaseBillModelUpdateForm._meta.model, self.CustomBillModel)
        self.assertIs(form.instance.__class__, self.CustomBillModel)

    def test_runtime_bill_list_view_queryset_uses_custom_bill_model(self):
        from django_ledger.views.bill import BillModelListView

        setup = self.create_accounting_setup(name='API Swappable Bill View Entity')
        bill_model = self.create_bill(setup)
        view = BillModelListView()
        view.AUTHORIZED_ENTITY_MODEL = setup['entity_model']
        view.kwargs = {'entity_slug': setup['entity_model'].slug}

        bill_qs = view.get_queryset()

        self.assertIs(bill_qs.model, self.CustomBillModel)
        self.assertTrue(bill_qs.filter(uuid=bill_model.uuid).exists())
