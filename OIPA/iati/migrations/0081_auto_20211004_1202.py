# Generated by Django 2.0.13 on 2021-10-04 12:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iati', '0080_auto_20210903_1359'),
    ]

    operations = [
        migrations.AddField(
            model_name='activityaggregation',
            name='budget_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activityaggregation',
            name='commitment_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activityaggregation',
            name='credit_guarantee_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activityaggregation',
            name='disbursement_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activityaggregation',
            name='expenditure_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activityaggregation',
            name='incoming_commitment_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activityaggregation',
            name='incoming_funds_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activityaggregation',
            name='incoming_pledge_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activityaggregation',
            name='interest_payment_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activityaggregation',
            name='loan_repayment_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activityaggregation',
            name='outgoing_pledge_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activityaggregation',
            name='purchase_of_equity_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activityaggregation',
            name='reimbursement_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activityaggregation',
            name='sale_of_equity_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activitypluschildaggregation',
            name='budget_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activitypluschildaggregation',
            name='commitment_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activitypluschildaggregation',
            name='credit_guarantee_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activitypluschildaggregation',
            name='disbursement_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activitypluschildaggregation',
            name='expenditure_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activitypluschildaggregation',
            name='incoming_commitment_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activitypluschildaggregation',
            name='incoming_funds_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activitypluschildaggregation',
            name='incoming_pledge_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activitypluschildaggregation',
            name='interest_payment_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activitypluschildaggregation',
            name='loan_repayment_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activitypluschildaggregation',
            name='outgoing_pledge_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activitypluschildaggregation',
            name='purchase_of_equity_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activitypluschildaggregation',
            name='reimbursement_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='activitypluschildaggregation',
            name='sale_of_equity_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='childaggregation',
            name='budget_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='childaggregation',
            name='commitment_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='childaggregation',
            name='credit_guarantee_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='childaggregation',
            name='disbursement_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='childaggregation',
            name='expenditure_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='childaggregation',
            name='incoming_commitment_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='childaggregation',
            name='incoming_funds_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='childaggregation',
            name='incoming_pledge_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='childaggregation',
            name='interest_payment_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='childaggregation',
            name='loan_repayment_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='childaggregation',
            name='outgoing_pledge_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='childaggregation',
            name='purchase_of_equity_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='childaggregation',
            name='reimbursement_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='childaggregation',
            name='sale_of_equity_value_gbp',
            field=models.DecimalField(blank=True, db_index=True, decimal_places=2, max_digits=15, null=True),
        ),
    ]
