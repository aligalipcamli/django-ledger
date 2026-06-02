"""
Integration smoke tests for combined InvoiceModel and ItemTransactionModel swapping.

These tests require django_ledger.tests.settings_swappable_invoice_item_transaction
so both custom models are configured before Django's app registry is populated.
"""

import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.items import ItemTransactionModel
from django_ledger.models.utils import lazy_loader


CUSTOM_INVOICE_SETTING = 'swappable_invoice_app.CustomInvoiceModel'
CUSTOM_ITEM_TRANSACTION_SETTING = 'swappable_item_transaction_app.CustomItemTransactionModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_INVOICEMODEL_MODEL', None) == CUSTOM_INVOICE_SETTING
    and getattr(settings, 'DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL', None) == CUSTOM_ITEM_TRANSACTION_SETTING,
    'requires django_ledger.tests.settings_swappable_invoice_item_transaction',
)
class InvoiceItemTransactionSwappableIntegrationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomInvoiceModel = apps.get_model('swappable_invoice_app', 'CustomInvoiceModel')
        cls.CustomItemTransactionModel = apps.get_model(
            'swappable_item_transaction_app',
            'CustomItemTransactionModel',
        )
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_invoice_itemtx_admin',
            email='api-swappable-invoice-itemtx-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Invoice Item Transaction Entity'):
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
        receivable_account = coa_model.create_account(
            code='1210',
            name=f'{name} Receivable',
            role='asset_ca_recv',
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        deferred_account = coa_model.create_account(
            code='2310',
            name=f'{name} Deferred Revenue',
            role='lia_cl_def_rev',
            balance_type='credit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='5010',
            name=f'{name} COGS',
            role='cogs_regular',
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='4010',
            name=f'{name} Income',
            role='in_operational',
            balance_type='credit',
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
        invoice_model = entity_model.create_invoice(
            customer_model=customer_model,
            terms=self.CustomInvoiceModel.TERMS_NET_30,
            cash_account=cash_account,
            prepaid_account=receivable_account,
            payable_account=deferred_account,
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        invoice_model.refresh_from_db()
        return {
            'invoice_model': invoice_model,
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

    def test_combined_loaders_and_field_targets_resolve_to_custom_models(self):
        InvoiceModelEffective = lazy_loader.get_invoice_model()
        ItemTransactionModelEffective = lazy_loader.get_item_transaction_model()

        self.assertIs(InvoiceModelEffective, self.CustomInvoiceModel)
        self.assertIs(ItemTransactionModelEffective, self.CustomItemTransactionModel)
        self.assertEqual(InvoiceModel._meta.swapped, CUSTOM_INVOICE_SETTING)
        self.assertEqual(ItemTransactionModel._meta.swapped, CUSTOM_ITEM_TRANSACTION_SETTING)
        self.assertIs(
            self.CustomItemTransactionModel._meta.get_field('invoice_model').remote_field.model,
            self.CustomInvoiceModel,
        )
        self.assertIs(
            self.CustomInvoiceModel._meta.get_field('invoice_items').remote_field.through,
            self.CustomItemTransactionModel,
        )

    def test_combined_custom_invoice_itemization_uses_custom_item_transaction(self):
        setup = self.create_accounting_setup()
        invoice_model = setup['invoice_model']
        service_item = setup['service_item']
        itemtxs = {
            service_item.item_number: {
                'quantity': Decimal('2.00'),
                'unit_cost': Decimal('75.00'),
                'total_amount': Decimal('150.00'),
            }
        }

        itemtxs_batch = invoice_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=self.CustomInvoiceModel.ITEMIZE_REPLACE,
            commit=True,
        )
        invoice_model.mark_as_review(commit=True, date_in_review=date(2026, 1, 16))
        invoice_model.refresh_from_db()
        item_tx = self.CustomItemTransactionModel.objects.select_related('invoice_model', 'item_model').get(
            invoice_model=invoice_model,
        )

        self.assertEqual(len(itemtxs_batch), 1)
        self.assertIsInstance(invoice_model, self.CustomInvoiceModel)
        self.assertIsInstance(item_tx, self.CustomItemTransactionModel)
        self.assertEqual(item_tx.invoice_model_id, invoice_model.uuid)
        self.assertEqual(item_tx.custom_marker, 'custom')
        self.assertEqual(invoice_model.amount_due, Decimal('150.00'))
        self.assertTrue(invoice_model.is_review())
