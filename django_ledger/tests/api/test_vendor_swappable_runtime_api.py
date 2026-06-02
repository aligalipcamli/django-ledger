"""
Runtime-only tests for the VendorModel Swapper integration.

These tests require django_ledger.tests.settings_swappable_vendor so the
custom model is configured before Django's app registry is populated.
"""

import unittest

import swapper
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, DEBIT, EXPENSE_OPERATIONAL
from django_ledger.models import BankAccountModel
from django_ledger.models.data_import import ImportJobModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.utils import lazy_loader
from django_ledger.models.vendor import VendorModel


CUSTOM_VENDOR_SETTING = 'swappable_vendor_app.CustomVendorModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_VENDORMODEL_MODEL', None) == CUSTOM_VENDOR_SETTING,
    'requires django_ledger.tests.settings_swappable_vendor',
)
class VendorSwappableRuntimeAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomVendorModel = apps.get_model('swappable_vendor_app', 'CustomVendorModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_vendor_admin',
            email='api-swappable-vendor-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_entity(self, name='API Swappable Vendor Entity'):
        return EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_vendor(self, entity_model, *, name='API Swappable Vendor', active=True):
        return entity_model.create_vendor(
            {
                'vendor_name': name,
                'description': f'{name} description',
                'active': active,
                'hidden': False,
            }
        )

    def create_accounting_setup(self, name='API Swappable Vendor Forms Entity'):
        entity_model = self.create_entity(name=name)
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f'{name} CoA',
            commit=True,
            assign_as_default=True,
        )
        cash_account = coa_model.create_account(
            code='1010',
            name=f'{name} Cash',
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        expense_account = coa_model.create_account(
            code='6010',
            name=f'{name} Expense',
            role=EXPENSE_OPERATIONAL,
            balance_type=DEBIT,
            active=True,
        )
        bank_account = BankAccountModel(
            name=f'{name} Bank',
            account_model=cash_account,
            account_number='000123456789',
            routing_number='000111000',
            active=True,
        )
        bank_account.configure(entity_slug=entity_model, user_model=self.admin_user, commit=True)
        import_job_model = ImportJobModel.objects.create(
            description=f'{name} Import Job',
            bank_account_model=bank_account,
        )
        import_job_model.configure(commit=True)
        import_job_model.refresh_from_db()
        return {
            'entity_model': entity_model,
            'cash_account': cash_account,
            'expense_account': expense_account,
            'import_job_model': import_job_model,
        }

    def test_runtime_loader_returns_custom_vendor_model(self):
        self.assertIs(lazy_loader.get_vendor_model(), self.CustomVendorModel)
        self.assertIs(swapper.load_model('django_ledger', 'VendorModel'), self.CustomVendorModel)
        self.assertEqual(swapper.get_model_name('django_ledger', 'VendorModel'), CUSTOM_VENDOR_SETTING)

    def test_runtime_default_vendor_model_remains_importable_but_not_effective(self):
        self.assertEqual(VendorModel._meta.label, 'django_ledger.VendorModel')
        self.assertIsNot(VendorModel, self.CustomVendorModel)
        self.assertIs(lazy_loader.get_vendor_model(), self.CustomVendorModel)

    def test_runtime_entity_create_vendor_uses_custom_vendor_model(self):
        entity_model = self.create_entity()

        vendor_model = self.create_vendor(entity_model)

        self.assertIsInstance(vendor_model, self.CustomVendorModel)
        self.assertEqual(vendor_model.entity_model_id, entity_model.uuid)
        self.assertEqual(vendor_model.custom_marker, 'custom')
        self.assertTrue(vendor_model.vendor_number)

    def test_runtime_entity_get_vendors_queries_custom_vendor_model(self):
        entity_model = self.create_entity(name='API Swappable Vendor Scoped Entity')
        other_entity_model = self.create_entity(name='API Other Swappable Vendor Scoped Entity')
        active_vendor = self.create_vendor(entity_model, name='API Active Swappable Vendor')
        inactive_vendor = self.create_vendor(
            entity_model,
            name='API Inactive Swappable Vendor',
            active=False,
        )
        other_vendor = self.create_vendor(other_entity_model, name='API Other Swappable Vendor')

        default_vendor_qs = entity_model.get_vendors()
        all_vendor_qs = entity_model.get_vendors(active=False)

        self.assertIs(default_vendor_qs.model, self.CustomVendorModel)
        self.assertIs(all_vendor_qs.model, self.CustomVendorModel)
        self.assertTrue(default_vendor_qs.filter(uuid=active_vendor.uuid).exists())
        self.assertFalse(default_vendor_qs.filter(uuid=inactive_vendor.uuid).exists())
        self.assertFalse(default_vendor_qs.filter(uuid=other_vendor.uuid).exists())
        self.assertTrue(all_vendor_qs.filter(uuid=active_vendor.uuid).exists())
        self.assertTrue(all_vendor_qs.filter(uuid=inactive_vendor.uuid).exists())
        self.assertFalse(all_vendor_qs.filter(uuid=other_vendor.uuid).exists())

    def test_runtime_vendor_form_resolves_custom_vendor_model(self):
        from django_ledger.forms.vendor import VendorModelForm

        self.assertIs(VendorModelForm._meta.model, self.CustomVendorModel)

    def test_runtime_bill_form_uses_custom_vendor_queryset(self):
        from django_ledger.forms.bill import BillModelCreateForm

        setup = self.create_accounting_setup()
        vendor_model = self.create_vendor(setup['entity_model'])

        form = BillModelCreateForm(entity_model=setup['entity_model'])

        self.assertIs(form.fields['vendor'].queryset.model, self.CustomVendorModel)
        self.assertTrue(form.fields['vendor'].queryset.filter(uuid=vendor_model.uuid).exists())

    def test_runtime_staged_transaction_formset_uses_custom_vendor_queryset(self):
        from django_ledger.forms.data_import import StagedTransactionModelFormSet

        setup = self.create_accounting_setup(name='API Swappable Vendor Formset Entity')
        vendor_model = self.create_vendor(setup['entity_model'])

        formset = StagedTransactionModelFormSet(
            entity_model=setup['entity_model'],
            import_job_model=setup['import_job_model'],
        )

        self.assertIs(formset.VENDOR_MODEL_QS.model, self.CustomVendorModel)
        self.assertTrue(formset.VENDOR_MODEL_QS.filter(uuid=vendor_model.uuid).exists())
