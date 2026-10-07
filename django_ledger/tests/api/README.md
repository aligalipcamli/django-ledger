# High-Level API Behavior Tests

## Purpose

This directory contains deterministic, high-level behavior tests for Django Ledger's public model API.

The goal is not to replace the existing test suite or prescribe a new testing strategy. These tests add a readable contract layer around public APIs that downstream applications are likely to call directly: model methods, managers, querysets, numbering helpers, lifecycle actions, and cross-model orchestration.

The suite now contains 800+ high-level API tests covering the main accounting, document, import, inventory, and party-model surfaces.

## Why this directory exists

Django Ledger exposes important behavior through coordinated model interactions rather than isolated field validation alone. Examples include:

* entity-scoped and fiscal-year-scoped number generation,
* ledger and journal entry posting behavior,
* document lifecycle transitions,
* item transaction ownership across documents,
* import job and staged transaction migration,
* receipt and closing entry behavior,
* queryset and manager-level filtering contracts.

The tests are intentionally placed under `django_ledger/tests/api/` to make the scope explicit: these are public API behavior tests, not private implementation tests.

## Design goals

1. **Deterministic setup**

   Tests avoid randomized fixture generation. Each module creates the minimum entity, chart of accounts, accounts, counterparties, items, documents, imports, or transactions needed to express the behavior under test.

2. **Public API first**

   Tests prefer public model methods, manager methods, queryset methods, and high-level flows over private helpers or implementation details.

3. **Behavior over implementation**

   Assertions focus on externally meaningful contracts such as generated numbers, state transitions, ownership links, ledger effects, queryset results, and public helper output.

4. **Refactor safety**

   The suite is intended to provide confidence before larger refactors, including possible swappable-model work. If concrete models, abstract bases, foreign keys, manager implementations, or wrapper relationships change, these tests should help confirm that public behavior remains stable.

5. **Small focused tests**

   Test files are grouped by model family or behavior family. Shared setup is kept local enough that each module remains understandable in isolation.

## Coverage overview

### Core accounting engine

Covered model families include:

* `EntityModel`
* `EntityStateModel`
* `EntityUnitModel`
* `ChartOfAccountModel` and bundled default CoA data
* `AccountModel`
* `LedgerModel`
* `JournalEntryModel`
* `TransactionModel`

Covered behavior includes entity creation, fiscal-period helpers, tree behavior, default chart of accounts orchestration, account creation and role defaults, ledger lifecycle predicates and transitions, journal entry verification and numbering, transaction filtering and validation, entity state sequencing, and core queryset/user scoping contracts.

### Import, staging, receipts, and closing

Covered model families include:

* `BankAccountModel`
* `ImportJobModel`
* `StagedTransactionModel`
* `ReceiptModel`
* `ClosingEntryModel`
* `ClosingEntryTransactionModel`

Covered behavior includes bank account configuration, import job setup and annotations, staged transaction splitting and matching, import/undo behavior, receipt configuration and deletion guards, closing entry posting/unposting, closing transaction normalization, and locked-period behavior.

### Commercial documents

Covered model families include:

* `BillModel`
* `InvoiceModel`
* `EstimateModel`
* `PurchaseOrderModel`

Covered behavior includes document configuration, itemization, lifecycle transitions, payment or fulfillment behavior where applicable, document numbering, URL/message helpers, status signals, queryset filters, deletion/void guards, and selected cross-document bindings.

### Items, units, and line items

Covered model families include:

* `UnitOfMeasureModel`
* `ItemModel`
* `ItemTransactionModel`

Covered behavior includes unit creation and scoping, item role/account behavior, product/service/expense/inventory helpers, item transaction ownership across documents, amount/status helpers, inventory pipeline filters, inventory count aggregation, and inventory update behavior.

### Commercial parties

Covered model families include:

* `CustomerModel`
* `VendorModel`

Covered behavior includes entity/user scoping, active/inactive/hidden/visible filters, direct numbering APIs, entity factory helpers, display and URL helpers, upload paths, contact validation, customer tax collection validation, and light vendor tax/financial-account helper behavior.

### Infrastructure and compatibility

Covered infrastructure includes:

* `lazy_loader` model and report class resolution,
* public schema constant top-level shape,
* deprecated `entity_slug=` compatibility behavior,
* selected IO blueprint/commit behavior.

These tests are intentionally smoke-level. They protect public infrastructure contracts without asserting private import mechanics or full schema bodies.

## Behavior patterns documented by the suite

The suite intentionally documents recurring behavior patterns that downstream code may depend on:

