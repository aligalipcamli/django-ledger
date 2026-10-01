"""
High-level API behavior tests for EntityModel creation and user scoping.

These tests document deterministic entity creation, slug, accounting method,
and access-scope behavior without requiring accounting fixtures.
"""

import re
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from django_ledger.models.entity import (
    EntityManagementModel,
    EntityModel,
    EntityModelValidationError,
)


class EntityCreationAPITest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.admin_user = user_model.objects.create_user(
            username="api_entity_creation_admin",
            email="api-entity-creation-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.other_admin_user = user_model.objects.create_user(
            username="api_entity_creation_other_admin",
            email="api-entity-creation-other-admin@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.manager_user = user_model.objects.create_user(
            username="api_entity_creation_manager",
            email="api-entity-creation-manager@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.unrelated_user = user_model.objects.create_user(
            username="api_entity_creation_unrelated",
            email="api-entity-creation-unrelated@example.com",
            password="NeverUseThisPassword12345",
        )
        cls.superuser = user_model.objects.create_superuser(
            username="api_entity_creation_superuser",
            email="api-entity-creation-superuser@example.com",
            password="NeverUseThisPassword12345",
        )

    def create_entity(
        self,
        *,
        name="API Entity Creation Entity",
        admin=None,
        use_accrual_method=True,
        fy_start_month=1,
        parent_entity=None,
    ):
        return EntityModel.create_entity(
            name=name,
            admin=admin or self.admin_user,
            use_accrual_method=use_accrual_method,
            fy_start_month=fy_start_month,
            parent_entity=parent_entity,
        )

    def assert_is_slug_with_random_suffix(self, slug, base_slug):
        self.assertRegex(slug, rf"^{re.escape(base_slug)}-[a-z0-9]{{8}}$")

    def assert_entity_is_child_of_parent(self, child_entity, parent_entity):
        child_entity.refresh_from_db()
        parent_entity.refresh_from_db()

        self.assertFalse(child_entity.is_root())
        self.assertTrue(child_entity.is_child_of(parent_entity))
        self.assertEqual(EntityModel.objects.get_parent(child_entity).uuid, parent_entity.uuid)

    def test_create_root_entity_assigns_public_fields_and_tree_root(self):
        entity_model = self.create_entity(
            name="API Root Entity",
            use_accrual_method=True,
            fy_start_month=4,
        )

        self.assertIsNotNone(entity_model.uuid)
        self.assertEqual(entity_model.name, "API Root Entity")
        self.assertEqual(entity_model.admin_id, self.admin_user.id)
        self.assertEqual(entity_model.fy_start_month, 4)
        self.assertTrue(entity_model.accrual_method)
        self.assert_is_slug_with_random_suffix(entity_model.slug, "api-root-entity")

        self.assertTrue(entity_model.is_root())
        self.assertEqual(entity_model.depth, 1)

    def test_accrual_and_cash_method_helpers_reflect_entity_setting(self):
        accrual_entity = self.create_entity(
            name="API Accrual Entity",
            use_accrual_method=True,
        )
        cash_entity = self.create_entity(
            name="API Cash Entity",
            use_accrual_method=False,
        )

        self.assertTrue(accrual_entity.is_accrual_method())
        self.assertFalse(accrual_entity.is_cash_method())
        self.assertEqual(accrual_entity.get_accrual_method(), EntityModel.ACCRUAL_METHOD)

        self.assertTrue(cash_entity.is_cash_method())
        self.assertFalse(cash_entity.is_accrual_method())
        self.assertEqual(cash_entity.get_accrual_method(), EntityModel.CASH_METHOD)

    def test_create_child_entity_accepts_parent_model_instance(self):
        parent_entity = self.create_entity(name="API Parent Model Entity")

        child_entity = self.create_entity(
            name="API Child From Parent Model Entity",
            parent_entity=parent_entity,
        )

        self.assert_entity_is_child_of_parent(child_entity, parent_entity)

    def test_create_child_entity_accepts_parent_slug(self):
        parent_entity = self.create_entity(name="API Parent Slug Entity")

        child_entity = self.create_entity(
            name="API Child From Parent Slug Entity",
            parent_entity=parent_entity.slug,
        )

        self.assert_entity_is_child_of_parent(child_entity, parent_entity)

    def test_create_child_entity_accepts_parent_uuid(self):
        parent_entity = self.create_entity(name="API Parent UUID Entity")

        child_entity = self.create_entity(
            name="API Child From Parent UUID Entity",
            parent_entity=parent_entity.uuid,
        )

        self.assert_entity_is_child_of_parent(child_entity, parent_entity)

    def test_create_child_entity_rejects_parent_administered_by_other_user_without_side_effect(self):
        parent_entity = self.create_entity(
            name="API Other Admin Parent Entity",
            admin=self.other_admin_user,
        )

        with self.assertRaises(EntityModelValidationError):
            self.create_entity(
                name="API Rejected Other Admin Child Entity",
                parent_entity=parent_entity,
            )

        self.assertFalse(
            EntityModel.objects.filter(name="API Rejected Other Admin Child Entity").exists()
        )

    def test_create_child_entity_rejects_invalid_parent_type_without_side_effect(self):
        with self.assertRaises(EntityModelValidationError):
            self.create_entity(
                name="API Invalid Parent Type Child Entity",
                parent_entity=object(),
            )

        self.assertFalse(
            EntityModel.objects.filter(name="API Invalid Parent Type Child Entity").exists()
        )

    def test_for_user_includes_admin_and_manager_entities_only(self):
        entity_model = self.create_entity(name="API Scoped Entity")
        other_entity = self.create_entity(
            name="API Other Scoped Entity",
            admin=self.other_admin_user,
        )

        EntityManagementModel.objects.create(
            entity=entity_model,
            user=self.manager_user,
            permission_level="read",
        )

        admin_qs = EntityModel.objects.for_user(self.admin_user)
        manager_qs = EntityModel.objects.for_user(self.manager_user)
        unrelated_qs = EntityModel.objects.for_user(self.unrelated_user)

        self.assertTrue(admin_qs.filter(uuid=entity_model.uuid).exists())
        self.assertFalse(admin_qs.filter(uuid=other_entity.uuid).exists())

        self.assertTrue(manager_qs.filter(uuid=entity_model.uuid).exists())
        self.assertFalse(manager_qs.filter(uuid=other_entity.uuid).exists())

        self.assertFalse(unrelated_qs.filter(uuid=entity_model.uuid).exists())
        self.assertFalse(unrelated_qs.filter(uuid=other_entity.uuid).exists())

    def test_for_user_authorized_superuser_can_see_all_entities(self):
        entity_model = self.create_entity(name="API Superuser Entity")
        other_entity = self.create_entity(
            name="API Other Superuser Entity",
            admin=self.other_admin_user,
        )

        default_superuser_qs = EntityModel.objects.for_user(self.superuser)
        authorized_superuser_qs = EntityModel.objects.for_user(
            self.superuser,
            authorized_superuser=True,
        )

        self.assertFalse(default_superuser_qs.filter(uuid=entity_model.uuid).exists())
        self.assertFalse(default_superuser_qs.filter(uuid=other_entity.uuid).exists())

        self.assertTrue(authorized_superuser_qs.filter(uuid=entity_model.uuid).exists())
        self.assertTrue(authorized_superuser_qs.filter(uuid=other_entity.uuid).exists())

    def test_generate_slug_from_name_slugifies_name_and_adds_suffix(self):
        slug = EntityModel.generate_slug_from_name("API Slug Contract Entity")

        self.assert_is_slug_with_random_suffix(slug, "api-slug-contract-entity")

    def test_generated_slug_respects_field_limits_without_shortening_suffix(self):
        for name, base in (
            ("A" * 41, "a" * 41),
            ("A" * 42, "a" * 41),
            ("A" * 150, "a" * 41),
            ("A" * 40 + " B", "a" * 40),
            ("İstanbul Şişli", "istanbul-sisli"),
            ("東京家具工房", "entity"),
            ("---", "entity"),
            ("", "entity"),
            ("A", "a"),
        ):
            with self.subTest(name=name):
                with patch("django_ledger.models.entity.choices", return_value=list("12345678")):
                    slug = EntityModel.generate_slug_from_name(name)
                self.assertEqual(slug, base + "-12345678")
                EntityModel._meta.get_field("slug").clean(slug, None)

    def test_long_named_root_and_child_keep_names_and_valid_tree(self):
        name = "A" * EntityModel._meta.get_field("name").max_length
        parent = self.create_entity(name=name)
        child = self.create_entity(name=name, parent_entity=parent)
        self.assert_entity_is_child_of_parent(child, parent)
        self.assertEqual(parent.name, name)
        self.assertEqual(child.name, name)
        self.assertNotEqual(parent.slug, child.slug)
        self.assertEqual(len(parent.slug), 50)
        self.assertEqual(len(child.slug), 50)

    def test_unchanged_short_slug_contract_and_existing_slug_survive_save(self):
        with patch("django_ledger.models.entity.choices", return_value=list("12345678")):
            entity = self.create_entity(name="Ada Studio")
        self.assertEqual(entity.slug, "ada-studio-12345678")
        entity.name = "A" * 150
        entity.save(update_fields=["name"])
        entity.refresh_from_db()
        self.assertEqual(entity.slug, "ada-studio-12345678")

    def test_generate_slug_refuses_existing_slug_unless_forced(self):
        entity_model = self.create_entity(name="API Force Slug Entity")
        original_slug = entity_model.slug

        with self.assertRaises(ValidationError):
            entity_model.generate_slug()

        self.assertEqual(entity_model.slug, original_slug)

        forced_slug = entity_model.generate_slug(force_update=True)

        self.assertEqual(entity_model.slug, forced_slug)
        self.assert_is_slug_with_random_suffix(forced_slug, "api-force-slug-entity")
