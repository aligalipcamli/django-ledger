"""
Runtime tests for InvoiceModel Swapper integration.

These tests require django_ledger.tests.settings_swappable_invoice so the custom
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
    ASSET_CA_RECEIVABLES,
    COGS,
    INCOME_OPERATIONAL,
    LIABILITY_CL_DEFERRED_REVENUE,
)
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.utils import lazy_loader


CUSTOM_INVOICE_SETTING = 'swappable_invoice_app.CustomInvoiceModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_INVOICEMODEL_MODEL', None) == CUSTOM_INVOICE_SETTING,
    'requires django_ledger.tests.settings_swappable_invoice',
)
class InvoiceSwappableRuntimeAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomInvoiceModel = apps.get_model('swappable_invoice_app', 'CustomInvoiceModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_invoice_admin',
            email='api-swappable-invoice-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Invoice Entity'):
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
            code='1210',
            name=f'{name} Receivable',
            role=ASSET_CA_RECEIVABLES,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='2310',
            name=f'{name} Deferred Revenue',
            role=LIABILITY_CL_DEFERRED_REVENUE,
            balance_type='credit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='5010',
            name=f'{name} COGS',
            role=COGS,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        coa_model.create_account(
            code='4010',
            name=f'{name} Income',
            role=INCOME_OPERATIONAL,
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
        CustomerModel = lazy_loader.get_customer_model()
        customer_model = CustomerModel(
            customer_name=f'{name} Customer',
            entity_model=entity_model,
            description=f'{name} Customer description',
            active=True,
            hidden=False,
        )
        customer_model.full_clean()
        customer_model.save()
        return {
            'entity_model': entity_model,
            'customer_model': customer_model,
            'service_item': service_item,
        }

    def create_invoice(self, setup):
        invoice_model = setup['entity_model'].create_invoice(
            customer_model=setup['customer_model'],
            terms=self.CustomInvoiceModel.TERMS_NET_30,
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        invoice_model.refresh_from_db()
        return invoice_model

    def test_runtime_loader_returns_custom_invoice_model(self):
        self.assertIs(lazy_loader.get_invoice_model(), self.CustomInvoiceModel)
        self.assertIs(swapper.load_model('django_ledger', 'InvoiceModel'), self.CustomInvoiceModel)
        self.assertEqual(swapper.get_model_name('django_ledger', 'InvoiceModel'), CUSTOM_INVOICE_SETTING)

    def test_runtime_default_invoice_model_remains_importable_but_not_effective(self):
        self.assertEqual(InvoiceModel._meta.label, 'django_ledger.InvoiceModel')
        self.assertIsNot(InvoiceModel, self.CustomInvoiceModel)
        self.assertIs(lazy_loader.get_invoice_model(), self.CustomInvoiceModel)

    def test_runtime_entity_create_invoice_uses_custom_invoice_model(self):
        setup = self.create_accounting_setup()

        invoice_model = self.create_invoice(setup)

        self.assertIsInstance(invoice_model, self.CustomInvoiceModel)
        self.assertEqual(invoice_model.entity_model_id, setup['entity_model'].uuid)
        self.assertTrue(invoice_model.invoice_number)
        self.assertEqual(invoice_model.custom_marker, 'custom')
        self.assertTrue(self.CustomInvoiceModel.objects.filter(uuid=invoice_model.uuid).exists())
        self.assertEqual(InvoiceModel._meta.swapped, CUSTOM_INVOICE_SETTING)

    def test_runtime_entity_get_invoices_queries_custom_invoice_model(self):
        setup = self.create_accounting_setup(name='API Swappable Invoice Scoped Entity')
        other_setup = self.create_accounting_setup(name='API Other Swappable Invoice Scoped Entity')
        invoice_model = self.create_invoice(setup)
        other_invoice_model = self.create_invoice(other_setup)

        invoice_qs = setup['entity_model'].get_invoices()

        self.assertIs(invoice_qs.model, self.CustomInvoiceModel)
        self.assertTrue(invoice_qs.filter(uuid=invoice_model.uuid).exists())
        self.assertFalse(invoice_qs.filter(uuid=other_invoice_model.uuid).exists())

    def test_runtime_invoice_forms_use_custom_invoice_model(self):
        from django_ledger.forms.invoice import (
            BaseInvoiceModelUpdateForm,
            InvoiceModelCreateForEstimateForm,
            InvoiceModelCreateForm,
        )

        setup = self.create_accounting_setup(name='API Swappable Invoice Form Entity')
        form = InvoiceModelCreateForm(entity_slug=setup['entity_model'].slug, user_model=self.admin_user)

        self.assertIs(InvoiceModelCreateForm._meta.model, self.CustomInvoiceModel)
        self.assertIs(InvoiceModelCreateForEstimateForm._meta.model, self.CustomInvoiceModel)
        self.assertIs(BaseInvoiceModelUpdateForm._meta.model, self.CustomInvoiceModel)
        self.assertIs(form.instance.__class__, self.CustomInvoiceModel)

    def test_runtime_invoice_list_view_queryset_uses_custom_invoice_model(self):
        from django_ledger.views.invoice import InvoiceModelListView

        setup = self.create_accounting_setup(name='API Swappable Invoice View Entity')
        invoice_model = self.create_invoice(setup)
        view = InvoiceModelListView()
        view.kwargs = {'entity_slug': setup['entity_model'].slug}

        invoice_qs = view.get_queryset()

        self.assertIs(invoice_qs.model, self.CustomInvoiceModel)
        self.assertTrue(invoice_qs.filter(uuid=invoice_model.uuid).exists())
