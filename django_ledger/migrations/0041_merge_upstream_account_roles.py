"""Join upstream role choices and the private swappable-model history."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('django_ledger', '0030_alter_accountmodel_role'),
        ('django_ledger', '0040_receipt_model_swappable'),
    ]
    operations = []