* `EntityStateModel` sequences are scoped by entity, optional entity unit, fiscal year, and key.
* Customer, vendor, and item numbering use entity-level state without fiscal year or entity unit.
* Bills, invoices, estimates, purchase orders, receipts, and journal entries use fiscal-year-scoped numbering.
* Journal entry numbering also uses entity-unit scoping when an entity unit is present.
* Some `commit=False` APIs still mutate the in-memory model and may consume entity state sequence values.
* Hidden-but-active records are often included by `active()` filters but excluded by `visible()` filters.
* Cross-entity bindings are guarded for accounts, counterparties, documents, receipts, imports, inventory, and staged transactions.
* Some documents have wrapper ledgers before they are fully migrated into accounting transactions.
* Staged transaction operations that rely on annotation-backed state are exercised through annotated queryset instances.

## Bug fixes and characterization coverage

The suite distinguishes between public bugs and characterization:

* Clear public bugs discovered during test development received minimal production fixes and regression tests.
* Surprising but stable current behavior is documented as characterization when changing it would require a broader product or API decision.

This keeps the suite useful for maintainers: tests describe expected public behavior without turning every oddity into an immediate refactor.

## Running the suite

Run all high-level API behavior tests:

```bash
python manage.py test django_ledger.tests.api
```

Latest full API suite result after the Customer/Vendor campaign:

```bash
.venv/bin/python manage.py test django_ledger.tests.api
# Ran 816 tests
# OK (skipped=1)
```

The final isolated infrastructure and compatibility smoke tests were also run:

```bash
.venv/bin/python manage.py test \
  django_ledger.tests.api.test_model_infrastructure_api \
  django_ledger.tests.api.test_deprecated_entity_slug_api
# Ran 6 tests
# OK
```

Run an individual module:

```bash
python manage.py test django_ledger.tests.api.test_receipt_api
python manage.py test django_ledger.tests.api.test_data_import_api
python manage.py test django_ledger.tests.api.test_closing_entry_api
```

## Contribution notes

### Upstream 0.8.5 integration

The private fork includes upstream master through `ecbd0663329ffee0b9f433aeaa56c12e012305d7`.
The merge preserves the swappable models, Treebeard 7 native managers, bounded
entity slug generation and guarded typing imports. Migration
`0041_merge_upstream_account_roles` joins upstream's role choices with the
existing `0040_receipt_model_swappable` leaf; it does not rewrite applied
migrations or create financial transactions.

`test_upstream_085_compatibility_api.py` protects the compatibility boundaries:

* `COGS` remains an alias for the persisted `cogs_regular` role.
* Legacy `GROUP_IC_*` names retain their original scopes; new `GROUP_PNL_*`
  groups expose the expanded upstream classifications.
* Direct `python_digest(equity_only=True)` retains the earnings filter rather
  than silently broadening it after the upstream keyword rename.
* Default product and service factories select regular COGS even when every
  new cost subtype has its own default account.
* Account-tree setup rolls back atomically on failure and restores the routing
  context. The new no-return account creation option still persists the account.

The default API run skips tests whose custom models are not installed. A full
private-fork acceptance must also run those tests using their documented
`django_ledger.tests.settings_swappable_*` settings. A skip is not a pass.
Keep each settings process and test database isolated; do not change the
application's user model or swappable settings to make these tests run.

Lemuur's independently pinned runtime dependencies remain authoritative for
its integration tests; upstream's development lockfile is not a request to
upgrade the deployed Django runtime.

### Model typing imports

`test_model_typing_contract.py` protects the account and entity-unit forward
references. `EntityModel` and `ChartOfAccountModel` are imported only under
`TYPE_CHECKING`; runtime model resolution remains with `lazy_loader` to avoid
circular imports during Django startup. The tests resolve the unchanged
annotations using an explicit namespace built from those guarded imports and
check that model names are absent from the runtime module namespaces.

This is a static typing contract, not a promise that bare `get_type_hints()`
can resolve type-checking-only names without a supplied namespace. It also
does not certify a whole-project mypy baseline.

With Ruff installed, the owning static gate is:

```bash
python -m ruff check --select F821 django_ledger/models/accounts.py django_ledger/models/unit.py
python manage.py test django_ledger.tests.api.test_model_typing_contract
```

These tests are intentionally more explicit than fixture-heavy tests. The verbosity is a tradeoff: it keeps each behavior contract readable without relying on hidden randomized fixtures or broad shared state.

The suite is especially useful before changes involving:

* abstract/concrete model boundaries,
* swappable model support,
* manager/queryset refactors,
* foreign key target changes,
* document lifecycle changes,
* ledger and journal entry posting internals,
* entity state and numbering internals,
* import/staging and receipt orchestration.

## AI assistance disclosure

This test suite was developed with AI assistance and human review.

AI was used to help draft test structures, identify likely behavior contracts, and iterate on failures. The human contributor ran the tests, inspected failures, reviewed behavior against the source code, and made the final decisions about which contracts and fixes to keep.
