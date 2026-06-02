"""
Runtime tests for ItemTransactionModel Swapper integration.

These tests require django_ledger.tests.settings_swappable_item_transaction so
the custom model is configured before Django's app registry is populated.
"""

import unittest
from uuid import uuid4

import swapper
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.entity import EntityModel
from django_ledger.models.items import ItemTransactionModel
from django_ledger.models.utils import lazy_loader


CUSTOM_ITEM_TRANSACTION_SETTING = 'swappable_item_transaction_app.CustomItemTransactionModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL', None) == CUSTOM_ITEM_TRANSACTION_SETTING,
    'requires django_ledger.tests.settings_swappable_item_transaction',
)
class ItemTransactionSwappableRuntimeAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomItemTransactionModel = apps.get_model(
            'swappable_item_transaction_app',
            'CustomItemTransactionModel',
        )
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_itemtx_admin',
            email='api-swappable-itemtx-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Item Transaction Entity'):
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
            role='asset_ca_cash',
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='1210',
            name=f'{name} Receivable',
            role='asset_ca_recv',
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='2310',
            name=f'{name} Deferred Revenue',
            role='lia_cl_def_rev',
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
        item_model = entity_model.create_item_expense(
            name=f'{name} Expense Item',
            expense_type=lazy_loader.get_item_model().ITEM_TYPE_OTHER,
            uom_model=uom_model,
            expense_account=expense_account,
            coa_model=coa_model,
            commit=True,
        )
        return {
            'entity_model': entity_model,
            'item_model': item_model,
        }

    def test_runtime_loader_returns_custom_item_transaction_model(self):
        self.assertIs(lazy_loader.get_item_transaction_model(), self.CustomItemTransactionModel)
        self.assertIs(
            swapper.load_model('django_ledger', 'ItemTransactionModel'),
            self.CustomItemTransactionModel,
        )
        self.assertEqual(
            swapper.get_model_name('django_ledger', 'ItemTransactionModel'),
            CUSTOM_ITEM_TRANSACTION_SETTING,
        )

    def test_runtime_default_item_transaction_model_remains_importable_but_not_effective(self):
        self.assertEqual(ItemTransactionModel._meta.label, 'django_ledger.ItemTransactionModel')
        self.assertIsNot(ItemTransactionModel, self.CustomItemTransactionModel)
        self.assertEqual(ItemTransactionModel._meta.swapped, CUSTOM_ITEM_TRANSACTION_SETTING)
        self.assertIs(lazy_loader.get_item_transaction_model(), self.CustomItemTransactionModel)

    def test_runtime_manager_queryset_methods_use_custom_model_constants(self):
        setup = self.create_accounting_setup()
        item_tx = self.CustomItemTransactionModel.objects.create(
            item_model=setup['item_model'],
            po_item_status=self.CustomItemTransactionModel.STATUS_RECEIVED,
        )

        received_qs = self.CustomItemTransactionModel.objects.is_received()

        self.assertIs(received_qs.model, self.CustomItemTransactionModel)
        self.assertTrue(received_qs.filter(uuid=item_tx.uuid).exists())

    def test_runtime_item_transaction_forms_use_custom_model(self):
        from django_ledger.forms.bill import BillItemTransactionForm
        from django_ledger.forms.estimate import EstimateItemModelForm
        from django_ledger.forms.invoice import InvoiceItemForm
        from django_ledger.forms.purchase_order import PurchaseOrderItemTransactionForm

        self.assertIs(BillItemTransactionForm._meta.model, self.CustomItemTransactionModel)
        self.assertIs(EstimateItemModelForm._meta.model, self.CustomItemTransactionModel)
        self.assertIs(InvoiceItemForm._meta.model, self.CustomItemTransactionModel)
        self.assertIs(PurchaseOrderItemTransactionForm._meta.model, self.CustomItemTransactionModel)

    def test_runtime_document_related_manager_resolves_custom_accessor(self):
        setup = self.create_accounting_setup(name='API Swappable Item Transaction Related Entity')
        invoice_model = setup['entity_model'].create_invoice(
            customer_model=self.create_customer(setup['entity_model']),
            terms=lazy_loader.get_invoice_model().TERMS_NET_30,
            commit=True,
        )
        item_tx = self.CustomItemTransactionModel.objects.create(
            invoice_model=invoice_model,
            item_model=setup['item_model'],
        )

        related_manager = invoice_model.get_itemtxs_related_manager()
        related_name = lazy_loader.get_item_transaction_model_related_name('invoice_model')

        self.assertIs(related_manager.model, self.CustomItemTransactionModel)
        self.assertTrue(hasattr(invoice_model, related_name))
        self.assertTrue(related_manager.filter(uuid=item_tx.uuid).exists())

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
