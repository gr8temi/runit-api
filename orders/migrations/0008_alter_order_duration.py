# Generated by Django 4.1.6 on 2024-04-14 15:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0007_order_distance_order_duration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='duration',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
