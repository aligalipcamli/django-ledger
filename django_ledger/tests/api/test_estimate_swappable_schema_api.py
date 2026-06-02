"""
Schema and workflow tests for the EstimateModel Swapper proof.

These tests require django_ledger.tests.settings_swappable_estimate so the custom
estimate model is configured before migrations and app loading.
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

from django_ledger.io import (
    ASSET_CA_CASH,
    ASSET_CA_INVENTORY,
    ASSET_CA_PREPAID,
    ASSET_CA_RECEIVABLES,
    COGS,
    EXPENSE_OPERATIONAL,
    INCOME_OPERATIONAL,
    LIABILITY_CL_ACC_PAYABLE,
    LIABILITY_CL_DEFERRED_REVENUE,
)
from django_ledger.models.bill import BillModel
from django_ledger.models.estimate import EstimateModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.items import ItemModel, ItemTransactionModel
from django_ledger.models.purchase_order import PurchaseOrderModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.models.utils import lazy_loader


CUSTOM_ESTIMATE_SETTING = 'swappable_estimate_app.CustomEstimateModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_ESTIMATEMODEL_MODEL', None) == CUSTOM_ESTIMATE_SETTING,
    'requires django_ledger.tests.settings_swappable_estimate',
)
class EstimateSwappableSchemaAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomEstimateModel = apps.get_model('swappable_estimate_app', 'CustomEstimateModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_estimate_schema_admin',
            email='api-swappable-estimate-schema-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Estimate Schema Entity'):
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
        prepaid_account = coa_model.create_account(
            code='1410',
            name=f'{name} Prepaid',
            role=ASSET_CA_PREPAID,
            balance_type='debit',
            active=True,
            is_role_default=True,
        )
        payable_account = coa_model.create_account(
            code='2010',
            name=f'{name} Payable',
            role=LIABILITY_CL_ACC_PAYABLE,
            balance_type='credit',
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
            code='1510',
            name=f'{name} Inventory',
            role=ASSET_CA_INVENTORY,
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
        coa_model.create_account(
            code='5010',
            name=f'{name} COGS',
            role=COGS,
            balance_type='debit',
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
        service_item = entity_model.create_item_service(
            name=f'{name} Service Item',
            uom_model=uom_model,
            coa_model=coa_model,
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
        customer_model = self.create_customer(entity_model)
        vendor_model = self.create_vendor(entity_model)
        invoice_model = entity_model.create_invoice(
            customer_model=customer_model,
            terms=InvoiceModel.TERMS_NET_30,
            cash_account=cash_account,
            prepaid_account=receivable_account,
            payable_account=deferred_account,
            date_draft=date(2026, 1, 20),
            commit=True,
        )
        bill_model = entity_model.create_bill(
            vendor_model=vendor_model,
            terms=BillModel.TERMS_NET_30,
            cash_account=cash_account,
            prepaid_account=prepaid_account,
            payable_account=payable_account,
            date_draft=date(2026, 1, 20),
            commit=True,
        )
        po_model = entity_model.create_purchase_order(
            po_title=f'{name} PO',
            date_draft=date(2026, 1, 20),
            commit=True,
        )
        return {
            'entity_model': entity_model,
            'customer_model': customer_model,
            'invoice_model': invoice_model,
            'bill_model': bill_model,
            'po_model': po_model,
            'service_item': service_item,
            'expense_item': expense_item,
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

    def create_vendor(self, entity_model):
        VendorModel = lazy_loader.get_vendor_model()
        vendor_model = VendorModel(
            vendor_name=f'{entity_model.name} Vendor',
            entity_model=entity_model,
            description=f'{entity_model.name} Vendor description',
            active=True,
            hidden=False,
        )
        vendor_model.full_clean()
        vendor_model.save()
        return vendor_model

    def create_estimate(self, setup, title='API Swappable Estimate Schema Contract'):
        estimate_model = setup['entity_model'].create_estimate(
            estimate_title=title,
            contract_terms=self.CustomEstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=setup['customer_model'],
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        estimate_model.refresh_from_db()
        return estimate_model

    def itemize_estimate(self, estimate_model, setup):
        itemtxs = {
            setup['service_item'].item_number: {
                'quantity': Decimal('2.00'),
                'unit_cost': Decimal('50.00'),
                'unit_revenue': Decimal('75.00'),
                'total_amount': Decimal('150.00'),
            }
        }
        itemtxs_batch = estimate_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=self.CustomEstimateModel.ITEMIZE_REPLACE,
            commit=True,
        )
        estimate_model.refresh_from_db()
        return itemtxs_batch

    def approve_estimate(self, estimate_model, setup):
        self.itemize_estimate(estimate_model, setup)
        estimate_model.mark_as_review(commit=True, date_in_review=date(2026, 1, 16))
        estimate_model.refresh_from_db()
        estimate_model.mark_as_approved(commit=True, date_approved=date(2026, 1, 17))
        estimate_model.refresh_from_db()
        return estimate_model

    def test_schema_estimate_model_is_swapped_out(self):
        self.assertEqual(EstimateModel._meta.label, 'django_ledger.EstimateModel')
        self.assertEqual(EstimateModel._meta.swapped, CUSTOM_ESTIMATE_SETTING)
        self.assertIs(lazy_loader.get_estimate_model(), self.CustomEstimateModel)

    def test_schema_document_estimate_fks_resolve_to_custom_estimate_model(self):
        fk_cases = (
            (ItemTransactionModel, 'ce_model'),
            (BillModel, 'ce_model'),
            (InvoiceModel, 'ce_model'),
            (PurchaseOrderModel, 'ce_model'),
        )

        for model_class, field_name in fk_cases:
            with self.subTest(model=model_class.__name__, field=field_name):
                field = model_class._meta.get_field(field_name)
                self.assertIs(field.remote_field.model, self.CustomEstimateModel)

    def test_schema_system_checks_do_not_report_swapped_estimate_fk_errors(self):
        errors = [error for error in run_checks() if error.id == 'fields.E301']

        self.assertEqual(errors, [])

    def test_schema_commercial_documents_keep_expected_swappability_boundary(self):
        self.assertEqual(BillModel._meta.swappable, 'DJANGO_LEDGER_BILLMODEL_MODEL')
        self.assertEqual(InvoiceModel._meta.swappable, 'DJANGO_LEDGER_INVOICEMODEL_MODEL')
        self.assertEqual(ItemTransactionModel._meta.swappable, 'DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL')
        self.assertEqual(PurchaseOrderModel._meta.swappable, 'DJANGO_LEDGER_PURCHASEORDERMODEL_MODEL')
        self.assertIs(lazy_loader.get_purchase_order_model(), PurchaseOrderModel)
        self.assertIsNone(ReceiptModel._meta.swappable)

    def test_schema_item_transaction_accepts_and_persists_custom_estimate_assignment(self):
        setup = self.create_accounting_setup()
        estimate_model = self.create_estimate(setup)
        item_tx = ItemTransactionModel.objects.create(
            ce_model=estimate_model,
            item_model=setup['service_item'],
            ce_quantity=1,
            ce_unit_cost_estimate=10,
            ce_unit_revenue_estimate=15,
        )
        item_tx = ItemTransactionModel.objects.select_related('ce_model', 'item_model').get(uuid=item_tx.uuid)

        self.assertEqual(item_tx.ce_model_id, estimate_model.uuid)
        self.assertIsInstance(item_tx.ce_model, self.CustomEstimateModel)

    def test_schema_custom_estimate_itemization_and_lifecycle_smoke(self):
        setup = self.create_accounting_setup(name='API Swappable Estimate Lifecycle Entity')
        estimate_model = self.create_estimate(setup)

        itemtxs_batch = self.itemize_estimate(estimate_model, setup)
        estimate_model.mark_as_review(commit=True, date_in_review=date(2026, 1, 16))
        estimate_model.refresh_from_db()
        estimate_model.mark_as_approved(commit=True, date_approved=date(2026, 1, 17))
        estimate_model.refresh_from_db()
        item_tx = ItemTransactionModel.objects.select_related('ce_model', 'item_model').get(ce_model=estimate_model)

        self.assertEqual(len(itemtxs_batch), 1)
        self.assertIsInstance(estimate_model, self.CustomEstimateModel)
        self.assertEqual(item_tx.ce_model_id, estimate_model.uuid)
        self.assertEqual(item_tx.ce_cost_estimate, Decimal('100.00'))
        self.assertEqual(item_tx.ce_revenue_estimate, Decimal('150.00'))
        self.assertEqual(estimate_model.labor_estimate, Decimal('100.00'))
        self.assertEqual(estimate_model.revenue_estimate, Decimal('150.00'))
        self.assertTrue(estimate_model.is_approved())

    def test_schema_custom_estimate_binds_to_downstream_documents(self):
        setup = self.create_accounting_setup(name='API Swappable Estimate Binding Entity')
        estimate_model = self.approve_estimate(self.create_estimate(setup), setup)
        invoice_model = setup['invoice_model']
        bill_model = setup['bill_model']
        po_model = setup['po_model']

        invoice_model.bind_estimate(estimate_model, commit=True)
        bill_model.bind_estimate(estimate_model, commit=True)
        po_model.action_bind_estimate(estimate_model, commit=True)
        invoice_model.refresh_from_db()
        bill_model.refresh_from_db()
        po_model.refresh_from_db()

        self.assertEqual(invoice_model.ce_model_id, estimate_model.uuid)
        self.assertEqual(bill_model.ce_model_id, estimate_model.uuid)
        self.assertEqual(po_model.ce_model_id, estimate_model.uuid)
        self.assertIsInstance(invoice_model.ce_model, self.CustomEstimateModel)
        self.assertIsInstance(bill_model.ce_model, self.CustomEstimateModel)
        self.assertIsInstance(po_model.ce_model, self.CustomEstimateModel)
