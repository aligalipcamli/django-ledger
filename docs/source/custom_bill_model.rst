Custom Bill Model
=================

Django Ledger supports a Swapper-backed custom ``BillModel`` for projects that
configure the custom model before running Django Ledger migrations.

This support is intended for new projects, or for empty databases where the
custom bill model is selected before the first ``migrate``. It is not a generic
late-swap mechanism for existing databases with built-in Django Ledger bill
data.

Setting
-------

Configure the effective bill model in your Django settings:

.. code-block:: python

    DJANGO_LEDGER_BILLMODEL_MODEL = "myapp.MyBillModel"

The setting must be present before Django loads the app registry and before
initial migrations are run.

Custom Model Shape
------------------

The recommended custom model inherits from
``django_ledger.models.bill.BillModelAbstract`` so it keeps Django Ledger's
expected bill fields, manager, queryset helpers, ledger relationship, vendor
relationship, payment terms, itemization behavior, numbering behavior,
lifecycle transitions, payment behavior, and validation hooks.

For example:

.. code-block:: python

    from django.db import models

    from django_ledger.models.bill import BillModelAbstract


    class MyBillModel(BillModelAbstract):
        supplier_document_ref = models.CharField(max_length=64, blank=True)
        purchase_document_type = models.CharField(max_length=32, blank=True)

        class Meta(BillModelAbstract.Meta):
            app_label = "myapp"

When the model is declared in ``myapp/models.py``, Django can usually infer the
app label. If the model lives outside the app's normal models module, declare
``app_label`` explicitly.

Avoid inheriting from the concrete ``django_ledger.models.bill.BillModel`` when
the goal is to avoid extra joins. Django concrete model inheritance uses
multi-table inheritance and keeps a parent bill table join.

Custom implementations that do not inherit from ``BillModelAbstract`` must
preserve the bill contract used by Django Ledger. In practice that includes the
ledger, entity, vendor, terms, account, amount, date, status, estimate,
itemization, numbering, payment, lifecycle, manager, and queryset behavior
expected by the built-in bill workflows.

What Is Covered
---------------

With the custom setting configured before initial migrations, Django Ledger
resolves the effective bill model through Swapper. The supported surfaces
include:

* ``lazy_loader.get_bill_model()`` runtime resolution.
* ``EntityModel`` bill helper methods such as create and list.
* Bill forms and bill views when imported after the custom setting is
  configured.
* ``ItemTransactionModel.bill_model``.
* ``BillModel.bill_items`` through the effective ``ItemTransactionModel``.
* Bill numbering and entity assignment for the effective bill model.
* Bill itemization, approval, payment, and ledger wrapper smoke paths.

If no custom item transaction model is configured, bill itemization uses the
built-in ``ItemTransactionModel``. Projects that also configure
``DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL`` before initial migrations can use a
custom line-item table with a custom bill table.

``VendorModel`` and ``EstimateModel`` may also be custom models when their own
settings are configured before initial migrations.

Migration Timing
----------------

Bill model swapping is migration-sensitive. Configure
``DJANGO_LEDGER_BILLMODEL_MODEL`` before the first ``migrate`` for a new
project.

Changing this setting after Django Ledger migrations have already run is not
supported automatically. Existing bills, ledgers, item transactions, purchase
order line links, and document relationships are not copied or remapped by
Django Ledger. A project that needs to move from the built-in bill table to a
custom bill table must design and test its own data migration.

The migration history still creates Django Ledger's built-in bill table before
a later migration retargets ``ItemTransactionModel.bill_model`` through
Swapper. This keeps the forward migration path compatible, but it does not mean
an existing populated database can freely switch bill models.

Lemuur Purchase Documents
-------------------------

For Lemuur, ``BillModel`` swappability can support a custom purchase invoice or
expense bill header row. Supplier document references, purchase document type,
supplier tax-number snapshots, supplier title snapshots, address snapshots,
input VAT totals, withholding totals, discount totals, grand totals, payable
classification, and compact integration status fields may fit naturally on a
custom bill model.

Line-level tax breakdowns, withholding details, integration payloads,
integration responses, retry history, approval workflow events, and full
e-document event logs should usually live on sidecar/profile models or project
services. Those values can be repeated, large, workflow-specific, or better
modeled as child records.

Tax and e-document calculation policy belongs in project services. Django
Ledger's custom bill support only changes the effective bill header model; it
does not add Turkish tax, withholding, or e-document calculation logic.

What Is Not Covered
-------------------

This feature does not provide:

* a generic data migration from built-in bills to a custom bill table,
* safe late switching of ``DJANGO_LEDGER_BILLMODEL_MODEL`` after migrations,
* swappable purchase orders, receipts, accounts, entities, ledgers, journal
  entries, or other core ledger models,
* built-in tax, withholding, or e-document calculation.

``BillModel`` support is independent from ``CustomerModel``, ``VendorModel``,
``BankAccountModel``, ``UnitOfMeasureModel``, ``ItemModel``, ``InvoiceModel``,
``EstimateModel``, and ``ItemTransactionModel`` support. Configure each custom
model explicitly before initial migrations.
