from django.core.management.base import BaseCommand
from iati.transaction.models import Transaction
from iati.models import Activity
from django.conf import settings


class Command(BaseCommand):
    
    def update_searchable_activities(self):
        """
            Set all activities to searchable if the reporting org is in the settings.ROOT_ORGANISATIONS list
        """
        # set all activities as non searchable
        Activity.objects.filter(is_searchable=True).exclude(reporting_organisations__ref__in=settings.ROOT_ORGANISATIONS).update(is_searchable=False)

        # set all root activities as searchable
        Activity.objects.filter(is_searchable=False, reporting_organisations__ref__in=settings.ROOT_ORGANISATIONS).update(is_searchable=True)

        # loop through root activities and set children as searchable
        activities = Activity.objects.filter(reporting_organisations__ref__in=settings.ROOT_ORGANISATIONS)

        for activity in activities:
            self.set_children_searchable(activity)


    def set_children_searchable(self, orig_activity):
        """
            sets all the children to searchable
            recursively calls itself but keeps a list of already set activities
        """

        # all transactions where this id is given as provider activity
        provider_activity_transactions = Transaction.objects.filter(
            provider_organisation__provider_activity_id=orig_activity.id)

        for transaction in provider_activity_transactions:
            activity = transaction.activity
            if not activity.is_searchable:
                activity.is_searchable = True
                activity.save()
                self.set_children_searchable(activity)
        return

    def handle(self, *args, **options):
        self.update_searchable_activities()


