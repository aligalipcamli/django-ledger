# Generated manually for the ItemTransactionModel Strategy A schema proof.

import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0035_invoice_model_item_transaction_fk_swappable'),
        swapper.dependency('django_ledger', 'ItemTransactionModel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billmodel',
            name='bill_items',
            field=models.ManyToManyField(
                through=swapper.get_model_name('django_ledger', 'ItemTransactionModel'),
                through_fields=('bill_model', 'item_model'),
                to=swapper.get_model_name('django_ledger', 'ItemModel'),
                verbose_name='Bill Items',
            ),
        ),
        migrations.AlterField(
            model_name='invoicemodel',
            name='invoice_items',
            field=models.ManyToManyField(
                through=swapper.get_model_name('django_ledger', 'ItemTransactionModel'),
                through_fields=('invoice_model', 'item_model'),
                to=swapper.get_model_name('django_ledger', 'ItemModel'),
                verbose_name='Invoice Items',
            ),
        ),
        migrations.AlterField(
            model_name='purchaseordermodel',
            name='po_items',
            field=models.ManyToManyField(
                through=swapper.get_model_name('django_ledger', 'ItemTransactionModel'),
                through_fields=('po_model', 'item_model'),
                to=swapper.get_model_name('django_ledger', 'ItemModel'),
                verbose_name='Purchase Order Items',
            ),
        ),
    ]
