# Generated by Django 2.0.13 on 2020-10-20 12:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iati', '0074_auto_20201020_1048'),
    ]

    operations = [
        migrations.AddField(
            model_name='planneddisbursement',
            name='imf_url',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='planneddisbursement',
            name='usd_exchange_rate',
            field=models.DecimalField(decimal_places=10, max_digits=15, null=True),
        ),
    ]
