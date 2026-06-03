Custom Purchase Order Model
===========================

Django Ledger supports a Swapper-backed custom ``PurchaseOrderModel`` for
projects that configure the custom model before running Django Ledger
migrations.

This support is intended for new projects, or for empty databases where the
custom purchase order model is selected before the first ``migrate``. It is not
a generic late-swap mechanism for existing databases with built-in Django
Ledger purchase order data.

Setting
-------

Configure the effective purchase order model in your Django settings:

.. code-block:: python

    DJANGO_LEDGER_PURCHASEORDERMODEL_MODEL = "myapp.MyPurchaseOrderModel"

The setting must be present before Django loads the app registry and before
initial migrations are run.

Custom Model Shape
------------------

The recommended custom model inherits from
``django_ledger.models.purchase_order.PurchaseOrderModelAbstract`` so it keeps
Django Ledger's expected purchase order fields, manager, queryset helpers,
itemization behavior, estimate binding, numbering behavior, lifecycle
transitions, receiving behavior, PO-to-Bill lookup behavior, and validation
hooks.

For example:

.. code-block:: python

    from django.db import models

    from django_ledger.models.purchase_order import PurchaseOrderModelAbstract


    class MyPurchaseOrderModel(PurchaseOrderModelAbstract):
        supplier_order_ref = models.CharField(max_length=64, blank=True)
        expected_delivery_date = models.DateField(null=True, blank=True)

        class Meta(PurchaseOrderModelAbstract.Meta):
            app_label = "myapp"

When the model is declared in ``myapp/models.py``, Django can usually infer the
app label. If the model lives outside the app's normal models module, declare
``app_label`` explicitly.

Avoid inheriting from the concrete
``django_ledger.models.purchase_order.PurchaseOrderModel`` when the goal is to
avoid extra joins. Django concrete model inheritance uses multi-table
inheritance and keeps a parent purchase order table join.

Custom implementations that do not inherit from
``PurchaseOrderModelAbstract`` must preserve the purchase order contract used
by Django Ledger. In practice that includes the entity, estimate, itemization,
numbering, amount, date, status, receiving, manager, and queryset behavior
expected by the built-in purchase order workflows.

What Is Covered
---------------

With the custom setting configured before initial migrations, Django Ledger
resolves the effective purchase order model through Swapper. The supported
surfaces include:

* ``lazy_loader.get_purchase_order_model()`` runtime resolution.
* ``EntityModel`` purchase order helper methods such as create and list.
* Purchase order forms and views when imported after the custom setting is
  configured.
* ``ItemTransactionModel.po_model``.
* ``PurchaseOrderModel.po_items`` through the effective item transaction model.
* Purchase order numbering for the effective purchase order model.
* Purchase order itemization, review, approval, receiving, and PO-to-Bill smoke
  paths.

If no custom item transaction model is configured, purchase order itemization
uses the built-in ``ItemTransactionModel``. Projects that also configure
``DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL`` before initial migrations can use
a custom line-item table with a custom purchase order table.

``EstimateModel``, ``BillModel``, and ``ReceiptModel`` may also be custom
models when their own settings are configured before initial migrations.

``ImportJobModel`` and ``StagedTransactionModel`` remain fixed Django Ledger
models.

Migration Timing
----------------

Purchase order model swapping is migration-sensitive. Configure
``DJANGO_LEDGER_PURCHASEORDERMODEL_MODEL`` before the first ``migrate`` for a
new project.

Changing this setting after Django Ledger migrations have already run is not
supported automatically. Existing purchase orders, item transactions, bills,
estimate links, inventory state, and document relationships are not copied or
remapped by Django Ledger. A project that needs to move from the built-in
purchase order table to a custom purchase order table must design and test its
own data migration.

The migration history still creates Django Ledger's built-in purchase order
table before a later migration retargets ``ItemTransactionModel.po_model``
through Swapper. This keeps the forward migration path compatible, but it does
not mean an existing populated database can freely switch purchase order
models.

Lemuur Purchase Orders
----------------------

For Lemuur, ``PurchaseOrderModel`` swappability can support a custom supplier
order or procurement header row. Supplier order references, procurement status,
approval metadata, expected delivery dates, shipping or receiving metadata,
warehouse hints, supplier snapshots, and compact external document references
may fit naturally on a custom purchase order model.

Approval workflow events, receiving event history, line-level tax breakdowns,
integration payloads, integration responses, retry history, and procurement
automation should usually live on sidecar/profile models or project services.
Those values can be repeated, large, workflow-specific, or better modeled as
child records.

Unsupported
-----------

Django Ledger does not provide:

* safe late switching of ``DJANGO_LEDGER_PURCHASEORDERMODEL_MODEL`` after
  migrations,
* automatic migration from built-in purchase order rows to custom purchase
  order rows,
* custom receipt, import job, or staged transaction model swapping through this
  setting,
* tax, e-document, or procurement automation logic inside Django Ledger.
