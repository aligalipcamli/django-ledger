"""
Runtime-only tests for the BankAccountModel Swapper integration.

These tests require django_ledger.tests.settings_swappable_bank_account so the
custom model is configured before Django's app registry is populated.
"""

import unittest
from uuid import uuid4

import swapper
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, DEBIT
from django_ledger.models.bank_account import BankAccountModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.utils import lazy_loader


CUSTOM_BANK_ACCOUNT_SETTING = 'swappable_bank_account_app.CustomBankAccountModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_BANKACCOUNTMODEL_MODEL', None) == CUSTOM_BANK_ACCOUNT_SETTING,
    'requires django_ledger.tests.settings_swappable_bank_account',
)
class BankAccountSwappableRuntimeAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomBankAccountModel = apps.get_model('swappable_bank_account_app', 'CustomBankAccountModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_bank_account_admin',
            email='api-swappable-bank-account-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Bank Account Entity'):
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
        cash_account = coa_model.create_account(
            code='1010',
            name=f'{name} Cash',
            role=ASSET_CA_CASH,
            balance_type=DEBIT,
            active=True,
            is_role_default=True,
        )
        return {
            'entity_model': entity_model,
            'cash_account': cash_account,
        }

    def create_bank_account(self, entity_model, cash_account, *, name='API Swappable Bank Account', active=True):
        return entity_model.create_bank_account(
            name=name,
            account_type=self.CustomBankAccountModel.ACCOUNT_CHECKING,
            active=active,
            account_model=cash_account,
            bank_account_model_kwargs={
                'account_number': str(uuid4().int)[:12],
                'routing_number': str(uuid4().int)[:9],
            },
        )

    def test_runtime_loader_returns_custom_bank_account_model(self):
        self.assertIs(lazy_loader.get_bank_account_model(), self.CustomBankAccountModel)
        self.assertIs(swapper.load_model('django_ledger', 'BankAccountModel'), self.CustomBankAccountModel)
        self.assertEqual(swapper.get_model_name('django_ledger', 'BankAccountModel'), CUSTOM_BANK_ACCOUNT_SETTING)

    def test_runtime_default_bank_account_model_remains_importable_but_not_effective(self):
        self.assertEqual(BankAccountModel._meta.label, 'django_ledger.BankAccountModel')
        self.assertIsNot(BankAccountModel, self.CustomBankAccountModel)
        self.assertIs(lazy_loader.get_bank_account_model(), self.CustomBankAccountModel)

    def test_runtime_entity_create_bank_account_uses_custom_bank_account_model(self):
        setup = self.create_accounting_setup()

        bank_account = self.create_bank_account(setup['entity_model'], setup['cash_account'])

        self.assertIsInstance(bank_account, self.CustomBankAccountModel)
        self.assertEqual(bank_account.entity_model_id, setup['entity_model'].uuid)
        self.assertEqual(bank_account.account_model_id, setup['cash_account'].uuid)
        self.assertEqual(bank_account.custom_marker, 'custom')
        self.assertTrue(self.CustomBankAccountModel.objects.filter(uuid=bank_account.uuid).exists())

    def test_runtime_entity_get_bank_accounts_queries_custom_bank_account_model(self):
        setup = self.create_accounting_setup(name='API Swappable Bank Account Scoped Entity')
        other_setup = self.create_accounting_setup(name='API Other Swappable Bank Account Scoped Entity')
        active_bank_account = self.create_bank_account(
            setup['entity_model'],
            setup['cash_account'],
            name='API Active Swappable Bank Account',
        )
        inactive_bank_account = self.create_bank_account(
            setup['entity_model'],
            setup['cash_account'],
            name='API Inactive Swappable Bank Account',
            active=False,
        )
        other_bank_account = self.create_bank_account(
            other_setup['entity_model'],
            other_setup['cash_account'],
            name='API Other Swappable Bank Account',
        )

        default_bank_account_qs = setup['entity_model'].get_bank_accounts()
        all_bank_account_qs = setup['entity_model'].get_bank_accounts(active=False)

        self.assertIs(default_bank_account_qs.model, self.CustomBankAccountModel)
        self.assertIs(all_bank_account_qs.model, self.CustomBankAccountModel)
        self.assertTrue(default_bank_account_qs.filter(uuid=active_bank_account.uuid).exists())
        self.assertFalse(default_bank_account_qs.filter(uuid=inactive_bank_account.uuid).exists())
        self.assertFalse(default_bank_account_qs.filter(uuid=other_bank_account.uuid).exists())
        self.assertTrue(all_bank_account_qs.filter(uuid=active_bank_account.uuid).exists())
        self.assertTrue(all_bank_account_qs.filter(uuid=inactive_bank_account.uuid).exists())
        self.assertFalse(all_bank_account_qs.filter(uuid=other_bank_account.uuid).exists())

    def test_runtime_bank_account_forms_resolve_custom_bank_account_model(self):
        from django_ledger.forms.bank_account import BankAccountCreateForm, BankAccountUpdateForm

        setup = self.create_accounting_setup(name='API Swappable Bank Account Form Entity')

        form = BankAccountCreateForm(entity_slug=setup['entity_model'].slug, user_model=self.admin_user)

        self.assertIs(BankAccountCreateForm._meta.model, self.CustomBankAccountModel)
        self.assertIs(BankAccountUpdateForm._meta.model, self.CustomBankAccountModel)
        self.assertTrue(form.fields['account_model'].queryset.filter(uuid=setup['cash_account'].uuid).exists())

    def test_runtime_import_job_create_form_lists_custom_active_bank_accounts(self):
        from django_ledger.forms.data_import import ImportJobModelCreateForm

        setup = self.create_accounting_setup(name='API Swappable Bank Account Import Form Entity')
        active_bank_account = self.create_bank_account(setup['entity_model'], setup['cash_account'])
        inactive_bank_account = self.create_bank_account(
            setup['entity_model'],
            setup['cash_account'],
            active=False,
        )

        form = ImportJobModelCreateForm(entity_model=setup['entity_model'])

        self.assertIs(form.fields['bank_account_model'].queryset.model, self.CustomBankAccountModel)
        self.assertTrue(form.fields['bank_account_model'].queryset.filter(uuid=active_bank_account.uuid).exists())
        self.assertFalse(form.fields['bank_account_model'].queryset.filter(uuid=inactive_bank_account.uuid).exists())
