# Generated manually for combined InvoiceModel and EstimateModel swap tests.

import django.db.models.deletion
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0037_estimate_model_document_fk_swappable'),
        ('swappable_invoice_app', '0002_alter_custominvoicemodel_invoice_items'),
    ]

    operations = [
        migrations.AlterField(
            model_name='custominvoicemodel',
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
