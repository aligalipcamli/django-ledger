# Generated manually for combined ItemTransactionModel and PurchaseOrderModel swap tests.

import django.db.models.deletion
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0039_purchase_order_model_swappable'),
        ('swappable_item_transaction_app', '0003_alter_customitemtransactionmodel_bill_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customitemtransactionmodel',
            name='po_model',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                to=swapper.get_model_name('django_ledger', 'PurchaseOrderModel'),
                verbose_name='Purchase Order Model',
            ),
        ),
    ]
