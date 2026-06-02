Custom Vendor Model
===================

Django Ledger supports a Swapper-backed custom ``VendorModel`` for projects
that configure the custom model before running Django Ledger migrations.

This support is intended for new projects, or for empty databases where the
custom vendor model is selected before the first ``migrate``. It is not a
generic late-swap mechanism for existing databases with built-in Django Ledger
vendor data.

Setting
-------

Configure the effective vendor model in your Django settings:

.. code-block:: python

    DJANGO_LEDGER_VENDORMODEL_MODEL = "myapp.MyVendorModel"

The setting must be present before Django loads the app registry and before
initial migrations are run.

Custom Model Shape
------------------

The recommended custom model inherits from
``django_ledger.models.vendor.VendorModelAbstract`` so it keeps Django Ledger's
expected fields, manager, queryset helpers, numbering behavior, and entity
relationship.

For example:

.. code-block:: python

    from django.db import models

    from django_ledger.models.vendor import VendorModelAbstract


    class MyVendorModel(VendorModelAbstract):
        external_id = models.CharField(max_length=64, blank=True)

        class Meta(VendorModelAbstract.Meta):
            app_label = "myapp"

When the model is declared in ``myapp/models.py``, Django can usually infer the
app label. If the model lives outside the app's normal models module, declare
``app_label`` explicitly.

Custom implementations that do not inherit from ``VendorModelAbstract`` must
preserve the vendor contract used by Django Ledger. In practice that includes
the entity relationship, vendor number/name fields, active and hidden flags, and
manager/queryset methods such as ``for_entity()``, ``active()``, and
``visible()``.

What Is Covered
---------------

With the custom setting configured before initial migrations, Django Ledger
resolves the effective vendor model through Swapper. The supported surfaces
include:

* ``lazy_loader.get_vendor_model()`` runtime resolution.
* ``EntityModel`` vendor helper methods such as vendor create and list.
* Vendor forms when imported after the custom setting is configured.
* Bill and staged transaction forms that list vendors.
* ``BillModel.vendor``.
* ``ReceiptModel.vendor_model``.
* ``StagedTransactionModel.vendor_model``.

Migration Timing
----------------

Vendor model swapping is migration-sensitive. Configure
``DJANGO_LEDGER_VENDORMODEL_MODEL`` before the first ``migrate`` for a new
project.

Changing this setting after Django Ledger migrations have already run is not
supported automatically. Existing document foreign keys and existing vendor rows
are not copied or remapped by Django Ledger. A project that needs to move from
the built-in vendor table to a custom vendor table must design and test its own
data migration.

The migration history still creates Django Ledger's built-in vendor table
before a later migration retargets the document vendor foreign keys through
Swapper. This keeps the forward migration path compatible, but it does not mean
an existing populated database can freely switch vendor models.

What Is Not Covered
-------------------

This feature does not provide:

* a generic data migration from built-in vendors to a custom vendor table,
* safe late switching of ``DJANGO_LEDGER_VENDORMODEL_MODEL`` after migrations,
* swappable bills, purchase orders, receipts, import jobs, staged transactions,
  or other fixed commercial document models.

``VendorModel`` support is independent from ``CustomerModel``,
``BankAccountModel``, ``UnitOfMeasureModel``, ``ItemModel``, ``InvoiceModel``,
``EstimateModel``, and ``ItemTransactionModel`` support. Configure each custom
model explicitly before initial migrations.
