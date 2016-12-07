from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.filters import DjangoFilterBackend

from rest_framework.viewsets import ModelViewSet

from api.activity import serializers as activitySerializers
from api.activity import filters
from api.generics.filters import DistanceFilter
from api.generics.filters import SearchFilter
from api.generics.views import DynamicListView, DynamicDetailView
from api.transaction.serializers import TransactionSerializer
from api.activity.tree_serializers import ActivityTree
from api.transaction.filters import TransactionFilter

from api.aggregation.views import AggregationView, Aggregation, GroupBy

from django.db.models import Count, Sum, F


from geodata.models import Country
from geodata.models import Region
import iati.models as iati_models
from iati.models import Activity
from iati.models import Sector
from iati.models import ActivityStatus
from iati.models import PolicyMarker
from iati.models import CollaborationType
from iati.models import DocumentCategory
from iati.models import FlowType
from iati.models import AidType
from iati.models import FinanceType
from iati.models import TiedStatus
from iati.models import ActivityParticipatingOrganisation
from iati.models import OrganisationType
from iati.models import Organisation
from iati.models import PolicySignificance

from api.activity.serializers import CodelistSerializer
from api.country.serializers import CountrySerializer
from api.region.serializers import RegionSerializer
from api.sector.serializers import SectorSerializer
from api.organisation.serializers import OrganisationSerializer



class ActivityAggregations(AggregationView):
    """
    Returns aggregations based on the item grouped by, and the selected aggregation.

    ## Group by options

    API request has to include `group_by` parameter.
    
    This parameter controls result aggregations and
    can be one or more (comma separated values) of:

    - `recipient_country`
    - `recipient_region`
    - `sector`
    - `related_activity`
    - `reporting_organisation`
    - `participating_organisation`
    - `participating_organisation_type`
    - `document_link_category`
    - `activity_status`
    - `collaboration_type`

    ## Aggregation options

    API request has to include `aggregations` parameter.
    
    This parameter controls result aggregations and
    can be one or more (comma separated values) of:

    - `count`
    - `count_distinct`

    ## Request parameters

    All filters available on the Activity List, can be used on aggregations.

    """

    queryset = Activity.objects.all()

    filter_backends = (SearchFilter, DjangoFilterBackend,)
    filter_class = filters.ActivityFilter

    allowed_aggregations = (
        Aggregation(
            query_param='count',
            field='count',
            annotate=Count('id'),
        ),
        Aggregation(
            query_param='count_distinct',
            field='count',
            annotate=Count('id', distinct=True),
        ),
    )

    allowed_groupings = (
        GroupBy(
            query_param="recipient_country",
            fields="recipient_country",
            queryset=Country.objects.all(),
            serializer=CountrySerializer,
            serializer_fields=('url', 'code', 'name', 'location'),
            name_search_field='recipient_country__name',
            renamed_name_search_field='recipient_country_name',
        ),  
        GroupBy(
            query_param="recipient_region",
            fields="recipient_region",
            queryset=Region.objects.all(),
            serializer=RegionSerializer,
            serializer_fields=('url', 'code', 'name', 'location'),
            name_search_field="recipient_region__name",
            renamed_name_search_field="recipient_region_name",
        ),
        GroupBy(
            query_param="sector",
            fields="sector",
            queryset=Sector.objects.all(),
            serializer=SectorSerializer,
            serializer_fields=('url', 'code', 'name', 'location'),
            name_search_field="sector__name",
            renamed_name_search_field="sector_name",
        ),
        GroupBy(
            query_param="related_activity",
            fields=("relatedactivity__ref_activity__id"),
            renamed_fields="related_activity",
        ),
        GroupBy(
            query_param="reporting_organisation",
            fields="reporting_organisations__normalized_ref",
            renamed_fields="reporting_organisation",
            queryset=Organisation.objects.all(),
            serializer=OrganisationSerializer,
            serializer_main_field='organisation_identifier',
            name_search_field="reporting_organisations__organisation__primary_name",
            renamed_name_search_field="reporting_organisation_name"
        ),
        GroupBy(
            query_param="participating_organisation",
            fields=("participating_organisations__primary_name", "participating_organisations__normalized_ref"),
            renamed_fields=("participating_organisation", "participating_organisation_ref"),
            queryset=ActivityParticipatingOrganisation.objects.all(),
            name_search_field="participating_organisations__primary_name",
            renamed_name_search_field="participating_organisation_name"
        ),
        GroupBy(
            query_param="participating_organisation_type",
            fields="participating_organisations__type",
            renamed_fields="participating_organisation_type",
            queryset=OrganisationType.objects.all(),
            serializer=CodelistSerializer,
            name_search_field="participating_organisations__type__name",
            renamed_name_search_field="participating_organisations_type_name"
        ),
        GroupBy(
            query_param="document_link_category",
            fields="documentlink__categories__code",
            renamed_fields="document_link_category",
            queryset=DocumentCategory.objects.all(),
            serializer=CodelistSerializer,
            name_search_field="documentlink__categories__name",
            renamed_name_search_field="document_link_category_name"
        ),
        GroupBy(
            query_param="activity_status",
            fields="activity_status",
            queryset=ActivityStatus.objects.all(),
            serializer=CodelistSerializer,
            name_search_field="activity_status__name",
            renamed_name_search_field="activity_status_name"
        ),
        GroupBy(
            query_param="collaboration_type",
            fields="collaboration_type",
            renamed_fields="collaboration_type",
            queryset=CollaborationType.objects.all(),
            serializer=CodelistSerializer,
            name_search_field="collaboration_type__name",
            renamed_name_search_field="collaboration_type_name"
        ),
        GroupBy(
            query_param="policy_marker_significance",
            fields="activitypolicymarker__significance",
            renamed_fields="significance",
            queryset=PolicySignificance.objects.all(),
            serializer=CodelistSerializer,
        ),
    )


