Custom Receipt Model
====================

Django Ledger supports a Swapper-backed custom ``ReceiptModel`` for projects
that configure the custom model before running Django Ledger migrations.

This support is intended for new projects, or for empty databases where the
custom receipt model is selected before the first ``migrate``. It is not a
generic late-swap mechanism for existing databases with built-in Django Ledger
receipt data.

Setting
-------

Configure the effective receipt model in your Django settings:

.. code-block:: python

    DJANGO_LEDGER_RECEIPTMODEL_MODEL = "myapp.MyReceiptModel"

The setting must be present before Django loads the app registry and before
initial migrations are run.

Custom Model Shape
------------------

The recommended custom model inherits from
``django_ledger.models.receipt.ReceiptModelAbstract`` so it keeps Django
Ledger's expected receipt fields, manager, queryset helpers, ledger
relationship, customer and vendor relationships, staged transaction link,
numbering behavior, posting behavior, and validation hooks.

For example:

.. code-block:: python

    from django.db import models

    from django_ledger.models.receipt import ReceiptModelAbstract


    class MyReceiptModel(ReceiptModelAbstract):
        external_receipt_id = models.CharField(max_length=64, blank=True)
        payment_channel = models.CharField(max_length=32, blank=True)

        class Meta(ReceiptModelAbstract.Meta):
            app_label = "myapp"

When the model is declared in ``myapp/models.py``, Django can usually infer the
app label. If the model lives outside the app's normal models module, declare
``app_label`` explicitly.

Avoid inheriting from the concrete ``django_ledger.models.receipt.ReceiptModel``
when the goal is to avoid extra joins. Django concrete model inheritance uses
multi-table inheritance and keeps a parent receipt table join.

Custom implementations that do not inherit from ``ReceiptModelAbstract`` must
preserve the receipt contract used by Django Ledger. In practice that includes
the ledger, customer, vendor, unit, charge account, receipt account, staged
transaction, amount, date, type, numbering, posting, manager, and queryset
behavior expected by the built-in receipt workflows.

What Is Covered
---------------

With the custom setting configured before initial migrations, Django Ledger
resolves the effective receipt model through Swapper. The supported surfaces
include:

* ``lazy_loader.get_receipt_model()`` runtime resolution.
* ``EntityModel`` receipt helper methods such as list/query helpers.
* Customer and vendor receipt query paths.
* ``StagedTransactionModel.generate_receipt_model()`` and
  ``StagedTransactionModel.migrate_receipt()`` creating the effective receipt
  model.
* ``ReceiptModel.customer_model`` and ``ReceiptModel.vendor_model`` through the
  effective customer and vendor models.
* The fixed ``StagedTransactionModel`` link using the stable
  ``receiptmodel`` reverse accessor and query name.
* Receipt numbering, persistence, and ledger posting for the effective receipt
  model.

``ImportJobModel`` and ``StagedTransactionModel`` remain fixed Django Ledger
models. Receipt swapping changes the receipt header table only.

Migration Timing
----------------

Receipt model swapping is migration-sensitive. Configure
``DJANGO_LEDGER_RECEIPTMODEL_MODEL`` before the first ``migrate`` for a new
project.

Changing this setting after Django Ledger migrations have already run is not
supported automatically. Existing receipts, ledgers, staged transaction links,
and document relationships are not copied or remapped by Django Ledger. A
project that needs to move from the built-in receipt table to a custom receipt
table must design and test its own data migration.

The migration history still creates Django Ledger's built-in receipt table
before a later migration marks receipt swappability and preserves the staged
transaction reverse path. This keeps the forward migration path compatible, but
it does not mean an existing populated database can freely switch receipt
models.

Lemuur Receipts
---------------

For Lemuur, ``ReceiptModel`` swappability can support a custom receipt header
row for payment-channel metadata, external payment references, tax or fiscal
receipt identifiers, bank import snapshots, and compact integration status
fields.

Bank provider imports, POS integrations, reconciliation logic, detailed event
history, and retry payloads should usually live in project services or sidecar
models. Django Ledger's custom receipt support only changes the effective
receipt model; it does not add bank, POS, provider, or reconciliation behavior.

What Is Not Covered
-------------------

This feature does not provide:

* a generic data migration from built-in receipts to a custom receipt table,
* safe late switching of ``DJANGO_LEDGER_RECEIPTMODEL_MODEL`` after migrations,
* swappable import job or staged transaction models,
* bank provider, POS, reconciliation, tax, or e-document automation logic.

``ReceiptModel`` support is independent from ``CustomerModel``,
``VendorModel``, ``BankAccountModel``, ``UnitOfMeasureModel``, ``ItemModel``,
``InvoiceModel``, ``BillModel``, ``EstimateModel``,
``ItemTransactionModel``, and ``PurchaseOrderModel`` support. Configure each
custom model explicitly before initial migrations.
