"""
Integration smoke tests for combined EstimateModel and InvoiceModel swapping.
"""

import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

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
from django_ledger.models.estimate import EstimateModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.items import ItemTransactionModel
from django_ledger.models.utils import lazy_loader


CUSTOM_ESTIMATE_SETTING = 'swappable_estimate_app.CustomEstimateModel'
CUSTOM_INVOICE_SETTING = 'swappable_invoice_app.CustomInvoiceModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_ESTIMATEMODEL_MODEL', None) == CUSTOM_ESTIMATE_SETTING
    and getattr(settings, 'DJANGO_LEDGER_INVOICEMODEL_MODEL', None) == CUSTOM_INVOICE_SETTING,
    'requires django_ledger.tests.settings_swappable_estimate_invoice',
)
class EstimateInvoiceSwappableIntegrationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomEstimateModel = apps.get_model('swappable_estimate_app', 'CustomEstimateModel')
        cls.CustomInvoiceModel = apps.get_model('swappable_invoice_app', 'CustomInvoiceModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_estimate_invoice_admin',
            email='api-swappable-estimate-invoice-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Estimate Invoice Entity'):
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
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        receivable_account = coa_model.create_account(
            code='1210',
            name=f'{name} Receivable',
            role=ASSET_CA_RECEIVABLES,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        deferred_account = coa_model.create_account(
            code='2310',
            name=f'{name} Deferred Revenue',
            role=LIABILITY_CL_DEFERRED_REVENUE,
            balance_type='credit',
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
        coa_model.create_account(
            code='5010',
            name=f'{name} COGS',
            role=COGS,
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
            date_draft=date(2026, 1, 20),
            commit=True,
        )
        estimate_model = entity_model.create_estimate(
            estimate_title='API Swappable Estimate Invoice Contract',
            contract_terms=self.CustomEstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=customer_model,
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        return {
            'estimate_model': estimate_model,
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

    def approve_estimate(self, estimate_model, service_item):
        estimate_model.migrate_itemtxs(
            itemtxs={
                service_item.item_number: {
                    'quantity': Decimal('2.00'),
                    'unit_cost': Decimal('50.00'),
                    'unit_revenue': Decimal('75.00'),
                    'total_amount': Decimal('150.00'),
                }
            },
            operation=self.CustomEstimateModel.ITEMIZE_REPLACE,
            commit=True,
        )
        estimate_model.mark_as_review(commit=True, date_in_review=date(2026, 1, 16))
        estimate_model.refresh_from_db()
        estimate_model.mark_as_approved(commit=True, date_approved=date(2026, 1, 17))
        estimate_model.refresh_from_db()
        return estimate_model

    def test_combined_estimate_invoice_field_targets_resolve_to_custom_models(self):
        self.assertIs(lazy_loader.get_estimate_model(), self.CustomEstimateModel)
        self.assertIs(lazy_loader.get_invoice_model(), self.CustomInvoiceModel)
        self.assertEqual(EstimateModel._meta.swapped, CUSTOM_ESTIMATE_SETTING)
        self.assertEqual(InvoiceModel._meta.swapped, CUSTOM_INVOICE_SETTING)
        self.assertIs(
            self.CustomInvoiceModel._meta.get_field('ce_model').remote_field.model,
            self.CustomEstimateModel,
        )

    def test_combined_custom_invoice_binds_to_custom_estimate(self):
        setup = self.create_accounting_setup()
        estimate_model = self.approve_estimate(setup['estimate_model'], setup['service_item'])
        invoice_model = setup['invoice_model']

        invoice_model.bind_estimate(estimate_model, commit=True)
        invoice_model.refresh_from_db()

        self.assertIsInstance(estimate_model, self.CustomEstimateModel)
        self.assertIsInstance(invoice_model, self.CustomInvoiceModel)
        self.assertEqual(invoice_model.ce_model_id, estimate_model.uuid)
        self.assertIsInstance(invoice_model.ce_model, self.CustomEstimateModel)
        self.assertTrue(ItemTransactionModel.objects.filter(ce_model=estimate_model).exists())
