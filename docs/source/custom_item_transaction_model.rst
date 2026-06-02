Custom Item Transaction Model
=============================

Django Ledger supports a Swapper-backed custom ``ItemTransactionModel`` for
projects that configure the custom model before running Django Ledger
migrations.

This support is intended for new projects, or for empty databases where the
custom line-item model is selected before the first ``migrate``. It is not a
generic late-swap mechanism for existing databases with built-in Django Ledger
line-item data.

Setting
-------

Configure the effective item transaction model in your Django settings:

.. code-block:: python

    DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL = "myapp.MyItemTransactionModel"

The setting must be present before Django loads the app registry and before
initial migrations are run.

Custom Model Shape
------------------

The recommended custom model inherits from
``django_ledger.models.items.ItemTransactionModelAbstract`` so it keeps Django
Ledger's expected line fields, manager, queryset helpers, document
relationships, item relationship, purchase-order status fields, estimate
fields, amount calculation hooks, and validation behavior.

For example:

.. code-block:: python

    from django.db import models

    from django_ledger.models.items import ItemTransactionModelAbstract


    class MyItemTransactionModel(ItemTransactionModelAbstract):
        tax_total = models.DecimalField(max_digits=20, decimal_places=2, default=0)
        external_line_id = models.CharField(max_length=64, blank=True)

        class Meta(ItemTransactionModelAbstract.Meta):
            app_label = "myapp"

When the model is declared in ``myapp/models.py``, Django can usually infer the
app label. If the model lives outside the app's normal models module, declare
``app_label`` explicitly.

Custom implementations that do not inherit from
``ItemTransactionModelAbstract`` must preserve the item transaction contract
used by Django Ledger. In practice that includes the item foreign key, bill,
invoice, estimate, and purchase order foreign keys, entity unit foreign key,
quantity and amount fields, purchase order status fields, manager/queryset
methods, and calculation helpers used by itemized document workflows.

What Is Covered
---------------

With the custom setting configured before initial migrations, Django Ledger
resolves the effective line-item model through Swapper. The supported surfaces
include:

* ``lazy_loader.get_item_transaction_model()`` runtime resolution.
* Item transaction forms and formsets when imported after the custom setting is
  configured.
* Itemized document runtime helpers that create, query, aggregate, and update
  line items.
* ``BillModel.bill_items`` through the effective item transaction model.
* ``InvoiceModel.invoice_items`` through the effective item transaction model.
* ``PurchaseOrderModel.po_items`` through the effective item transaction model.
* The item transaction ``item_model`` and ``invoice_model`` relationships,
  which continue to resolve to the effective ``ItemModel`` and ``InvoiceModel``.

``EstimateModel`` itemization uses ``ItemTransactionModel.ce_model`` and does
not declare a direct many-to-many field to ``ItemModel``.

Migration Timing
----------------

Item transaction swapping is migration-sensitive. Configure
``DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL`` before the first ``migrate`` for a
new project.

Changing this setting after Django Ledger migrations have already run is not
supported automatically. Existing document item relationships and line rows are
not copied or remapped by Django Ledger. A project that needs to move from the
built-in line-item table to a custom line-item table must design and test its
own data migration.

The migration history still creates Django Ledger's built-in item transaction
table before a later migration retargets document item many-to-many fields
through Swapper. This keeps the forward migration path compatible, but it does
not mean an existing populated database can freely switch line-item models.

Combining Custom Models
-----------------------

``ItemTransactionModel`` support can be combined with custom
``UnitOfMeasureModel``, ``ItemModel``, ``InvoiceModel``, and ``EstimateModel``
settings when all settings are configured before initial migrations. The custom
item transaction model should keep foreign keys aligned with the effective item,
invoice, and estimate models by inheriting from ``ItemTransactionModelAbstract``
or by using equivalent Swapper-aware relationships.

Bill, purchase order, and receipt models remain fixed Django Ledger models in
this support slice.

Lemuur Line Items
-----------------

For Lemuur, ``ItemTransactionModel`` swappability can support transaction-level
line fields such as tax totals, tax-included pricing snapshots, discount
snapshots, exemption metadata, e-document line identifiers, and integration
status flags.

Detailed tax breakdown tables, withholding breakdowns, integration payloads,
retry history, and full e-document events should usually live on sidecar or
profile models. Those values can be repeated, large, workflow-specific, or
better modeled as child records.

Tax and e-document calculation policy belongs in project services. Django
Ledger's custom item transaction support only changes the effective line-item
model; it does not add Turkish tax, withholding, discount, or e-document
calculation logic.

What Is Not Covered
-------------------

This feature does not provide:

* a generic data migration from built-in line items to a custom line-item table,
* safe late switching of ``DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL`` after
  migrations,
* swappable bills, purchase orders, receipts, accounts, entities, ledgers,
  journal entries, or other core ledger models,
* built-in tax, discount, withholding, or e-document calculation.

``ItemTransactionModel`` support is independent from ``CustomerModel``,
``VendorModel``, ``BankAccountModel``, ``UnitOfMeasureModel``, ``ItemModel``,
``InvoiceModel``, and ``EstimateModel`` support. Configure each custom model
explicitly before initial migrations.
