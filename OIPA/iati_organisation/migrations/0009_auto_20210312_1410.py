# Generated by Django 2.0.13 on 2021-03-12 14:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iati_organisation', '0008_auto_20201021_0844'),
    ]

    operations = [
        migrations.AlterField(
            model_name='totalexpenditureline',
            name='value',
            field=models.DecimalField(decimal_places=4, default=None, max_digits=16, null=True),
        ),
    ]
