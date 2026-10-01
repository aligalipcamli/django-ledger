"""Ledger read-query optimizations at the public Treebeard mutation boundary."""

from django.db import transaction
from treebeard.mp_tree import MP_NodeQuerySet


class LedgerMPNodeQuerySet(MP_NodeQuerySet):
    def delete(self, *args, **kwargs):
        # Treebeard projects path/depth/numchild before deleting descendants.
        # Read-only select_related joins conflict with that projection. Keep
        # filters (including tenant scope), annotations and Treebeard's native
        # deletion/counter logic; remove only eager loading from this clone.
        with transaction.atomic(using=self.db):
            result = super(LedgerMPNodeQuerySet, self.select_related(None)).delete(
                *args, **kwargs
            )
        self._result_cache = None
        return result

    delete.alters_data = True
    delete.queryset_only = True
