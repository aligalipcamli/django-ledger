# Generated manually for the ItemTransactionModel swappability proof.

import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('django_ledger', '0035_invoice_model_item_transaction_fk_swappable'),
        migrations.swappable_dependency(settings.DJANGO_LEDGER_INVOICEMODEL_MODEL),
        migrations.swappable_dependency(settings.DJANGO_LEDGER_ITEMMODEL_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomItemTransactionModel',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True, null=True)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('quantity', models.FloatField(
                    blank=True,
                    null=True,
                    validators=[django.core.validators.MinValueValidator(limit_value=0.0)],
                    verbose_name='Quantity',
                )),
                ('unit_cost', models.FloatField(
                    blank=True,
                    null=True,
                    validators=[django.core.validators.MinValueValidator(limit_value=0.0)],
                    verbose_name='Cost Per Unit',
                )),
                ('total_amount', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    editable=False,
                    max_digits=20,
                    null=True,
                    validators=[django.core.validators.MinValueValidator(limit_value=0.0)],
                    verbose_name='Total Amount QTY x UnitCost',
                )),
                ('po_quantity', models.FloatField(
                    blank=True,
                    help_text='Authorized item quantity for purchasing.',
                    null=True,
                    validators=[django.core.validators.MinValueValidator(limit_value=0.0)],
                    verbose_name='PO Quantity',
                )),
                ('po_unit_cost', models.FloatField(
                    blank=True,
                    help_text='Purchase Order unit cost.',
                    null=True,
                    validators=[django.core.validators.MinValueValidator(limit_value=0.0)],
                    verbose_name='PO Unit Cost',
                )),
                ('po_total_amount', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    editable=False,
                    help_text='Maximum authorized cost per Purchase Order.',
                    max_digits=20,
                    null=True,
                    validators=[django.core.validators.MinValueValidator(limit_value=0.0)],
                    verbose_name='Authorized maximum item cost per Purchase Order',
                )),
                ('po_item_status', models.CharField(
                    blank=True,
                    choices=[
                        ('not_ordered', 'Not Ordered'),
                        ('ordered', 'Ordered'),
                        ('in_transit', 'In Transit'),
                        ('received', 'Received'),
                        ('cancelled', 'Canceled'),
                    ],
                    max_length=15,
                    null=True,
                    verbose_name='PO Item Status',
                )),
                ('ce_quantity', models.FloatField(
                    blank=True,
                    null=True,
                    validators=[django.core.validators.MinValueValidator(limit_value=0.0)],
                    verbose_name='Estimated/Contract Quantity',
                )),
                ('ce_unit_cost_estimate', models.FloatField(
                    blank=True,
                    null=True,
                    validators=[django.core.validators.MinValueValidator(limit_value=0.0)],
                    verbose_name='Estimate/Contract Cost per Unit.',
                )),
                ('ce_cost_estimate', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    editable=False,
                    max_digits=20,
                    null=True,
                    validators=[django.core.validators.MinValueValidator(limit_value=0.0)],
                    verbose_name='Total Estimate/Contract Cost.',
                )),
                ('ce_unit_revenue_estimate', models.FloatField(
                    blank=True,
                    null=True,
                    validators=[django.core.validators.MinValueValidator(limit_value=0.0)],
                    verbose_name='Estimate/Contract Revenue per Unit.',
                )),
                ('ce_revenue_estimate', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    editable=False,
                    max_digits=20,
                    null=True,
                    validators=[django.core.validators.MinValueValidator(limit_value=0.0)],
                    verbose_name='Total Estimate/Contract Revenue.',
                )),
                ('item_notes', models.CharField(
                    blank=True,
                    max_length=400,
                    null=True,
                    verbose_name='Description',
                )),
                ('custom_marker', models.CharField(default='custom', max_length=32)),
                ('line_tax_total', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('bill_model', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.RESTRICT,
                    to='django_ledger.billmodel',
                    verbose_name='Bill Model',
                )),
                ('ce_model', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.RESTRICT,
                    to='django_ledger.estimatemodel',
                    verbose_name='Customer Estimate',
                )),
                ('entity_unit', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.RESTRICT,
                    to='django_ledger.entityunitmodel',
                    verbose_name='Associated Entity Unit',
                )),
                ('invoice_model', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.RESTRICT,
                    to=settings.DJANGO_LEDGER_INVOICEMODEL_MODEL,
                    verbose_name='Invoice Model',
                )),
                ('item_model', models.ForeignKey(
                    on_delete=django.db.models.deletion.RESTRICT,
                    to=settings.DJANGO_LEDGER_ITEMMODEL_MODEL,
                    verbose_name='Item Model',
                )),
                ('po_model', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.RESTRICT,
                    to='django_ledger.purchaseordermodel',
                    verbose_name='Purchase Order Model',
                )),
            ],
            options={
                'abstract': False,
                'indexes': [
                    models.Index(fields=['bill_model', 'item_model'], name='swappable_i_bill_mo_31870d_idx'),
                    models.Index(fields=['invoice_model', 'item_model'], name='swappable_i_invoice_0c9705_idx'),
                    models.Index(fields=['po_model', 'item_model'], name='swappable_i_po_mode_72681a_idx'),
                    models.Index(fields=['ce_model', 'item_model'], name='swappable_i_ce_mode_88cad4_idx'),
                    models.Index(fields=['po_item_status'], name='swappable_i_po_item_616a0f_idx'),
                ],
            },
        ),
    ]
