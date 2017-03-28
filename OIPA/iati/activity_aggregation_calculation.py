from django.db.models import Sum
from django.core.exceptions import ObjectDoesNotExist

from iati.models import Activity
from iati.models import ActivityAggregation
from iati.models import ChildAggregation
from iati.models import ActivityPlusChildAggregation
from iati.transaction.models import Transaction
from django.db import IntegrityError


class ActivityAggregationCalculation():

    def parse_all_activity_aggregations(self):
        for activity in Activity.objects.all():
            self.parse_activity_aggregations(activity)

    def parse_activity_aggregations_by_source(self, dataset_id):
        for activity in Activity.objects.filter(dataset__id=dataset_id):
            self.parse_activity_aggregations(activity)

    def parse_activity_aggregations(self, activity):
        self.calculate_activity_aggregations(activity)
        self.calculate_child_aggregations(activity)
        self.calculate_activity_plus_child_aggregations(activity)
        self.update_parents_child_budgets(activity)
        activity.save()

    def update_parents_child_budgets(self, activity):

        if activity.hierarchy != 1:
            # update the parent's child budgets
            parent_activity = activity.relatedactivity_set.filter(type__code=1)
            if len(parent_activity) and parent_activity[0].ref_activity:
                parent_activity = parent_activity[0].ref_activity
                try:
                    parent_activity.activity_aggregation
                except ObjectDoesNotExist:
                    self.calculate_activity_aggregations(parent_activity)
                self.calculate_child_aggregations(parent_activity)
                self.calculate_activity_plus_child_aggregations(parent_activity)
                parent_activity.save()

    def set_aggregation(
            self,
            activity_aggregation,
            currency_field_name,
            value_field_name,
            aggregation_object):
        """

        """

        currency = None
        value = 0

        for agg_item in aggregation_object:
            currency = agg_item[0]
            if agg_item[1]:
                value = value + agg_item[1]

        if len(aggregation_object) > 1:
            # mixed currencies, set as None
            currency = None

        setattr(activity_aggregation, currency_field_name, currency)
        setattr(activity_aggregation, value_field_name, value)

        return activity_aggregation

    def calculate_activity_aggregations(self, activity):
        """

        """

        try:
            activity_aggregation = activity.activity_aggregation
        except ObjectDoesNotExist:
            activity_aggregation = ActivityAggregation()
            activity_aggregation.activity = activity

        budget_total = activity.budget_set.values_list('currency').annotate(Sum('value'))
        activity_aggregation = self.set_aggregation(
            activity_aggregation,
            'budget_currency',
            'budget_value',
            budget_total)

        incoming_fund_total = activity.transaction_set.filter(transaction_type=1).values_list('currency').annotate(Sum('value'))
        activity_aggregation = self.set_aggregation(
            activity_aggregation,
            'incoming_funds_currency',
            'incoming_funds_value',
            incoming_fund_total)

        commitment_total = activity.transaction_set.filter(transaction_type=2).values_list('currency').annotate(Sum('value'))
        activity_aggregation = self.set_aggregation(
            activity_aggregation,
            'commitment_currency',
            'commitment_value',
            commitment_total)

        disbursement_total = activity.transaction_set.filter(transaction_type=3).values_list('currency').annotate(Sum('value'))
        activity_aggregation = self.set_aggregation(
            activity_aggregation,
            'disbursement_currency',
            'disbursement_value',
            disbursement_total)

        expenditure_total = activity.transaction_set.filter(transaction_type=4).values_list('currency').annotate(Sum('value'))
        activity_aggregation = self.set_aggregation(
            activity_aggregation,
            'expenditure_currency',
            'expenditure_value',
            expenditure_total)

        # raises IntegrityError when an activity appears in multiple sources and they are parsed at the same time
        # TODO find solution that's less ugly
        try:
            activity_aggregation.save()
        except IntegrityError:
            pass

    def calculate_child_budget_aggregation(
            self,
            activity):

        return Activity.objects\
            .filter(relatedactivity__ref=activity.iati_identifier, relatedactivity__type=1,)\
            .filter(budget__currency__isnull=False)\
            .values_list('budget__currency')\
            .annotate(total_budget=Sum('budget__value'))

    def calculate_child_transaction_aggregation(
            self,
            activity,
            transaction_type):

        return Transaction.objects\
            .filter(activity__relatedactivity__ref=activity.iati_identifier, activity__relatedactivity__type=1)\
            .filter(transaction_type=transaction_type)\
            .filter(currency__isnull=False)\
            .values_list('currency')\
            .annotate(Sum('value'))

    def calculate_child_aggregations(self, activity):

        try:
            child_aggregation = activity.child_aggregation
        except ObjectDoesNotExist:
            child_aggregation = ChildAggregation()
            child_aggregation.activity = activity

        budget_total = self.calculate_child_budget_aggregation(activity)
        child_aggregation = self.set_aggregation(
            child_aggregation,
            'budget_currency',
            'budget_value',
            budget_total)

        incoming_fund_total = self.calculate_child_transaction_aggregation(activity, 1)
        child_aggregation = self.set_aggregation(
            child_aggregation,
            'incoming_funds_currency',
            'incoming_funds_value',
            incoming_fund_total)

        commitment_total = self.calculate_child_transaction_aggregation(activity, 2)
        child_aggregation = self.set_aggregation(
            child_aggregation,
            'commitment_currency',
            'commitment_value',
            commitment_total)

        disbursement_total = self.calculate_child_transaction_aggregation(activity, 3)
        child_aggregation = self.set_aggregation(
            child_aggregation,
            'disbursement_currency',
            'disbursement_value',
            disbursement_total)

        expenditure_total = self.calculate_child_transaction_aggregation(activity, 4)
        child_aggregation = self.set_aggregation(
            child_aggregation,
            'expenditure_currency',
            'expenditure_value',
            expenditure_total)

        # raises IntegrityError when an activity appears in multiple sources and they are parsed at the same time
        # TODO find solution that's less ugly
        try:
            child_aggregation.save()
        except IntegrityError:
            pass

    def update_total_aggregation(
            self,
            activity,
            total_aggregation,
            aggregation_type):
        """

        """
        activity_value = getattr(activity.activity_aggregation, aggregation_type + '_value')
        activity_currency = getattr(activity.activity_aggregation, aggregation_type + '_currency')
        child_value = getattr(activity.child_aggregation, aggregation_type + '_value')
        child_currency = getattr(activity.child_aggregation, aggregation_type + '_currency')

        total_aggregation_currency = None

        if activity_value > 0 and child_value == 0 or activity_value == child_value:
            total_aggregation_currency = activity_currency
        elif activity_value == 0 and child_value > 0:
            total_aggregation_currency = child_currency

        total_aggregation_value = activity_value + child_value

        setattr(total_aggregation, aggregation_type + '_currency', total_aggregation_currency)
        setattr(total_aggregation, aggregation_type + '_value', total_aggregation_value)

        return total_aggregation

    def calculate_activity_plus_child_aggregations(self, activity):

        try:
            total_aggregation = activity.activity_plus_child_aggregation
        except ObjectDoesNotExist:
            total_aggregation = ActivityPlusChildAggregation()
            total_aggregation.activity = activity

        total_aggregation = self.update_total_aggregation(activity, total_aggregation, 'budget')
        total_aggregation = self.update_total_aggregation(activity, total_aggregation, 'incoming_funds')
        total_aggregation = self.update_total_aggregation(activity, total_aggregation, 'commitment')
        total_aggregation = self.update_total_aggregation(activity, total_aggregation, 'disbursement')
        total_aggregation = self.update_total_aggregation(activity, total_aggregation, 'expenditure')

        # raises IntegrityError when an activity appears in multiple sources and they are parsed at the same time
        # TODO find solution that's less ugly
        try:
            total_aggregation.save()
        except IntegrityError:
            pass


