"""Resolve model annotations without adding eager runtime model imports.

These are typing-only bindings. Runtime introspection supplies the declared
typing namespace explicitly; get_type_hints without that namespace is not a
newly promised public API. Runtime model selection stays with lazy_loader.
"""

import ast
import importlib
import inspect
from typing import get_type_hints
from uuid import UUID

from django.test import SimpleTestCase

from django_ledger.models import accounts, unit
from django_ledger.models.chart_of_accounts import ChartOfAccountModel
from django_ledger.models.entity import EntityModel


class ModelTypingContractTest(SimpleTestCase):
    def typing_namespace(self, module, expected):
        tree = ast.parse(inspect.getsource(module))
        guards = [
            node
            for node in tree.body
            if isinstance(node, ast.If) and isinstance(node.test, ast.Name) and node.test.id == 'TYPE_CHECKING'
        ]
        self.assertEqual(len(guards), 1, 'Model typing imports need one explicit guard')
        namespace = {}
        for node in guards[0].body:
            self.assertIsInstance(node, ast.ImportFrom)
            self.assertEqual(node.level, 0)
            imported = importlib.import_module(node.module)
            for alias in node.names:
                namespace[alias.asname or alias.name] = getattr(imported, alias.name)
        self.assertEqual(namespace, expected)
        return namespace

    def test_account_entity_and_coa_annotations_resolve(self):
        namespace = self.typing_namespace(
            accounts,
            {
                'EntityModel': EntityModel,
                'ChartOfAccountModel': ChartOfAccountModel,
            },
        )
        method = inspect.unwrap(accounts.AccountModelManager.for_entity)
        hints = get_type_hints(method, globalns=vars(accounts), localns=namespace)
        self.assertEqual(hints['entity_model'], EntityModel | str | UUID)
        self.assertEqual(hints['coa_model'], ChartOfAccountModel | str | UUID | None)
        self.assertIs(hints['return'], accounts.AccountModelQuerySet)
        self.assertIsNone(inspect.signature(method).parameters['entity_model'].default)
        self.assertIsNone(inspect.signature(method).parameters['coa_model'].default)

    def test_unit_manager_annotation_resolves(self):
        namespace = self.typing_namespace(unit, {'EntityModel': EntityModel})
        method = inspect.unwrap(unit.EntityUnitModelManager.for_entity)
        hints = get_type_hints(method, globalns=vars(unit), localns=namespace)
        self.assertEqual(hints['entity_model'], EntityModel | str | UUID)
        self.assertIsNone(inspect.signature(method).parameters['entity_model'].default)

    def test_unit_validation_annotation_resolves(self):
        namespace = self.typing_namespace(unit, {'EntityModel': EntityModel})
        hints = get_type_hints(
            unit.EntityUnitModelAbstract.validate_for_entity,
            globalns=vars(unit),
            localns=namespace,
        )
        self.assertEqual(hints['entity_model'], EntityModel | str | UUID)

    def test_model_types_do_not_become_eager_module_bindings(self):
        for module, names in (
            (accounts, ('EntityModel', 'ChartOfAccountModel')),
            (unit, ('EntityModel',)),
        ):
            with self.subTest(module=module.__name__):
                for name in names:
                    self.assertNotIn(name, vars(module))
                self.assertIs(module.lazy_loader.get_entity_model(), EntityModel)
        self.assertIs(accounts.lazy_loader.get_coa_model(), ChartOfAccountModel)
