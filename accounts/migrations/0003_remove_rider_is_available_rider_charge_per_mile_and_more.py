# Generated by Django 4.1.6 on 2024-01-24 08:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_rename_email_otp_userverification_otp_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rider',
            name='is_available',
        ),
        migrations.AddField(
            model_name='rider',
            name='charge_per_mile',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='rider',
            name='fragile_item_allowed',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='rider',
            name='max_capacity',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='rider',
            name='min_capacity',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='rider',
            name='ratings',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True),
        ),
    ]
