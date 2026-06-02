"""
Schema-level tests for the ItemModel Strategy A FK/M2M proof.

These tests require django_ledger.tests.settings_swappable_item so the custom
item model is configured before migrations and app loading.
"""

import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.checks import run_checks
from django.test import TestCase

from django_ledger.models.bill import BillModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.items import ItemTransactionModel
from django_ledger.models.purchase_order import PurchaseOrderModel
from django_ledger.models.utils import lazy_loader


CUSTOM_ITEM_SETTING = 'swappable_item_app.CustomItemModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_ITEMMODEL_MODEL', None) == CUSTOM_ITEM_SETTING,
    'requires django_ledger.tests.settings_swappable_item',
)
class ItemSwappableSchemaAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomItemModel = apps.get_model('swappable_item_app', 'CustomItemModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_item_schema_admin',
            email='api-swappable-item-schema-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_setup(self, name='API Swappable Item Schema Entity'):
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
            role='asset_ca_cash',
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        prepaid_account = coa_model.create_account(
            code='1410',
            name=f'{name} Prepaid',
            role='asset_ca_prepaid',
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        payable_account = coa_model.create_account(
            code='2010',
            name=f'{name} Payable',
            role='lia_cl_acc_payable',
            balance_type='credit',
            active=True,
            is_role_default=True,
        )
        expense_account = coa_model.create_account(
            code='6010',
            name=f'{name} Expense',
            role='ex_regular',
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
        VendorModel = lazy_loader.get_vendor_model()
        vendor_model = VendorModel(
            vendor_name=f'{name} Vendor',
            entity_model=entity_model,
            description=f'{name} Vendor description',
            active=True,
            hidden=False,
        )
        vendor_model.full_clean()
        vendor_model.save()
        item_model = entity_model.create_item_expense(
            name=f'{name} Expense Item',
            expense_type=self.CustomItemModel.ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            coa_model=coa_model,
            commit=True,
        )
        return {
            'entity_model': entity_model,
            'cash_account': cash_account,
            'prepaid_account': prepaid_account,
            'payable_account': payable_account,
            'vendor_model': vendor_model,
            'item_model': item_model,
        }

    def configure_bill(self, setup):
        bill_model = BillModel(
            vendor=setup['vendor_model'],
            terms=BillModel.TERMS_NET_30,
            cash_account=setup['cash_account'],
            prepaid_account=setup['prepaid_account'],
            unearned_account=setup['payable_account'],
        )
        _ledger_model, bill_model = bill_model.configure(
            entity_slug=setup['entity_model'],
            user_model=self.admin_user,
            date_draft=date(2026, 1, 15),
            ledger_name='API Swappable Item Bill Ledger',
            commit=True,
            commit_ledger=False,
        )
        bill_model.refresh_from_db()
        return bill_model

    def test_schema_item_transaction_fk_resolves_to_custom_item_model(self):
        field = ItemTransactionModel._meta.get_field('item_model')

        self.assertIs(field.remote_field.model, self.CustomItemModel)

    def test_schema_document_item_m2ms_resolve_to_custom_item_model(self):
        m2m_cases = (
            (BillModel, 'bill_items'),
            (InvoiceModel, 'invoice_items'),
            (PurchaseOrderModel, 'po_items'),
        )

        for model_class, field_name in m2m_cases:
            with self.subTest(model=model_class.__name__, field=field_name):
                field = model_class._meta.get_field(field_name)
                self.assertIs(field.remote_field.model, self.CustomItemModel)
                self.assertIs(field.remote_field.through, ItemTransactionModel)

    def test_schema_system_checks_do_not_report_swapped_item_fk_errors(self):
        errors = [error for error in run_checks() if error.id == 'fields.E301']

        self.assertEqual(errors, [])

    def test_schema_item_transaction_accepts_custom_item_assignment(self):
        setup = self.create_setup()
        item_model = setup['item_model']

        item_tx = ItemTransactionModel(
            item_model=item_model,
            quantity=1,
            unit_cost=10,
        )

        self.assertIsInstance(item_model, self.CustomItemModel)
        self.assertIs(lazy_loader.get_item_model(), self.CustomItemModel)
        self.assertIs(item_tx.item_model, item_model)

    def test_schema_item_transaction_persists_custom_item_rows(self):
        setup = self.create_setup(name='API Swappable Item Persisted Tx Entity')
        item_model = setup['item_model']

        item_tx = ItemTransactionModel.objects.create(item_model=item_model)

        self.assertEqual(item_tx.item_model_id, item_model.uuid)
        self.assertTrue(ItemTransactionModel.objects.filter(item_model=item_model).exists())

    def test_schema_bill_itemization_persists_custom_item_transaction(self):
        setup = self.create_setup(name='API Swappable Item Bill Itemization Entity')
        bill_model = self.configure_bill(setup)
        item_model = setup['item_model']
        itemtxs = {
            item_model.item_number: {
                'quantity': Decimal('2.00'),
                'unit_cost': Decimal('50.00'),
                'total_amount': Decimal('100.00'),
            }
        }

        itemtxs_batch = bill_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=BillModel.ITEMIZE_REPLACE,
            commit=True,
        )

        self.assertEqual(len(itemtxs_batch), 1)
        item_tx = ItemTransactionModel.objects.select_related('item_model').get(bill_model=bill_model)
        self.assertEqual(item_tx.item_model_id, item_model.uuid)
        self.assertIsInstance(item_tx.item_model, self.CustomItemModel)
        self.assertEqual(item_tx.total_amount, Decimal('100.00'))
