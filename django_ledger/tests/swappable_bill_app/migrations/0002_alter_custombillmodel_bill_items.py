# Generated manually for combined BillModel and ItemTransactionModel swap tests.

import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0038_bill_model_item_transaction_fk_swappable'),
        ('swappable_bill_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='custombillmodel',
            name='bill_items',
            field=models.ManyToManyField(
                through=swapper.get_model_name('django_ledger', 'ItemTransactionModel'),
                through_fields=('bill_model', 'item_model'),
                to=swapper.get_model_name('django_ledger', 'ItemModel'),
                verbose_name='Bill Items',
            ),
        ),
    ]