class ActivityList(DynamicListView):
    """
    Returns a list of IATI Activities stored in OIPA.

    ## Request parameters
    - `activity_id` (*optional*): Comma separated list of activity id's.
    - `activity_scope` (*optional*): Comma separated list of iso2 country codes.
    - `recipient_country` (*optional*): Comma separated list of iso2 country codes.
    - `recipient_region` (*optional*): Comma separated list of region codes.
    - `recipient_region_not_in` (*optional*): Comma separated list of region codes the activity should not be in.
    - `sector` (*optional*): Comma separated list of 5-digit sector codes.
    - `sector_category` (*optional*): Comma separated list of 3-digit sector codes.
    - `reporting_organisation` (*optional*): Comma separated list of organisation id's.
    - `participating_organisation` (*optional*): Comma separated list of organisation id's.
    - `total_budget_value_lte` (*optional*): Less then or equal total budget value
    - `total_budget_value_gte` (*optional*): Greater then or equal total budget value
    - `total_child_budget_value_lte` (*optional*): Less then or equal total child budget value
    - `total_child_budget_value_gte` (*optional*): Greater then or equal total child budget value
    - `planned_start_date_lte` (*optional*): Date in YYYY-MM-DD format, returns activities earlier or equal to the given activity date.
    - `planned_start_date_gte` (*optional*): Date in YYYY-MM-DD format, returns activities later or equal to the given activity date.
    - `actual_start_date_lte` (*optional*): Date in YYYY-MM-DD format, returns activities earlier or equal to the given activity date.
    - `actual_start_date_gte` (*optional*): Date in YYYY-MM-DD format, returns activities later or equal to the given activity date.
    - `planned_end_date_lte` (*optional*): Date in YYYY-MM-DD format, returns activities earlier or equal to the given activity date.
    - `planned_end_date_gte` (*optional*): Date in YYYY-MM-DD format, returns activities later or equal to the given activity date.
    - `actual_end_date_lte` (*optional*): Date in YYYY-MM-DD format, returns activities earlier or equal to the given activity date.
    - `actual_end_date_gte` (*optional*): Date in YYYY-MM-DD format, returns activities later or equal to the given activity date.
    - `activity_status` (*optional*): Comma separated list of activity statuses.
    - `hierarchy` (*optional*): Comma separated list of activity hierarchies.
    - `related_activity_id` (*optional*): Comma separated list of activity ids. Returns a list of all activities mentioning these activity id's.
    - `related_activity_type` (*optional*): Comma separated list of RelatedActivityType codes.
    - `related_activity_recipient_country` (*optional*): Comma separated list of iso2 country codes.
    - `related_activity_recipient_region` (*optional*): Comma separated list of region codes.
    - `related_activity_sector` (*optional*): Comma separated list of 5-digit sector codes.
    - `related_activity_sector_category` (*optional*): Comma separated list of 3-digit sector codes.
    - `transaction_provider_activity` (*optional*): Comma separated list of activity id's.
    - `transaction_date_year` (*optional*): Comma separated list of years in which the activity should have transactions.

    ## Text search

    API request may include `q` parameter. This parameter controls text search
    and contains expected value.

    By default, searching is performed on:

    - `iati_identifier` the IATI identifier
    - `title` narratives
    - `description` narratives
    - `recipient_country` recipient country code and name
    - `recipient_region` recipient region code and name
    - `reporting_org` ref and narratives
    - `sector` sector code and name
    - `document_link` url, category and title narratives
    - `participating_org` ref and narratives

    To search on subset of these fields the `q_fields` parameter can be used, like so;
    `q_fields=iati_identifier,title,description`

    By default, search only return results if the hit resembles a full word. 
    This can be altered through the `q_lookup` parameter. Options for this parameter are:

    - `exact` (default): Only return results when the query hit is a full word.
    - `startswith`: Also returns results when the word stars with the query. 

    ## Ordering

    API request may include `ordering` parameter. This parameter controls the order in which
    results are returned.

    Results can be ordered by:

    - `title`
    - `planned_start_date`
    - `actual_start_date`
    - `planned_end_date`
    - `actual_end_date`
    - `start_date`
    - `end_date`
    - `activity_budget_value`
    - `activity_incoming_funds_value`
    - `activity_disbursement_value`
    - `activity_expenditure_value`
    - `activity_plus_child_budget_value`

    The user may also specify reverse orderings by prefixing the field name with '-', like so: `-title`

    ## Aggregations

    At the moment there's no direct aggregations on this endpoint.

    The /activities/aggregations endpoint can be used for activity based aggregations.

    ## Result details

    Each item contains summarized information on the activity being shown,
    including the URI to activity details, which contain all information. 
    To show more information in list view the `fields` parameter can be used. Example;
    `fields=activity_id,title,country,any_field`.

    """

    queryset = Activity.objects.all()
    filter_backends = (SearchFilter, DjangoFilterBackend, DistanceFilter, filters.RelatedOrderingFilter,)
    filter_class = filters.ActivityFilter
    serializer_class = activitySerializers.ActivitySerializer

    fields = (
        'url', 
        'iati_identifier', 
        'title', 
        'descriptions', 
        'transactions', 
        'reporting_organisations')

    always_ordering = 'id'

    ordering_fields = (
        'title',
        'recipient_country',
        'planned_start_date',
        'actual_start_date',
        'planned_end_date',
        'actual_end_date',
        'start_date',
        'end_date',
        'activity_budget_value',
        'activity_incoming_funds_value',
        'activity_disbursement_value',
        'activity_expenditure_value',
        'activity_plus_child_budget_value')


