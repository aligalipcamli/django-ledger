# Generated manually for the UnitOfMeasureModel Strategy A schema proof.

import django.db.models.deletion
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0032_bank_account_model_import_job_fk_swappable'),
        swapper.dependency('django_ledger', 'UnitOfMeasureModel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemmodel',
            name='uom',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.RESTRICT,
                to=swapper.get_model_name('django_ledger', 'UnitOfMeasureModel'),
                verbose_name='Unit of Measure',
            ),
        ),
    ]
