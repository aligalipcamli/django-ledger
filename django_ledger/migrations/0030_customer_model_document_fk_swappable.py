# Generated manually for the CustomerModel Strategy A schema proof.

import django.db.models.deletion
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0029_stagedtransactionmodel_matched_transaction_and_more'),
        swapper.dependency('django_ledger', 'CustomerModel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='estimatemodel',
            name='customer',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.RESTRICT,
                to=swapper.get_model_name('django_ledger', 'CustomerModel'),
                verbose_name='Customer',
            ),
        ),
        migrations.AlterField(
            model_name='invoicemodel',
            name='customer',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.RESTRICT,
                to=swapper.get_model_name('django_ledger', 'CustomerModel'),
                verbose_name='Customer',
            ),
        ),
        migrations.AlterField(
            model_name='receiptmodel',
            name='customer_model',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to=swapper.get_model_name('django_ledger', 'CustomerModel'),
                verbose_name='Customer Model',
            ),
        ),
        migrations.AlterField(
            model_name='stagedtransactionmodel',
            name='customer_model',
            field=models.ForeignKey(
                blank=True,
                help_text='The Customer associated with the transaction.',
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                to=swapper.get_model_name('django_ledger', 'CustomerModel'),
                verbose_name='Associated Customer Model',
            ),
        ),
    ]
