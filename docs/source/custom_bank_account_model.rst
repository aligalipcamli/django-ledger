Custom Bank Account Model
=========================

Django Ledger supports a Swapper-backed custom ``BankAccountModel`` for
projects that configure the custom model before running Django Ledger
migrations.

This support is intended for new projects, or for empty databases where the
custom bank account model is selected before the first ``migrate``. It is not a
generic late-swap mechanism for existing databases with built-in Django Ledger
bank account data.

Setting
-------

Configure the effective bank account model in your Django settings:

.. code-block:: python

    DJANGO_LEDGER_BANKACCOUNTMODEL_MODEL = "myapp.MyBankAccountModel"

The setting must be present before Django loads the app registry and before
initial migrations are run.

Custom Model Shape
------------------

The recommended custom model inherits from
``django_ledger.models.bank_account.BankAccountModelAbstract`` so it keeps
Django Ledger's expected fields, manager, queryset helpers, account type
constants, active and hidden flags, and entity/account relationships.

For example:

.. code-block:: python

    from django.db import models

    from django_ledger.models.bank_account import BankAccountModelAbstract


    class MyBankAccountModel(BankAccountModelAbstract):
        external_id = models.CharField(max_length=64, blank=True)

        class Meta(BankAccountModelAbstract.Meta):
            app_label = "myapp"

When the model is declared in ``myapp/models.py``, Django can usually infer the
app label. If the model lives outside the app's normal models module, declare
``app_label`` explicitly.

Custom implementations that do not inherit from ``BankAccountModelAbstract``
must preserve the bank account contract used by Django Ledger. In practice that
includes the entity relationship, associated ``AccountModel`` relationship,
financial account fields, account type constants, active and hidden flags, and
manager/queryset methods such as ``for_entity()``, ``active()``, and
``hidden()``.

What Is Covered
---------------

With the custom setting configured before initial migrations, Django Ledger
resolves the effective bank account model through Swapper. The supported
surfaces include:

* ``lazy_loader.get_bank_account_model()`` runtime resolution.
* ``EntityModel`` bank account helper methods such as bank account create and
  list.
* Bank account forms when imported after the custom setting is configured.
* Import job creation forms that list bank accounts.
* ``ImportJobModel.bank_account_model``.

Migration Timing
----------------

Bank account model swapping is migration-sensitive. Configure
``DJANGO_LEDGER_BANKACCOUNTMODEL_MODEL`` before the first ``migrate`` for a new
project.

Changing this setting after Django Ledger migrations have already run is not
supported automatically. Existing import job foreign keys and existing bank
account rows are not copied or remapped by Django Ledger. A project that needs
to move from the built-in bank account table to a custom bank account table
must design and test its own data migration.

The migration history still creates Django Ledger's built-in bank account table
before a later migration retargets the import job bank account foreign key
through Swapper. This keeps the forward migration path compatible, but it does
not mean an existing populated database can freely switch bank account models.

Lemuur PaymentAccount
---------------------

For Lemuur, ``BankAccountModel`` swappability can support a custom model that
acts as the Django Ledger projection for a broader ``PaymentAccount`` concept.
That can be useful for bank and card import targets, financial institution
metadata, reconciliation state, and account-product identifiers.

Projects that do not need Django Ledger import jobs to point directly at a
custom table can still keep a separate sidecar/profile model related to the
built-in bank account model. Choose a custom ``BankAccountModel`` only when the
project needs the Django Ledger bank account row itself to carry the project
specific identity or metadata from the first migration.

What Is Not Covered
-------------------

This feature does not provide:

* a generic data migration from built-in bank accounts to a custom bank account
  table,
* safe late switching of ``DJANGO_LEDGER_BANKACCOUNTMODEL_MODEL`` after
  migrations,
* swappable import job, account, entity, staged transaction, or other core
  ledger models.

``BankAccountModel`` support is independent from ``CustomerModel`` and
``VendorModel`` support. Enabling a custom bank account model does not make all
domain-facing Django Ledger models swappable.
