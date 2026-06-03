# Generated manually for the EstimateModel Strategy A schema proof.

import django.db.models.deletion
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0036_item_transaction_model_swappable'),
        swapper.dependency('django_ledger', 'EstimateModel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemtransactionmodel',
            name='ce_model',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                to=swapper.get_model_name('django_ledger', 'EstimateModel'),
                verbose_name='Customer Estimate',
            ),
        ),
        migrations.AlterField(
            model_name='billmodel',
            name='ce_model',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                to=swapper.get_model_name('django_ledger', 'EstimateModel'),
                verbose_name='Associated Customer Job/Estimate',
            ),
        ),
        migrations.AlterField(
            model_name='invoicemodel',
            name='ce_model',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                to=swapper.get_model_name('django_ledger', 'EstimateModel'),
                verbose_name='Associated Customer Job/Estimate',
            ),
        ),
        migrations.AlterField(
            model_name='purchaseordermodel',
            name='ce_model',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                to=swapper.get_model_name('django_ledger', 'EstimateModel'),
                verbose_name='Associated Customer Job/Estimate',
            ),
        ),
    ]
