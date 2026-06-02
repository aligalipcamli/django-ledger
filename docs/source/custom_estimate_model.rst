Custom Estimate Model
=====================

Django Ledger supports a Swapper-backed custom ``EstimateModel`` for projects
that configure the custom model before running Django Ledger migrations.

This support is intended for new projects, or for empty databases where the
custom estimate model is selected before the first ``migrate``. It is not a
generic late-swap mechanism for existing databases with built-in Django Ledger
estimate data.

Setting
-------

Configure the effective estimate model in your Django settings:

.. code-block:: python

    DJANGO_LEDGER_ESTIMATEMODEL_MODEL = "myapp.MyEstimateModel"

The setting must be present before Django loads the app registry and before
initial migrations are run.

Custom Model Shape
------------------

The recommended custom model inherits from
``django_ledger.models.estimate.EstimateModelAbstract`` so it keeps Django
Ledger's expected estimate fields, manager, queryset helpers, customer
relationship, itemization behavior, numbering behavior, lifecycle transitions,
contract summary helpers, and validation hooks.

For example:

.. code-block:: python

    from django.db import models

    from django_ledger.models.estimate import EstimateModelAbstract


    class MyEstimateModel(EstimateModelAbstract):
        external_quote_ref = models.CharField(max_length=64, blank=True)
        approval_snapshot = models.JSONField(default=dict, blank=True)

        class Meta(EstimateModelAbstract.Meta):
            app_label = "myapp"

When the model is declared in ``myapp/models.py``, Django can usually infer the
app label. If the model lives outside the app's normal models module, declare
``app_label`` explicitly.

Avoid inheriting from the concrete
``django_ledger.models.estimate.EstimateModel`` when the goal is to avoid extra
joins. Django concrete model inheritance uses multi-table inheritance and keeps
a parent estimate table join.

Custom implementations that do not inherit from ``EstimateModelAbstract`` must
preserve the estimate contract used by Django Ledger. In practice that includes
the entity, customer, estimate number, title, contract terms, status, date,
amount estimate, itemization, numbering, lifecycle, manager, and queryset
behavior expected by the built-in estimate workflows.

What Is Covered
---------------

With the custom setting configured before initial migrations, Django Ledger
resolves the effective estimate model through Swapper. The supported surfaces
include:

* ``lazy_loader.get_estimate_model()`` runtime resolution.
* ``EntityModel`` estimate helper methods such as create and list.
* Estimate forms and estimate views when imported after the custom setting is
  configured.
* ``ItemTransactionModel.ce_model``.
* ``BillModel.ce_model``.
* ``InvoiceModel.ce_model``.
* ``PurchaseOrderModel.ce_model``.
* Estimate numbering, entity assignment, itemization, and lifecycle transitions
  for the effective estimate model.

``PurchaseOrderModel`` may also be a custom model when its own setting is
configured before initial migrations. ``ReceiptModel`` remains a fixed Django
Ledger model.
``InvoiceModel``, ``BillModel``, and ``ItemTransactionModel`` may be separately
swappable when their own settings are configured before initial migrations.

Migration Timing
----------------

Estimate model swapping is migration-sensitive. Configure
``DJANGO_LEDGER_ESTIMATEMODEL_MODEL`` before the first ``migrate`` for a new
project.

Changing this setting after Django Ledger migrations have already run is not
supported automatically. Existing estimates, item transactions, invoices, bills,
purchase orders, and document relationships are not copied or remapped by
Django Ledger. A project that needs to move from the built-in estimate table to
a custom estimate table must design and test its own data migration.

The migration history still creates Django Ledger's built-in estimate table
before a later migration retargets downstream estimate references through
Swapper. This keeps the forward migration path compatible, but it does not mean
an existing populated database can freely switch estimate models.

Lemuur Teklif Headers
---------------------

For Lemuur, ``EstimateModel`` swappability can support a custom Teklif header
row for quote references, external CRM identifiers, approval snapshots,
customer-facing validity metadata, and compact workflow status fields.

Line-level tax breakdowns, discount details, withholding details, integration
payloads, integration responses, retry history, and full event logs should
usually live on sidecar/profile models. Those values can be repeated, large,
line-specific, or workflow-specific, so storing them directly on the estimate
header can overstate the estimate model's responsibility.

Tax and e-document calculation policy belongs in project services. Django
Ledger's custom estimate support only changes the effective estimate header
model; it does not add Turkish tax, withholding, or e-document calculation
logic.

What Is Not Covered
-------------------

This feature does not provide:

* a generic data migration from built-in estimates to a custom estimate table,
* safe late switching of ``DJANGO_LEDGER_ESTIMATEMODEL_MODEL`` after migrations,
* swappable purchase orders, receipts, accounts, entities, ledgers, journal
  entries, or other core ledger models,
* built-in tax or e-document calculation.

``EstimateModel`` support is independent from ``CustomerModel``,
``VendorModel``, ``BankAccountModel``, ``UnitOfMeasureModel``, ``ItemModel``,
``InvoiceModel``, ``BillModel``, and ``ItemTransactionModel`` support.
Configure a custom invoice, bill, or item transaction model explicitly if those
rows also need custom tables.
