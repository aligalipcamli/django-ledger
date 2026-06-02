# Generated manually for the ItemModel Strategy A schema proof.

import django.db.models.deletion
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0033_unit_of_measure_model_item_fk_swappable'),
        swapper.dependency('django_ledger', 'ItemModel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemtransactionmodel',
            name='item_model',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.RESTRICT,
                to=swapper.get_model_name('django_ledger', 'ItemModel'),
                verbose_name='Item Model',
            ),
        ),
        migrations.AlterField(
            model_name='billmodel',
            name='bill_items',
            field=models.ManyToManyField(
                through='django_ledger.ItemTransactionModel',
                through_fields=('bill_model', 'item_model'),
                to=swapper.get_model_name('django_ledger', 'ItemModel'),
                verbose_name='Bill Items',
            ),
        ),
        migrations.AlterField(
            model_name='invoicemodel',
            name='invoice_items',
            field=models.ManyToManyField(
                through='django_ledger.ItemTransactionModel',
                through_fields=('invoice_model', 'item_model'),
                to=swapper.get_model_name('django_ledger', 'ItemModel'),
                verbose_name='Invoice Items',
            ),
        ),
        migrations.AlterField(
            model_name='purchaseordermodel',
            name='po_items',
            field=models.ManyToManyField(
                through='django_ledger.ItemTransactionModel',
                through_fields=('po_model', 'item_model'),
                to=swapper.get_model_name('django_ledger', 'ItemModel'),
                verbose_name='Purchase Order Items',
            ),
        ),
    ]
