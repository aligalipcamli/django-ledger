"""
Schema-level tests for the BankAccountModel Strategy A FK proof.

These tests require django_ledger.tests.settings_swappable_bank_account so the
custom bank account model is configured before migrations and app loading.
"""

import unittest
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.checks import run_checks
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, DEBIT
from django_ledger.models.data_import import ImportJobModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.utils import lazy_loader


CUSTOM_BANK_ACCOUNT_SETTING = 'swappable_bank_account_app.CustomBankAccountModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_BANKACCOUNTMODEL_MODEL', None) == CUSTOM_BANK_ACCOUNT_SETTING,
    'requires django_ledger.tests.settings_swappable_bank_account',
)
class BankAccountSwappableSchemaAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomBankAccountModel = apps.get_model('swappable_bank_account_app', 'CustomBankAccountModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_bank_account_schema_admin',
            email='api-swappable-bank-account-schema-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_setup(self):
        suffix = str(uuid4())[:8]
        name = f'API Swappable Bank Account Schema Entity {suffix}'
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
        bank_account = entity_model.create_bank_account(
            name=f'{name} Bank',
            account_type=self.CustomBankAccountModel.ACCOUNT_CHECKING,
            active=True,
            account_model=cash_account,
            bank_account_model_kwargs={
                'account_number': str(uuid4().int)[:12],
                'routing_number': str(uuid4().int)[:9],
            },
        )
        return {
            'entity_model': entity_model,
            'cash_account': cash_account,
            'bank_account': bank_account,
        }

    def test_schema_import_job_bank_account_fk_resolves_to_custom_bank_account_model(self):
        field = ImportJobModel._meta.get_field('bank_account_model')

        self.assertIs(field.remote_field.model, self.CustomBankAccountModel)

    def test_schema_system_checks_do_not_report_swapped_bank_account_fk_errors(self):
        errors = [error for error in run_checks() if error.id == 'fields.E301']

        self.assertEqual(errors, [])

    def test_schema_import_job_accepts_custom_bank_account_assignment(self):
        setup = self.create_setup()
        bank_account = setup['bank_account']

        import_job_model = ImportJobModel(
            description='API Swappable Bank Account Schema Import Job',
            bank_account_model=bank_account,
        )

        self.assertIsInstance(bank_account, self.CustomBankAccountModel)
        self.assertIs(lazy_loader.get_bank_account_model(), self.CustomBankAccountModel)
        self.assertIs(import_job_model.bank_account_model, bank_account)

    def test_schema_import_job_persists_custom_bank_account_rows(self):
        setup = self.create_setup()
        bank_account = setup['bank_account']

        import_job_model = ImportJobModel.objects.create(
            description='API Swappable Bank Account Persisted Import Job',
            bank_account_model=bank_account,
        )
        import_job_model.configure(commit=True)
        import_job_model.refresh_from_db()

        self.assertEqual(import_job_model.bank_account_model_id, bank_account.uuid)
        self.assertEqual(import_job_model.bank_account_model.entity_model_id, setup['entity_model'].uuid)
        self.assertTrue(ImportJobModel.objects.filter(bank_account_model=bank_account).exists())
