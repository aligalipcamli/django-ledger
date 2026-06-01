"""
Runtime-only tests for the CustomerModel Swapper integration.

These tests require django_ledger.tests.settings_swappable_customer so the
custom model is configured before Django's app registry is populated.
"""

import unittest

import swapper
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from django_ledger.models.customer import CustomerModel
from django_ledger.models.entity import EntityModel
from django_ledger.models.utils import lazy_loader


CUSTOM_CUSTOMER_SETTING = 'swappable_customer_app.CustomCustomerModel'


@unittest.skipUnless(
    getattr(settings, 'DJANGO_LEDGER_CUSTOMERMODEL_MODEL', None) == CUSTOM_CUSTOMER_SETTING,
    'requires django_ledger.tests.settings_swappable_customer',
)
class CustomerSwappableRuntimeAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.CustomCustomerModel = apps.get_model('swappable_customer_app', 'CustomCustomerModel')
        cls.admin_user = get_user_model().objects.create_user(
            username='api_swappable_customer_admin',
            email='api-swappable-customer-admin@example.com',
            password='NeverUseThisPassword12345',
        )

    def create_entity(self, name='API Swappable Customer Entity'):
        return EntityModel.create_entity(
            name=name,
            admin=self.admin_user,
            use_accrual_method=True,
            fy_start_month=1,
        )

    def create_customer(self, entity_model, *, name='API Swappable Customer', active=True):
        return entity_model.create_customer(
            {
                'customer_name': name,
                'description': f'{name} description',
                'active': active,
                'hidden': False,
            }
        )

    def test_runtime_loader_returns_custom_customer_model(self):
        self.assertIs(lazy_loader.get_customer_model(), self.CustomCustomerModel)
        self.assertIs(swapper.load_model('django_ledger', 'CustomerModel'), self.CustomCustomerModel)
        self.assertEqual(swapper.get_model_name('django_ledger', 'CustomerModel'), CUSTOM_CUSTOMER_SETTING)

    def test_runtime_default_customer_model_remains_importable_but_not_effective(self):
        self.assertEqual(CustomerModel._meta.label, 'django_ledger.CustomerModel')
        self.assertIsNot(CustomerModel, self.CustomCustomerModel)
        self.assertIs(lazy_loader.get_customer_model(), self.CustomCustomerModel)

    def test_runtime_entity_create_customer_uses_custom_customer_model(self):
        entity_model = self.create_entity()

        customer_model = self.create_customer(entity_model)

        self.assertIsInstance(customer_model, self.CustomCustomerModel)
        self.assertEqual(customer_model.entity_model_id, entity_model.uuid)
        self.assertEqual(customer_model.custom_marker, 'custom')
        self.assertTrue(customer_model.customer_number)

    def test_runtime_entity_get_customers_queries_custom_customer_model(self):
        entity_model = self.create_entity(name='API Swappable Customer Scoped Entity')
        other_entity_model = self.create_entity(name='API Other Swappable Customer Scoped Entity')
        active_customer = self.create_customer(entity_model, name='API Active Swappable Customer')
        inactive_customer = self.create_customer(
            entity_model,
            name='API Inactive Swappable Customer',
            active=False,
        )
        other_customer = self.create_customer(other_entity_model, name='API Other Swappable Customer')

        default_customer_qs = entity_model.get_customers()
        all_customer_qs = entity_model.get_customers(active=False)

        self.assertIs(default_customer_qs.model, self.CustomCustomerModel)
        self.assertIs(all_customer_qs.model, self.CustomCustomerModel)
        self.assertTrue(default_customer_qs.filter(uuid=active_customer.uuid).exists())
        self.assertFalse(default_customer_qs.filter(uuid=inactive_customer.uuid).exists())
        self.assertFalse(default_customer_qs.filter(uuid=other_customer.uuid).exists())
        self.assertTrue(all_customer_qs.filter(uuid=active_customer.uuid).exists())
        self.assertTrue(all_customer_qs.filter(uuid=inactive_customer.uuid).exists())
        self.assertFalse(all_customer_qs.filter(uuid=other_customer.uuid).exists())

    def test_runtime_customer_form_resolves_custom_customer_model(self):
        from django_ledger.forms.customer import CustomerModelForm

        self.assertIs(CustomerModelForm._meta.model, self.CustomCustomerModel)
