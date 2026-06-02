# Generated manually for the InvoiceModel Strategy A schema proof.

import django.db.models.deletion
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0034_item_model_item_transaction_fk_swappable'),
        swapper.dependency('django_ledger', 'InvoiceModel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemtransactionmodel',
            name='invoice_model',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                to=swapper.get_model_name('django_ledger', 'InvoiceModel'),
                verbose_name='Invoice Model',
            ),
        ),
    ]
