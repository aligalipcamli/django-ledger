# Generated manually for the BankAccountModel Strategy A schema proof.

import django.db.models.deletion
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0031_vendor_model_document_fk_swappable'),
        swapper.dependency('django_ledger', 'BankAccountModel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='importjobmodel',
            name='bank_account_model',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to=swapper.get_model_name('django_ledger', 'BankAccountModel'),
                verbose_name='Associated Bank Account Model',
            ),
        ),
    ]
