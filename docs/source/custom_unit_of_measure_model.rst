Custom Unit of Measure Model
============================

Django Ledger supports a Swapper-backed custom ``UnitOfMeasureModel`` for
projects that configure the custom model before running Django Ledger
migrations.

This support is intended for new projects, or for empty databases where the
custom unit of measure model is selected before the first ``migrate``. It is
not a generic late-swap mechanism for existing databases with built-in Django
Ledger unit of measure data.

Setting
-------

Configure the effective unit of measure model in your Django settings:

.. code-block:: python

    DJANGO_LEDGER_UNITOFMEASUREMODEL_MODEL = "myapp.MyUnitOfMeasureModel"

The setting must be present before Django loads the app registry and before
initial migrations are run.

Custom Model Shape
------------------

The recommended custom model inherits from
``django_ledger.models.items.UnitOfMeasureModelAbstract`` so it keeps Django
Ledger's expected fields, manager, queryset helpers, active flag, and entity
relationship.

For example:

.. code-block:: python

    from django.db import models

    from django_ledger.models.items import UnitOfMeasureModelAbstract


    class MyUnitOfMeasureModel(UnitOfMeasureModelAbstract):
        external_code = models.CharField(max_length=64, blank=True)

        class Meta(UnitOfMeasureModelAbstract.Meta):
            app_label = "myapp"

When the model is declared in ``myapp/models.py``, Django can usually infer the
app label. If the model lives outside the app's normal models module, declare
``app_label`` explicitly.

Custom implementations that do not inherit from
``UnitOfMeasureModelAbstract`` must preserve the unit of measure contract used
by Django Ledger. In practice that includes the entity relationship, name and
abbreviation fields, active flag, and manager/queryset methods such as
``for_entity()`` and ``for_entity_active()``.

What Is Covered
---------------

With the custom setting configured before initial migrations, Django Ledger
resolves the effective unit of measure model through Swapper. The supported
surfaces include:

* ``lazy_loader.get_uom_model()`` runtime resolution.
* ``EntityModel`` unit of measure helper methods such as create and list.
* Unit of measure forms when imported after the custom setting is configured.
* Item forms that list units of measure.
* ``ItemModel.uom``.

Migration Timing
----------------

Unit of measure model swapping is migration-sensitive. Configure
``DJANGO_LEDGER_UNITOFMEASUREMODEL_MODEL`` before the first ``migrate`` for a
new project.

Changing this setting after Django Ledger migrations have already run is not
supported automatically. Existing item foreign keys and existing unit of
measure rows are not copied or remapped by Django Ledger. A project that needs
to move from the built-in unit of measure table to a custom unit of measure
table must design and test its own data migration.

The migration history still creates Django Ledger's built-in unit of measure
table before a later migration retargets the item unit of measure foreign key
through Swapper. This keeps the forward migration path compatible, but it does
not mean an existing populated database can freely switch unit of measure
models.

Lemuur Unit Catalog
-------------------

For Lemuur, ``UnitOfMeasureModel`` swappability can support localized unit
labels, Turkish unit names, e-document unit codes, and Logo or e-Fatura unit
code mappings directly on the unit catalog row used by Django Ledger items.

Projects that do not need ``ItemModel.uom`` to point directly at a custom table
can still keep a separate sidecar/profile model related to the built-in unit of
measure model. Choose a custom ``UnitOfMeasureModel`` only when the project
needs the Django Ledger unit row itself to carry project-specific identity or
metadata from the first migration.

What Is Not Covered
-------------------

This feature does not provide:

* a generic data migration from built-in units of measure to a custom unit of
  measure table,
* safe late switching of ``DJANGO_LEDGER_UNITOFMEASUREMODEL_MODEL`` after
  migrations,
* swappable item, item transaction, bill, invoice, estimate, purchase order, or
  other commercial document models.

``UnitOfMeasureModel`` support is independent from ``CustomerModel``,
``VendorModel``, and ``BankAccountModel`` support. Enabling a custom unit of
measure model does not make item or document models swappable.
