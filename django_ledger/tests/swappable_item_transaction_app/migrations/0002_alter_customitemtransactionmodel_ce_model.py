# Generated manually for combined ItemTransactionModel and EstimateModel swap tests.

import django.db.models.deletion
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0037_estimate_model_document_fk_swappable'),
        ('swappable_item_transaction_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customitemtransactionmodel',
            name='ce_model',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                to=swapper.get_model_name('django_ledger', 'EstimateModel'),
                verbose_name='Customer Estimate',
            ),
        ),
    ]
