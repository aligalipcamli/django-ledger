# Generated manually for the ReceiptModel swappable test app.

import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('django_ledger', '0039_purchase_order_model_swappable'),
        migrations.swappable_dependency(settings.DJANGO_LEDGER_CUSTOMERMODEL_MODEL),
        migrations.swappable_dependency(settings.DJANGO_LEDGER_VENDORMODEL_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomReceiptModel',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True, null=True)),
                ('markdown_notes', models.TextField(blank=True, null=True, verbose_name='Markdown Notes')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('receipt_number', models.CharField(max_length=255, verbose_name='Receipt Number')),
                ('receipt_date', models.DateField(verbose_name='Receipt Date')),
                (
                    'receipt_type',
                    models.CharField(
                        choices=[
                            ('sales', 'Sales Receipt'),
                            ('customer_refund', 'Sales Refund'),
                            ('expense', 'Expense Receipt'),
                            ('expense_refund', 'Expense Refund'),
                            ('transfer', 'Transfer Receipt'),
                            ('debt_paydown', 'Debt Paydown Receipt'),
                        ],
                        max_length=15,
                        verbose_name='Receipt Type',
                    ),
                ),
                (
                    'amount',
                    models.DecimalField(
                        decimal_places=2,
                        help_text='Amount of the receipt.',
                        max_digits=20,
                        validators=[django.core.validators.MinValueValidator(limit_value=0)],
                        verbose_name='Receipt Amount',
                    ),
                ),
                ('custom_marker', models.CharField(default='custom', max_length=32)),
                ('payment_channel', models.CharField(blank=True, max_length=32)),
                (
                    'charge_account',
                    models.ForeignKey(
                        help_text='The financial account (cash or credit) where this transaction was made.',
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='charge_receiptmodel_set',
                        to='django_ledger.accountmodel',
                        verbose_name='Charge Account',
                    ),
                ),
                (
                    'customer_model',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.DJANGO_LEDGER_CUSTOMERMODEL_MODEL,
                        verbose_name='Customer Model',
                    ),
                ),
                (
                    'ledger_model',
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.PROTECT,
                        to='django_ledger.ledgermodel',
                        verbose_name='Ledger Model',
                    ),
                ),
                (
                    'receipt_account',
                    models.ForeignKey(
                        blank=True,
                        help_text='The income or expense account where this transaction will be reflected',
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to='django_ledger.accountmodel',
                        verbose_name='PnL Account',
                    ),
                ),
                (
                    'staged_transaction_model',
                    models.OneToOneField(
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
                (
                    'unit_model',
                    models.ForeignKey(
                        blank=True,
                        help_text='Helps segregate receipts and transactions into different classes or departments.',
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to='django_ledger.entityunitmodel',
                        verbose_name='Unit Model',
                    ),
                ),
                (
                    'vendor_model',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.DJANGO_LEDGER_VENDORMODEL_MODEL,
                        verbose_name='Vendor Model',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Sales/Expense Receipt',
                'verbose_name_plural': 'Sales/Expense Receipts',
                'abstract': False,
                'indexes': [
                    models.Index(fields=['receipt_number'], name='swappable_r_receipt_1c6696_idx'),
                    models.Index(fields=['ledger_model'], name='swappable_r_ledger__e745ab_idx'),
                    models.Index(fields=['receipt_date'], name='swappable_r_receipt_9822bc_idx'),
                    models.Index(fields=['receipt_type'], name='swappable_r_receipt_fe48d7_idx'),
                    models.Index(fields=['customer_model'], name='swappable_r_custome_f3dabf_idx'),
                    models.Index(fields=['vendor_model'], name='swappable_r_vendor__ef4001_idx'),
                ],
            },
        ),
    ]
