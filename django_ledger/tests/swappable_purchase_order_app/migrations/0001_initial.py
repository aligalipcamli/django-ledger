# Generated manually for the PurchaseOrderModel swappability proof.

import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('django_ledger', '0038_bill_model_item_transaction_fk_swappable'),
        migrations.swappable_dependency(settings.DJANGO_LEDGER_ESTIMATEMODEL_MODEL),
        migrations.swappable_dependency(settings.DJANGO_LEDGER_ITEMMODEL_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomPurchaseOrderModel',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True, null=True)),
                ('markdown_notes', models.TextField(blank=True, null=True, verbose_name='Markdown Notes')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('po_number', models.SlugField(editable=False, max_length=20, verbose_name='Purchase Order Number')),
                ('po_title', models.CharField(max_length=250, validators=[
                    django.core.validators.MinLengthValidator(
                        limit_value=5,
                        message='PO Title must be greater than 5',
                    ),
                ], verbose_name='Purchase Order Title')),
                ('po_status', models.CharField(choices=[
                    ('draft', 'Draft'),
                    ('in_review', 'In Review'),
                    ('approved', 'Approved'),
                    ('fulfilled', 'Fulfilled'),
                    ('canceled', 'Canceled'),
                    ('void', 'Void'),
                ], default='draft', max_length=10)),
                ('po_amount', models.DecimalField(
                    decimal_places=2,
                    default=0,
                    max_digits=20,
                    verbose_name='Purchase Order Amount',
                )),
                ('po_amount_received', models.DecimalField(
                    decimal_places=2,
                    default=0,
                    max_digits=20,
                    verbose_name='Received Amount',
                )),
                ('date_draft', models.DateField(blank=True, null=True, verbose_name='Draft Date')),
                ('date_in_review', models.DateField(blank=True, null=True, verbose_name='In Review Date')),
                ('date_approved', models.DateField(blank=True, null=True, verbose_name='Approved Date')),
                ('date_void', models.DateField(blank=True, null=True, verbose_name='Void Date')),
                ('date_fulfilled', models.DateField(blank=True, null=True, verbose_name='Fulfillment Date')),
                ('date_canceled', models.DateField(blank=True, null=True, verbose_name='Canceled Date')),
                ('custom_marker', models.CharField(default='custom', max_length=32)),
                ('supplier_order_ref', models.CharField(blank=True, max_length=64)),
                ('ce_model', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.RESTRICT,
                    to=settings.DJANGO_LEDGER_ESTIMATEMODEL_MODEL,
                    verbose_name='Associated Customer Job/Estimate',
                )),
                ('entity', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='django_ledger.entitymodel',
                    verbose_name='Entity',
                )),
                ('po_items', models.ManyToManyField(
                    through='django_ledger.ItemTransactionModel',
                    through_fields=('po_model', 'item_model'),
                    to=settings.DJANGO_LEDGER_ITEMMODEL_MODEL,
                    verbose_name='Purchase Order Items',
                )),
            ],
            options={
                'abstract': False,
                'indexes': [
                    models.Index(fields=['entity'], name='swappable_p_entity__63ae8a_idx'),
                    models.Index(fields=['po_number'], name='swappable_p_po_numb_d22569_idx'),
                    models.Index(fields=['po_status'], name='swappable_p_po_stat_99d04f_idx'),
                    models.Index(fields=['ce_model'], name='swappable_p_ce_mode_deb40c_idx'),
                    models.Index(fields=['date_draft'], name='swappable_p_date_dr_f1f694_idx'),
                    models.Index(fields=['date_in_review'], name='swappable_p_date_in_094d41_idx'),
                    models.Index(fields=['date_approved'], name='swappable_p_date_ap_0ee225_idx'),
                    models.Index(fields=['date_fulfilled'], name='swappable_p_date_fu_019b5e_idx'),
                    models.Index(fields=['date_canceled'], name='swappable_p_date_ca_00934a_idx'),
                    models.Index(fields=['date_void'], name='swappable_p_date_vo_2c3e2d_idx'),
                ],
                'unique_together': {('entity', 'po_number')},
            },
        ),
    ]
