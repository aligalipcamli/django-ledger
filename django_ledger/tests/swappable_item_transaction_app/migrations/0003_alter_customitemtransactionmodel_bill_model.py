# Generated manually for combined ItemTransactionModel and BillModel swap tests.

import django.db.models.deletion
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0038_bill_model_item_transaction_fk_swappable'),
        ('swappable_item_transaction_app', '0002_alter_customitemtransactionmodel_ce_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customitemtransactionmodel',
            name='bill_model',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                to=swapper.get_model_name('django_ledger', 'BillModel'),
                verbose_name='Bill Model',
            ),
        ),
    ]
