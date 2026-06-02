"""
Schema and persistence tests for the ItemTransactionModel Swapper proof.

These tests require django_ledger.tests.settings_swappable_item_transaction so
the custom item transaction model is configured before migrations and app
loading.
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
from django_ledger.models.estimate import EstimateModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.invoice import InvoiceModel
from django_ledger.models.items import ItemModel, ItemTransactionModel
from django_ledger.models.purchase_order import PurchaseOrderModel
from django_ledger.models.receipt import ReceiptModel
from django_ledger.models.utils import lazy_loader


CUSTOM_ITEM_TRANSACTION_SETTING = 'swappable_item_transaction_app.CustomItemTransactionModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL', None) == CUSTOM_ITEM_TRANSACTION_SETTING,
    'requires django_ledger.tests.settings_swappable_item_transaction',
)
class ItemTransactionSwappableSchemaAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomItemTransactionModel = apps.get_model(
            'swappable_item_transaction_app',
            'CustomItemTransactionModel',
        )
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_itemtx_schema_admin',
            email='api-swappable-itemtx-schema-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_accounting_setup(self, name='API Swappable Item Transaction Schema Entity'):
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
        deferred_account = coa_model.create_account(
            code='2310',
            name=f'{name} Deferred Revenue',
            role='lia_cl_def_rev',
            balance_type='credit',
            active=True,
            is_role_default=True,
        )
        inventory_account = coa_model.create_account(
            code='1510',
            name=f'{name} Inventory',
            role='asset_ca_inv',
            balance_type='debit',
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
        service_item = entity_model.create_item_service(
            name=f'{name} Service Item',
            uom_model=uom_model,
            coa_model=coa_model,
            commit=True,
        )
        inventory_item = entity_model.create_item_inventory(
            name=f'{name} Inventory Item',
            item_type=ItemModel.ITEM_TYPE_MATERIAL,
            uom_model=uom_model,
            inventory_account=inventory_account,
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
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        bill_model = entity_model.create_bill(
            vendor_model=vendor_model,
            terms=BillModel.TERMS_NET_30,
            cash_account=cash_account,
            prepaid_account=prepaid_account,
            payable_account=payable_account,
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        po_model = entity_model.create_purchase_order(
            po_title=f'{name} PO',
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        return {
            'entity_model': entity_model,
            'customer_model': customer_model,
            'invoice_model': invoice_model,
            'bill_model': bill_model,
            'po_model': po_model,
            'service_item': service_item,
            'inventory_item': inventory_item,
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

    def test_schema_default_item_transaction_model_is_swapped_out(self):
        self.assertEqual(ItemTransactionModel._meta.label, 'django_ledger.ItemTransactionModel')
        self.assertEqual(ItemTransactionModel._meta.swapped, CUSTOM_ITEM_TRANSACTION_SETTING)
        self.assertIs(lazy_loader.get_item_transaction_model(), self.CustomItemTransactionModel)

    def test_schema_custom_item_transaction_document_fks_resolve_to_effective_models(self):
        fk_cases = (
            ('bill_model', BillModel),
            ('invoice_model', InvoiceModel),
            ('po_model', lazy_loader.get_purchase_order_model()),
            ('ce_model', lazy_loader.get_estimate_model()),
            ('item_model', lazy_loader.get_item_model()),
        )

        for field_name, expected_model in fk_cases:
            with self.subTest(field=field_name):
                field = self.CustomItemTransactionModel._meta.get_field(field_name)
                self.assertIs(field.remote_field.model, expected_model)

    def test_schema_document_item_m2ms_use_custom_item_transaction_through_model(self):
        m2m_cases = (
            (BillModel, 'bill_items'),
            (InvoiceModel, 'invoice_items'),
            (PurchaseOrderModel, 'po_items'),
        )

        for model_class, field_name in m2m_cases:
            with self.subTest(model=model_class.__name__, field=field_name):
                field = model_class._meta.get_field(field_name)
                self.assertIs(field.remote_field.through, self.CustomItemTransactionModel)
                self.assertIs(field.remote_field.model, lazy_loader.get_item_model())

    def test_schema_system_checks_do_not_report_swapped_item_transaction_errors(self):
        errors = [error for error in run_checks() if error.id == 'fields.E301']

        self.assertEqual(errors, [])

    def test_schema_commercial_documents_keep_expected_swappability_boundary(self):
        self.assertEqual(BillModel._meta.swappable, 'DJANGO_LEDGER_BILLMODEL_MODEL')
        self.assertEqual(EstimateModel._meta.swappable, 'DJANGO_LEDGER_ESTIMATEMODEL_MODEL')
        self.assertEqual(PurchaseOrderModel._meta.swappable, 'DJANGO_LEDGER_PURCHASEORDERMODEL_MODEL')
        self.assertIs(lazy_loader.get_purchase_order_model(), PurchaseOrderModel)
        self.assertIsNone(ReceiptModel._meta.swappable)
        self.assertIs(lazy_loader.get_estimate_model(), EstimateModel)

    def test_schema_custom_item_transaction_persists_document_assignment(self):
        setup = self.create_accounting_setup()
        item_tx = self.CustomItemTransactionModel.objects.create(
            invoice_model=setup['invoice_model'],
            item_model=setup['service_item'],
            quantity=1,
            unit_cost=10,
        )
        item_tx = self.CustomItemTransactionModel.objects.select_related('invoice_model', 'item_model').get(
            uuid=item_tx.uuid,
        )

        self.assertEqual(item_tx.invoice_model_id, setup['invoice_model'].uuid)
        self.assertEqual(item_tx.item_model_id, setup['service_item'].uuid)
        self.assertEqual(item_tx.custom_marker, 'custom')

    def test_schema_bill_itemization_uses_custom_item_transaction(self):
        setup = self.create_accounting_setup(name='API Swappable Item Transaction Bill Entity')
        bill_model = setup['bill_model']
        expense_item = setup['expense_item']
        itemtxs = {
            expense_item.item_number: {
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
        bill_model.refresh_from_db()
        item_tx = self.CustomItemTransactionModel.objects.select_related('bill_model', 'item_model').get(
            bill_model=bill_model,
        )

        self.assertEqual(BillModel._meta.swappable, 'DJANGO_LEDGER_BILLMODEL_MODEL')
        self.assertEqual(len(itemtxs_batch), 1)
        self.assertIsInstance(item_tx, self.CustomItemTransactionModel)
        self.assertEqual(item_tx.bill_model_id, bill_model.uuid)
        self.assertEqual(item_tx.item_model_id, expense_item.uuid)
        self.assertEqual(item_tx.total_amount, Decimal('100.00'))
        self.assertEqual(bill_model.amount_due, Decimal('100.00'))

    def test_schema_estimate_itemization_uses_custom_item_transaction(self):
        setup = self.create_accounting_setup(name='API Swappable Item Transaction Estimate Entity')
        estimate_model = setup['entity_model'].create_estimate(
            estimate_title='API Swappable Item Transaction Estimate',
            contract_terms=EstimateModel.CONTRACT_TERMS_FIXED,
            customer_model=setup['customer_model'],
            date_draft=date(2026, 1, 15),
            commit=True,
        )
        service_item = setup['service_item']
        itemtxs = {
            service_item.item_number: {
                'quantity': Decimal('2.00'),
                'unit_cost': Decimal('50.00'),
                'unit_revenue': Decimal('75.00'),
                'total_amount': Decimal('150.00'),
            }
        }

        itemtxs_batch = estimate_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=EstimateModel.ITEMIZE_REPLACE,
            commit=True,
        )
        estimate_model.refresh_from_db()
        item_tx = self.CustomItemTransactionModel.objects.select_related('ce_model', 'item_model').get(
            ce_model=estimate_model,
        )

        self.assertEqual(EstimateModel._meta.swappable, 'DJANGO_LEDGER_ESTIMATEMODEL_MODEL')
        self.assertEqual(len(itemtxs_batch), 1)
        self.assertIsInstance(item_tx, self.CustomItemTransactionModel)
        self.assertEqual(item_tx.ce_model_id, estimate_model.uuid)
        self.assertEqual(item_tx.item_model_id, service_item.uuid)
        self.assertEqual(item_tx.ce_cost_estimate, Decimal('100.00'))
        self.assertEqual(item_tx.ce_revenue_estimate, Decimal('150.00'))
        self.assertEqual(estimate_model.labor_estimate, Decimal('100.00'))
        self.assertEqual(estimate_model.revenue_estimate, Decimal('150.00'))

    def test_schema_invoice_itemization_and_lifecycle_use_custom_item_transaction(self):
        setup = self.create_accounting_setup(name='API Swappable Item Transaction Invoice Entity')
        invoice_model = setup['invoice_model']
        service_item = setup['service_item']
        itemtxs = {
            service_item.item_number: {
                'quantity': Decimal('2.00'),
                'unit_cost': Decimal('50.00'),
                'total_amount': Decimal('100.00'),
            }
        }

        itemtxs_batch = invoice_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=InvoiceModel.ITEMIZE_REPLACE,
            commit=True,
        )
        invoice_model.mark_as_review(commit=True, date_in_review=date(2026, 1, 16))
        invoice_model.refresh_from_db()
        item_tx = self.CustomItemTransactionModel.objects.select_related('invoice_model', 'item_model').get(
            invoice_model=invoice_model,
        )

        self.assertEqual(len(itemtxs_batch), 1)
        self.assertIsInstance(item_tx, self.CustomItemTransactionModel)
        self.assertEqual(item_tx.invoice_model_id, invoice_model.uuid)
        self.assertEqual(item_tx.item_model_id, service_item.uuid)
        self.assertEqual(item_tx.total_amount, Decimal('100.00'))
        self.assertEqual(invoice_model.amount_due, Decimal('100.00'))
        self.assertTrue(invoice_model.is_review())

    def test_schema_purchase_order_itemization_uses_custom_related_manager(self):
        setup = self.create_accounting_setup(name='API Swappable Item Transaction PO Entity')
        po_model = setup['po_model']
        inventory_item = setup['inventory_item']
        itemtxs = {
            inventory_item.item_number: {
                'quantity': Decimal('3.00'),
                'unit_cost': Decimal('20.00'),
                'total_amount': Decimal('60.00'),
            }
        }

        itemtxs_batch = po_model.migrate_itemtxs(
            itemtxs=itemtxs,
            operation=PurchaseOrderModel.ITEMIZE_REPLACE,
            commit=True,
        )
        po_model.mark_as_review(commit=True, date_in_review=date(2026, 1, 16))
        po_model.refresh_from_db()
        po_model.mark_as_approved(commit=True, date_approved=date(2026, 1, 16))
        item_tx = po_model.get_itemtxs_related_manager().get()
        item_tx.bill_model = setup['bill_model']
        item_tx.save(update_fields=['bill_model', 'updated'])
        bill_qs = po_model.get_po_bill_queryset()

        self.assertEqual(len(itemtxs_batch), 1)
        self.assertIsInstance(item_tx, self.CustomItemTransactionModel)
        self.assertEqual(item_tx.po_model_id, po_model.uuid)
        self.assertEqual(item_tx.item_model_id, inventory_item.uuid)
        self.assertEqual(item_tx.po_total_amount, Decimal('60.00'))
        self.assertEqual(item_tx.po_item_status, self.CustomItemTransactionModel.STATUS_NOT_ORDERED)
        self.assertTrue(bill_qs.filter(uuid=setup['bill_model'].uuid).exists())
