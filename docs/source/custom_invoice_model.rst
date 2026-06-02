Custom Invoice Model
====================

Django Ledger supports a Swapper-backed custom ``InvoiceModel`` for projects
that configure the custom model before running Django Ledger migrations.

This support is intended for new projects, or for empty databases where the
custom invoice model is selected before the first ``migrate``. It is not a
generic late-swap mechanism for existing databases with built-in Django Ledger
invoice data.

Setting
-------

Configure the effective invoice model in your Django settings:

.. code-block:: python

    DJANGO_LEDGER_INVOICEMODEL_MODEL = "myapp.MyInvoiceModel"

The setting must be present before Django loads the app registry and before
initial migrations are run.

Custom Model Shape
------------------

The recommended custom model inherits from
``django_ledger.models.invoice.InvoiceModelAbstract`` so it keeps Django
Ledger's expected invoice fields, manager, queryset helpers, ledger
relationship, customer relationship, payment terms, itemization behavior,
numbering behavior, lifecycle transitions, and validation hooks.

For example:

.. code-block:: python

    from django.db import models

    from django_ledger.models.invoice import InvoiceModelAbstract


    class MyInvoiceModel(InvoiceModelAbstract):
        external_invoice_id = models.CharField(max_length=64, blank=True)
        e_document_status = models.CharField(max_length=32, blank=True)

        class Meta(InvoiceModelAbstract.Meta):
            app_label = "myapp"

When the model is declared in ``myapp/models.py``, Django can usually infer the
app label. If the model lives outside the app's normal models module, declare
``app_label`` explicitly.

Avoid inheriting from the concrete ``django_ledger.models.invoice.InvoiceModel``
when the goal is to avoid extra joins. Django concrete model inheritance uses
multi-table inheritance and keeps a parent invoice table join.

Custom implementations that do not inherit from ``InvoiceModelAbstract`` must
preserve the invoice contract used by Django Ledger. In practice that includes
the ledger, entity, customer, terms, account, amount, date, status, estimate,
itemization, numbering, lifecycle, manager, and queryset behavior expected by
the built-in invoice workflows.

What Is Covered
---------------

With the custom setting configured before initial migrations, Django Ledger
resolves the effective invoice model through Swapper. The supported surfaces
include:

* ``lazy_loader.get_invoice_model()`` runtime resolution.
* ``EntityModel`` invoice helper methods such as create and list.
* Invoice forms and invoice views when imported after the custom setting is
  configured.
* ``ItemTransactionModel.invoice_model``.
* ``InvoiceModel.invoice_items`` through the effective ``ItemTransactionModel``.
* Invoice numbering and entity assignment for the effective invoice model.

If no custom item transaction model is configured, invoice itemization uses the
built-in ``ItemTransactionModel``. Projects that also configure
``DJANGO_LEDGER_ITEMTRANSACTIONMODEL_MODEL`` before initial migrations can use a
custom line-item table with a custom invoice table.

Migration Timing
----------------

Invoice model swapping is migration-sensitive. Configure
``DJANGO_LEDGER_INVOICEMODEL_MODEL`` before the first ``migrate`` for a new
project.

Changing this setting after Django Ledger migrations have already run is not
supported automatically. Existing invoices, ledgers, item transactions, and
document relationships are not copied or remapped by Django Ledger. A project
that needs to move from the built-in invoice table to a custom invoice table
must design and test its own data migration.

The migration history still creates Django Ledger's built-in invoice table
before a later migration retargets ``ItemTransactionModel.invoice_model``
through Swapper. This keeps the forward migration path compatible, but it does
not mean an existing populated database can freely switch invoice models.

Lemuur Invoice Headers
----------------------

For Lemuur, ``InvoiceModel`` swappability can support a custom invoice header
row for header snapshots, external identifiers, and status fields. E-document
status, GIB or integrator UUIDs, buyer tax-number snapshots, buyer title
snapshots, address snapshots, discount totals, tax summary totals, and compact
integration status fields may fit naturally on a custom invoice model.

Line-level tax breakdowns, discount details, withholding details, integration
payloads, integration responses, retry history, and full e-document event logs
should usually live on sidecar/profile models. Those values can be repeated,
large, line-specific, or workflow-specific, so storing them directly on the
invoice header can overstate the invoice model's responsibility.

Tax and e-document calculation policy belongs in project services. Django
Ledger's custom invoice support only changes the effective invoice header model;
it does not add Turkish tax, withholding, or e-document calculation logic.

What Is Not Covered
-------------------

This feature does not provide:

* a generic data migration from built-in invoices to a custom invoice table,
* safe late switching of ``DJANGO_LEDGER_INVOICEMODEL_MODEL`` after migrations,
* swappable bills, purchase orders, receipts, accounts, entities, ledgers,
  journal entries, or other core ledger models,
* built-in tax or e-document calculation.

``InvoiceModel`` support is independent from ``CustomerModel``, ``VendorModel``,
``BankAccountModel``, ``UnitOfMeasureModel``, ``ItemModel``, ``EstimateModel``,
and ``ItemTransactionModel`` support. Configure a custom item transaction model
explicitly if line-item rows also need a custom table.
