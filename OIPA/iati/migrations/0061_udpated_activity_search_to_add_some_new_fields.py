# Generated by Django 2.0.6 on 2019-03-18 16:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iati', '0060_activity_budget_not_provided'),
    ]

    operations = [
        migrations.AddField(
            model_name='activitysearch',
            name='condition',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='activitysearch',
            name='contact_info',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='activitysearch',
            name='country_budget_items',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='activitysearch',
            name='location',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='activitysearch',
            name='other_identifier',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='activitysearch',
            name='policy_marker',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='activitysearch',
            name='related_activity',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='activitysearch',
            name='result',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='activitysearch',
            name='tag',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='activitysearch',
            name='transaction',
            field=models.TextField(null=True),
        ),
    ]
