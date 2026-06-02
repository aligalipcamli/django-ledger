# Generated manually for combined InvoiceModel and ItemTransactionModel swap tests.

import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0036_item_transaction_model_swappable'),
        ('swappable_invoice_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='custominvoicemodel',
            name='invoice_items',
            field=models.ManyToManyField(
                through=swapper.get_model_name('django_ledger', 'ItemTransactionModel'),
                through_fields=('invoice_model', 'item_model'),
                to=swapper.get_model_name('django_ledger', 'ItemModel'),
                verbose_name='Invoice Items',
            ),
        ),
    ]
