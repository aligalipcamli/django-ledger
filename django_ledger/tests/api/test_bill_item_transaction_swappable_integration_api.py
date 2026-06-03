"""
Integration smoke tests for combined BillModel and ItemTransactionModel swapping.
"""

import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.io import ASSET_CA_CASH, ASSET_CA_PREPAID, EXPENSE_OPERATIONAL, LIABILITY_CL_ACC_PAYABLE
from django_ledger.models.bill import BillModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemTransactionModel, ItemModel
from django_ledger.models.utils import lazy_loader


CUSTOM_BILL_SETTING = 'swappable_bill_app.CustomBillModel'
CUSTOM_ITEM_TRANSACTION_SETTING = 'swappable_item_transaction_app.CustomItemTransactionModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_BILLMODEL_MODEL', None) == CUSTOM_BILL_SETTING
    and getattr(settings, 'DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL', None) == CUSTOM_ITEM_TRANSACTION_SETTING,
    'requires django_ledger.tests.settings_swappable_bill_item_transaction',
)
class BillItemTransactionSwappableIntegrationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomBillModel = apps.get_model('swappable_bill_app', 'CustomBillModel')
        cls.CustomItemTransactionModel = apps.get_model(
            'swappable_item_transaction_app',
            'CustomItemTransactionModel',
        )
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_bill_itemtx_admin',
            email='api-swappable-bill-itemtx-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self):
        suffix = str(uuid4())[:8]
        entity_model = EntityModel.create_entity(
            name=f'API Swappable Bill ItemTx Entity {suffix}',
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )
        coa_model = entity_model.create_chart_of_accounts(
            coa_name=f'{entity_model.name} CoA',
            commit=True,
            assign_as_default=True,
        )
        expense_account = None
        for code, role, balance_type in (
            ('1010', ASSET_CA_CASH, 'debit'),
            ('1310', ASSET_CA_PREPAID, 'debit'),
            ('2010', LIABILITY_CL_ACC_PAYABLE, 'credit'),
            ('6010', EXPENSE_OPERATIONAL, 'debit'),
        ):
            account = coa_model.create_account(
                code=code,
                name=f'{entity_model.name} {role}',
                role=role,
                balance_type=balance_type,
                active=True,
                is_role_default=True,
            )
            if role == EXPENSE_OPERATIONAL:
                expense_account = account
        uom_model = entity_model.create_uom(
            name=f'Unit {suffix}',
            unit_abbr=f'u{suffix[:7]}',
            active=True,
            commit=True,
        )
        expense_item = entity_model.create_item_expense(
            name=f'{entity_model.name} Expense Item',
            expense_type=ItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            coa_model=coa_model,
            commit=True,
        )
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
        return {
            'bill_model': bill_model,
            'expense_item': expense_item,
        }

    def test_combined_loaders_and_field_targets_resolve_to_custom_models(self):
        self.assertIs(lazy_loader.get_bill_model(), self.CustomBillModel)
        self.assertIs(lazy_loader.get_item_transaction_model(), self.CustomItemTransactionModel)
        self.assertEqual(BillModel._meta.swapped, CUSTOM_BILL_SETTING)
        self.assertEqual(ItemTransactionModel._meta.swapped, CUSTOM_ITEM_TRANSACTION_SETTING)
        self.assertIs(
            self.CustomItemTransactionModel._meta.get_field('bill_model').remote_field.model,
            self.CustomBillModel,
        )
        self.assertIs(
            self.CustomBillModel._meta.get_field('bill_items').remote_field.through,
            self.CustomItemTransactionModel,
        )

    def test_combined_custom_bill_itemization_uses_custom_item_transaction(self):
        setup = self.create_accounting_setup()
        bill_model = setup['bill_model']
        expense_item = setup['expense_item']
        itemtxs = {
            expense_item.item_number: {
                'quantity': Decimal('2.00'),
                'unit_cost': Decimal('75.00'),
                'total_amount': Decimal('150.00'),
            }
        }

        itemtxs_batch = bill_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=self.CustomBillModel.ITEMIZE_REPLACE,
            commit=True,
        )
        bill_model.mark_as_review(commit=True, date_in_review=date(2026, 1, 16))
        bill_model.refresh_from_db()
        item_tx = self.CustomItemTransactionModel.objects.select_related('bill_model', 'item_model').get(
            bill_model=bill_model,
        )

        self.assertEqual(len(itemtxs_batch), 1)
        self.assertIsInstance(bill_model, self.CustomBillModel)
        self.assertIsInstance(item_tx, self.CustomItemTransactionModel)
        self.assertEqual(item_tx.bill_model_id, bill_model.uuid)
        self.assertEqual(item_tx.custom_marker, 'custom')
        self.assertEqual(bill_model.amount_due, Decimal('150.00'))
        self.assertTrue(bill_model.is_review())
