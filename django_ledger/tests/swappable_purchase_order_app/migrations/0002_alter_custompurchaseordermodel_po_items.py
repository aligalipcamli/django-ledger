# Generated manually for combined PurchaseOrderModel and ItemTransactionModel swap tests.

import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0039_purchase_order_model_swappable'),
        ('swappable_purchase_order_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='custompurchaseordermodel',
            name='po_items',
            field=models.ManyToManyField(
                through=swapper.get_model_name('django_ledger', 'ItemTransactionModel'),
                through_fields=('po_model', 'item_model'),
                to=swapper.get_model_name('django_ledger', 'ItemModel'),
                verbose_name='Purchase Order Items',
            ),
        ),
    ]
