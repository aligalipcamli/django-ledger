Custom Item Model
=================

Django Ledger supports a Swapper-backed custom ``ItemModel`` for projects that
configure the custom model before running Django Ledger migrations.

This support is intended for new projects, or for empty databases where the
custom item model is selected before the first ``migrate``. It is not a generic
late-swap mechanism for existing databases with built-in Django Ledger item
data.

Setting
-------

Configure the effective item model in your Django settings:

.. code-block:: python

    DJANGO_LEDGER_ITEMMODEL_MODEL = "myapp.MyItemModel"

The setting must be present before Django loads the app registry and before
initial migrations are run.

Custom Model Shape
------------------

The recommended custom model inherits from
``django_ledger.models.items.ItemModelAbstract`` so it keeps Django Ledger's
expected catalog fields, manager, queryset helpers, numbering behavior, unit of
measure relationship, entity relationship, account role mappings, inventory
fields, and validation hooks.

For example:

.. code-block:: python

    from django.db import models

    from django_ledger.models.items import ItemModelAbstract


    class MyItemModel(ItemModelAbstract):
        external_code = models.CharField(max_length=64, blank=True)

        class Meta(ItemModelAbstract.Meta):
            app_label = "myapp"

When the model is declared in ``myapp/models.py``, Django can usually infer the
app label. If the model lives outside the app's normal models module, declare
``app_label`` explicitly.

Custom implementations that do not inherit from ``ItemModelAbstract`` must
preserve the item contract used by Django Ledger. In practice that includes the
entity and unit of measure relationships, item role/type fields, item numbering,
active flag, default amount, account relationships, inventory fields, and
manager/queryset methods such as ``for_entity()``, ``for_bill()``,
``for_invoice()``, ``for_estimate()``, and ``for_po()``.

What Is Covered
---------------

With the custom setting configured before initial migrations, Django Ledger
resolves the effective item model through Swapper. The supported surfaces
include:

* ``lazy_loader.get_item_model()`` runtime resolution.
* ``EntityModel`` item helper methods such as create and list.
* Item forms and item views when imported after the custom setting is
  configured.
* Itemization querysets for bills, invoices, estimates, and purchase orders.
* ``ItemTransactionModel.item_model``.
* ``BillModel.bill_items``.
* ``InvoiceModel.invoice_items``.
* ``PurchaseOrderModel.po_items``.

``EstimateModel`` itemization uses ``ItemTransactionModel.ce_model`` and does
not declare a direct many-to-many field to ``ItemModel``.

Migration Timing
----------------

Item model swapping is migration-sensitive. Configure
``DJANGO_LEDGER_ITEMMODEL_MODEL`` before the first ``migrate`` for a new
project.

Changing this setting after Django Ledger migrations have already run is not
supported automatically. Existing item transaction foreign keys, document item
relationships, and existing item rows are not copied or remapped by Django
Ledger. A project that needs to move from the built-in item table to a custom
item table must design and test its own data migration.

The migration history still creates Django Ledger's built-in item table before
a later migration retargets item transaction and document item relationships
through Swapper. This keeps the forward migration path compatible, but it does
not mean an existing populated database can freely switch item models.

Unit of Measure Dependency
--------------------------

``ItemModel.uom`` resolves through the configured ``UnitOfMeasureModel``. A
project may use the built-in unit of measure model or a custom unit of measure
model, but both model settings must be configured before initial migrations.

Lemuur Product Catalog
----------------------

For Lemuur, ``ItemModel`` swappability can support a custom catalog row for
products, services, and işletme kalemleri. Stable catalog identity, default
account mappings, default unit metadata, default tax category references, and
Logo or e-Fatura/e-Arşiv item codes may fit naturally on a custom item model.

Document-specific tax, discount, tax-included pricing, exemption, withholding,
or e-document details usually belong on sidecar/profile models or on document
line data. Those values can vary by transaction, customer, date, and document
type, so storing them directly on the item catalog row can overstate the
catalog model's responsibility.

What Is Not Covered
-------------------

This feature does not provide:

* a generic data migration from built-in items to a custom item table,
* safe late switching of ``DJANGO_LEDGER_ITEMMODEL_MODEL`` after migrations,
* swappable purchase order, receipt, account, entity, or other models through
  this setting.

``ItemModel`` support is independent from ``CustomerModel``, ``VendorModel``,
``BankAccountModel``, ``UnitOfMeasureModel``, ``InvoiceModel``,
``BillModel``, ``EstimateModel``, ``ItemTransactionModel``,
``PurchaseOrderModel``, and ``ReceiptModel`` support. Configure a custom item
transaction model explicitly if line-item rows also need a custom table.
