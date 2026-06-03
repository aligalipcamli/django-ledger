# Generated manually for the BillModel Strategy A schema proof.

import django.db.models.deletion
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0037_estimate_model_document_fk_swappable'),
        swapper.dependency('django_ledger', 'BillModel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemtransactionmodel',
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
