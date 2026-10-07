"""Upstream 0.8.5 must not silently widen or break the private public API."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from django_ledger.io import roles
from django_ledger.io.io_core import IODatabaseMixIn
from django_ledger.models.accounts import AccountModel
from django_ledger.models.entity import EntityModel
from django_ledger.routing import DJL_DB_ROUTING_CONTEXT, db_routing_action


class UpstreamRoleCompatibilityTest(SimpleTestCase):
    def test_regular_cost_alias_preserves_persisted_role(self):
        self.assertEqual(roles.COGS, 'cogs_regular')
        self.assertEqual(roles.COGS, roles.COGS_REGULAR)
        self.assertEqual(len(roles.GROUP_COGS), len(set(roles.GROUP_COGS)))

    def test_legacy_statement_groups_preserve_original_scope(self):
        self.assertEqual(roles.GROUP_IC_OPERATING_COGS, [roles.COGS_REGULAR])
        self.assertEqual(roles.GROUP_IC_OPERATING_REVENUES, [roles.INCOME_OPERATIONAL])
        self.assertEqual(roles.GROUP_IC_OTHER_REVENUES, roles.GROUP_INCOME_NON_OPERATING)
        self.assertEqual(roles.GROUP_IC_OPERATING_EXPENSES, [roles.EXPENSE_OPERATIONAL])
        self.assertEqual(roles.GROUP_IC_OTHER_EXPENSES, roles.GROUP_PNL_OTHER_EXPENSES)

    def test_legacy_equity_only_does_not_silently_widen_query(self):
        for keyword in ('equity_only', 'earnings_only'):
            with self.subTest(keyword=keyword):
                io = IODatabaseMixIn()
                with patch.object(io, 'database_digest', side_effect=RuntimeError('query boundary')) as query:
                    with self.assertRaisesRegex(RuntimeError, 'query boundary'):
                        io.python_digest(**{keyword: True})
                self.assertEqual(query.call_args.kwargs['role'], roles.GROUP_PNL_NET_PROFIT)

    def test_conflicting_filter_keywords_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            IODatabaseMixIn().python_digest(earnings_only=True, equity_only=False)

    def test_nested_routing_context_restores_on_exception(self):
        original = DJL_DB_ROUTING_CONTEXT.get()
        with db_routing_action('outer'):
            with self.assertRaisesRegex(RuntimeError, 'test'):
                with db_routing_action('inner'):
                    self.assertEqual(DJL_DB_ROUTING_CONTEXT.get(), 'inner')
                    raise RuntimeError('test')
            self.assertEqual(DJL_DB_ROUTING_CONTEXT.get(), 'outer')
        self.assertEqual(DJL_DB_ROUTING_CONTEXT.get(), original)


class UpstreamCoACompatibilityTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='upstream085')

    def setup_entity(self):
        entity = EntityModel.create_entity(
            name='Upstream Compatibility', admin=self.user, use_accrual_method=True, fy_start_month=1
        )
        coa = entity.create_chart_of_accounts(assign_as_default=True, commit=True)
        entity.populate_default_coa(activate_accounts=True)
        uom = entity.create_uom(name='Unit', unit_abbr='unit', commit=True)
        return entity, coa, uom

    def test_default_product_uses_regular_cost_with_multiple_cost_roles(self):
        entity, coa, uom = self.setup_entity()
        self.assertGreater(coa.get_coa_accounts().filter(role__in=roles.GROUP_COGS, role_default=True).count(), 1)
        item = entity.create_item_product(name='Product', item_type='M', uom_model=uom)
        self.assertEqual(item.cogs_account.role, roles.COGS_REGULAR)

    def test_default_service_uses_regular_cost_with_multiple_cost_roles(self):
        entity, _coa, uom = self.setup_entity()
        item = entity.create_item_service(name='Service', uom_model=uom)
        self.assertEqual(item.cogs_account.role, roles.COGS_REGULAR)

    def test_failed_configuration_rolls_back_roots_and_context(self):
        entity = EntityModel.create_entity(
            name='Atomic CoA', admin=self.user, use_accrual_method=True, fy_start_month=1
        )
        before = AccountModel.objects.count()
        original = DJL_DB_ROUTING_CONTEXT.get()
        with patch('treebeard.mp_tree.MP_NodeManager.add_child', side_effect=RuntimeError('child failure')):
            with self.assertRaisesRegex(RuntimeError, 'child failure'):
                entity.create_chart_of_accounts(assign_as_default=True, commit=True)
        self.assertEqual(AccountModel.objects.count(), before)
        self.assertEqual(DJL_DB_ROUTING_CONTEXT.get(), original)

    def test_new_no_return_path_still_creates_account(self):
        _entity, coa, _uom = self.setup_entity()
        result = coa.create_account(
            code='6999',
            name='Additional Expense',
            role=roles.EXPENSE_OTHER,
            balance_type='debit',
            active=True,
            return_account_model=False,
        )
        self.assertIsNone(result)
        self.assertTrue(coa.get_coa_accounts().filter(code='6999').exists())