class ActivityDetail(DynamicDetailView):
    """
    Returns detailed information about Activity.

    ## URI Format

    ```
    /api/activities/{activity_id}
    ```

    ### URI Parameters

    - `activity_id`: Desired activity ID

    ## Extra endpoints

    All information on activity transactions can be found on a separate page:

    - `/api/activities/{activity_id}/transactions/`:
        List of transactions.
    - `/api/activities/{activity_id}/provider-activity-tree/`:
        The upward and downward provider-activity-id traceability tree of this activity.

    ## Request parameters

    - `fields` (*optional*): List of fields to display

    """
    queryset = Activity.objects.all()
    filter_class = filters.ActivityFilter
    serializer_class = activitySerializers.ActivitySerializer

# TODO separate endpoints for expensive fields like ActivityLocations & ActivityResults 08-07-2016


class ActivityTransactions(ListAPIView):
    """
    Returns a list of IATI Activity Transactions stored in OIPA.

    ## URI Format

    ```
    /api/activities/{activity_id}/transactions
    ```

    ### URI Parameters

    - `activity_id`: Desired activity ID

    ## Request parameters:

    - `recipient_country` (*optional*): Recipient countries list.
        Comma separated list of strings.
    - `recipient_region` (*optional*): Recipient regions list.
        Comma separated list of integers.
    - `sector` (*optional*): Sectors list. Comma separated list of integers.
    - `sector_category` (*optional*): Sectors list. Comma separated list of integers.
    - `reporting_organisations` (*optional*): Organisation ID's list.
    - `participating_organisations` (*optional*): Organisation IDs list.
        Comma separated list of strings.
    - `min_total_budget` (*optional*): Minimal total budget value.
    - `max_total_budget` (*optional*): Maximal total budget value.
    - `activity_status` (*optional*):


    - `related_activity_id` (*optional*):
    - `related_activity_type` (*optional*):
    - `related_activity_recipient_country` (*optional*):
    - `related_activity_recipient_region` (*optional*):
    - `related_activity_sector` (*optional*):

    ## Searching is performed on fields:

    - `description`
    - `provider_organisation_name`
    - `receiver_organisation_name`

    """
    serializer_class = TransactionSerializer
    filter_class = TransactionFilter


    def get_queryset(self):
        pk = self.kwargs.get('pk')
        return Activity(pk=pk).transaction_set.all()


class ActivityProviderActivityTree(DynamicDetailView):
    """
    Returns the upward and downward traceability tree of this activity. Field specification:
    
    - `providing activities`: The upward three of all activities that are listed as provider-activity-id in this activity.
    - `receiving activities`: The downward tree of all activities that list this activity as provider-activity-id.

    ## URI Format

    ```
    /api/activities/{activity_id}/provider-activity-tree
    ```
    """
    serializer_class = ActivityTree
    queryset = Activity.objects.all()



class SectorCrudModelViewSet(ModelViewSet):
    serializer_class = activitySerializers.SectorCrudAssociateSerializer
    queryset = iati_models.Activity.objects.all()







