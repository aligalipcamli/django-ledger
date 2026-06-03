Custom Customer Model
=====================

Django Ledger supports a Swapper-backed custom ``CustomerModel`` for projects
that configure the custom model before running Django Ledger migrations.

This support is intended for new projects, or for empty databases where the
custom customer model is selected before the first ``migrate``. It is not a
generic late-swap mechanism for existing databases with built-in Django Ledger
customer data.

Setting
-------

Configure the effective customer model in your Django settings:

.. code-block:: python

    DJANGO_LEDGER_CUSTOMERMODEL_MODEL = "myapp.MyCustomerModel"

The setting must be present before Django loads the app registry and before
initial migrations are run.

Custom Model Shape
------------------

The recommended custom model inherits from
``django_ledger.models.customer.CustomerModelAbstract`` so it keeps Django
Ledger's expected fields, manager, queryset helpers, numbering behavior, and
entity relationship.

For example:

.. code-block:: python

    from django.db import models

    from django_ledger.models.customer import CustomerModelAbstract


    class MyCustomerModel(CustomerModelAbstract):
        external_id = models.CharField(max_length=64, blank=True)

        class Meta(CustomerModelAbstract.Meta):
            app_label = "myapp"

When the model is declared in ``myapp/models.py``, Django can usually infer the
app label. If the model lives outside the app's normal models module, declare
``app_label`` explicitly.

Custom implementations that do not inherit from ``CustomerModelAbstract`` must
preserve the customer contract used by Django Ledger. In practice that includes
the entity relationship, customer number/name fields, active and hidden flags,
and manager/queryset methods such as ``for_entity()``, ``active()``, and
``visible()``.

What Is Covered
---------------

With the custom setting configured before initial migrations, Django Ledger
resolves the effective customer model through Swapper. The supported surfaces
include:

* ``lazy_loader.get_customer_model()`` runtime resolution.
* ``EntityModel`` customer helper methods such as customer create and list.
* Customer forms when imported after the custom setting is configured.
* ``InvoiceModel.customer``.
* ``EstimateModel.customer``.
* ``ReceiptModel.customer_model``.
* ``StagedTransactionModel.customer_model``.

Migration Timing
----------------

Customer model swapping is migration-sensitive. Configure
``DJANGO_LEDGER_CUSTOMERMODEL_MODEL`` before the first ``migrate`` for a new
project.

Changing this setting after Django Ledger migrations have already run is not
supported automatically. Existing document foreign keys and existing customer
rows are not copied or remapped by Django Ledger. A project that needs to move
from the built-in customer table to a custom customer table must design and
test its own data migration.

The migration history still creates Django Ledger's built-in customer table
before a later migration retargets the document customer foreign keys through
Swapper. This keeps the forward migration path compatible, but it does not mean
an existing populated database can freely switch customer models.

What Is Not Covered
-------------------

This feature does not provide:

* a generic data migration from built-in customers to a custom customer table,
* safe late switching of ``DJANGO_LEDGER_CUSTOMERMODEL_MODEL`` after migrations,
* swappable commercial documents or receipt models through this setting.

A future system check could warn when a project appears to configure a custom
customer model after Django Ledger has already been migrated. Such a check is a
separate safeguard and would not replace a project-specific data migration.
