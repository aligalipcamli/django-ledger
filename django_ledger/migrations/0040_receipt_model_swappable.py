# Generated manually for the ReceiptModel Strategy A schema proof.

import django.db.models.deletion
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0039_purchase_order_model_swappable'),
        swapper.dependency('django_ledger', 'ReceiptModel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='receiptmodel',
            name='staged_transaction_model',
            field=models.OneToOneField(
                blank=True,
                help_text='The staged transaction associated with the receipt from bank feeds.',
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name='receiptmodel',
                related_query_name='receiptmodel',
                to='django_ledger.stagedtransactionmodel',
                verbose_name='Staged Transaction Model',
            ),
        ),
    ]
