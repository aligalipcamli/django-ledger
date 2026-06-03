# Generated manually for the VendorModel Strategy A schema proof.

import django.db.models.deletion
import swapper
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0030_customer_model_document_fk_swappable'),
        swapper.dependency('django_ledger', 'VendorModel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billmodel',
            name='vendor',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to=swapper.get_model_name('django_ledger', 'VendorModel'),
                verbose_name='Vendor',
            ),
        ),
        migrations.AlterField(
            model_name='receiptmodel',
            name='vendor_model',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to=swapper.get_model_name('django_ledger', 'VendorModel'),
                verbose_name='Vendor Model',
            ),
        ),
        migrations.AlterField(
            model_name='stagedtransactionmodel',
            name='vendor_model',
            field=models.ForeignKey(
                blank=True,
                help_text='The Vendor associated with the transaction.',
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                to=swapper.get_model_name('django_ledger', 'VendorModel'),
                verbose_name='Associated Vendor Model',
            ),
        ),
    ]
