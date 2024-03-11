# Generated by Django 4.1.6 on 2024-03-10 22:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0005_order_updated_at'),
        ('wallet', '0003_alter_wallettransaction_transaction_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pendingwallettransaction',
            name='order',
            field=models.OneToOneField(default=1, on_delete=django.db.models.deletion.CASCADE, to='orders.order'),
            preserve_default=False,
        ),
    ]
