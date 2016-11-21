# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-11-21 16:13
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('iati', '0058_auto_20161108_1720'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transactionrecipientcountry',
            name='transaction',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='iati.Transaction'),
        ),
        migrations.AlterField(
            model_name='transactionrecipientregion',
            name='transaction',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='iati.Transaction'),
        ),
    ]
