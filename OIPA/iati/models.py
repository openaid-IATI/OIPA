from django.db import models
from geodata.models import Country, Region
from activity_manager import ActivityQuerySet
from organisation_manager import OrganisationQuerySet # from django.contrib.gis.geos import Point
from django.contrib.gis.db.models import PointField
# from iati.transaction.models import Transaction, TransactionType, TransactionDescription, TransactionProvider, TransactionReceiver, TransactionSector
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from iati_codelists.models import *
from iati_vocabulary.models import RegionVocabulary, GeographicVocabulary, PolicyMarkerVocabulary, SectorVocabulary, BudgetIdentifierVocabulary

# TODO: separate this
class Narrative(models.Model):
    content_type = models.ForeignKey(
        ContentType,
        verbose_name='xml Parent',
        null=True,
        blank=True,
    )
    object_id = models.CharField(
        max_length=250,
        verbose_name='related object',
        null=True,
    )
    parent_object = GenericForeignKey('content_type', 'object_id')
    language = models.ForeignKey(Language, null=True, default=None)
    iati_identifier = models.CharField(max_length=150,verbose_name='iati_identifier',null=True)
    content = models.TextField(null=True,blank=True)

class Title(models.Model):
    # activity = models.ForeignKey(Activity)
    narratives = GenericRelation(Narrative)

    def __unicode__(self,):
        return "Title"

class Activity(models.Model):
    hierarchy_choices = (
        (1, u"Parent"),
        (2, u"Child"),
    )
    
    title = models.OneToOneField(Title, null=True) # todo: remove null=true

    id = models.CharField(max_length=150,primary_key=True,blank=False)
    iati_identifier = models.CharField(max_length=150, blank=False)

    iati_standard_version = models.ForeignKey(Version)
    xml_source_ref = models.CharField(max_length=200, default="")

    default_currency = models.ForeignKey(Currency, null=True, default=None, related_name="default_currency")
    hierarchy = models.SmallIntegerField(choices=hierarchy_choices, default=1, null=True)
    # last_updated_datetime = models.CharField(max_length=100, default="")
    # value_date = models.DateField(null=True)
    last_updated_datetime = models.DateTimeField(max_length=100, blank=True, null=True)
    default_lang = models.CharField(max_length=2)
    linked_data_uri = models.CharField(max_length=100, blank=True, null=True, default="")
    activity_status = models.ForeignKey(
        ActivityStatus,
        null=True,
        default=None)

    # reporting_organisation = models.ForeignKey(
    #     Organisation,
    #     null=True,
    #     default=None,
    #     related_name="activity_reporting_organisation")
    # reporting_organisation = models.ManyToManyField(
    #     Organisation,
    #     related_name="reporting_organisations",
    #     through="ActivityReportingOrganisation")
    # participating_organisation = models.ManyToManyField(
    #     Organisation,
    #     related_name="participating_organisations",
    #     through="ActivityParticipatingOrganisation")
    policy_marker = models.ManyToManyField(
        PolicyMarker,
        through="ActivityPolicyMarker")
    sector = models.ManyToManyField(
        Sector,
        through="ActivitySector")
    recipient_country = models.ManyToManyField(
        Country,
        through="ActivityRecipientCountry")
    recipient_region = models.ManyToManyField(
        Region,
        through="ActivityRecipientRegion")

    collaboration_type = models.ForeignKey(
        CollaborationType,
        null=True,
        default=None)
    default_flow_type = models.ForeignKey(FlowType, null=True, default=None)
    default_aid_type = models.ForeignKey(AidType, null=True, default=None)
    default_finance_type = models.ForeignKey(FinanceType, null=True, default=None)
    default_tied_status = models.ForeignKey(TiedStatus, null=True, default=None)
    scope = models.ForeignKey(ActivityScope, null=True, default=None)

    capital_spend = models.DecimalField(max_digits=5, decimal_places=2, null=True, default=None) # @percentage on capital-spend
    has_conditions = models.BooleanField(default=False) # @attached on iati-conditions

    objects = ActivityQuerySet.as_manager()

    def __unicode__(self):
        return self.id

    class Meta:
        verbose_name_plural = "activities"

class ActivitySearchData(models.Model):
    activity = models.OneToOneField(Activity)
    search_identifier = models.CharField(db_index=True, max_length=150)
    search_description = models.TextField(max_length=80000)
    search_title = models.TextField(max_length=80000)
    search_country_name = models.TextField(max_length=80000)
    search_region_name = models.TextField(max_length=80000)
    search_sector_name = models.TextField(max_length=80000)
    search_participating_organisation_name = models.TextField(max_length=80000)
    search_reporting_organisation_name = models.TextField(max_length=80000)
    search_documentlink_title = models.TextField(max_length=80000)

# TODO: move this to a separate django app along with other organisation-related models
class Organisation(models.Model):
    code = models.CharField(max_length=250,primary_key=True)
    abbreviation = models.CharField(max_length=120, default="")
    type = models.ForeignKey(OrganisationType, null=True, default=None)
    reported_by_organisation = models.CharField(max_length=150, default="")
    name = models.CharField(max_length=250, default="")
    original_ref = models.CharField(max_length=120, default="")

    is_whitelisted = models.BooleanField(default=False) # for organisation fixture work-around

    def __unicode__(self):
        return self.name

    def total_activities(self):
        return self.activity_set.count()

    objects = OrganisationQuerySet.as_manager()

class ActivityReportingOrganisation(models.Model):
    ref = models.CharField(max_length=250)
    normalized_ref = models.CharField(max_length=120, default="")

    narratives = GenericRelation(Narrative)
    activity = models.ForeignKey(
        Activity,
        related_name="reporting_organisations"
        )
    organisation = models.ForeignKey(Organisation, null=True, default=None) # if in organisation standard
    type = models.ForeignKey(OrganisationType, null=True, default=None)

    secondary_reporter = models.BooleanField(default=False)

class ActivityParticipatingOrganisation(models.Model):
    ref = models.CharField(max_length=250)
    normalized_ref = models.CharField(max_length=120, default="")

    activity = models.ForeignKey(
        Activity,
        related_name="participating_organisations"
        )
    organisation = models.ForeignKey(Organisation, null=True, default=None) # if in organisation standard

    type = models.ForeignKey(OrganisationType, null=True, default=None)
    role = models.ForeignKey(OrganisationRole, null=True, default=None)

    narratives = GenericRelation(Narrative)

    def __unicode__(self,):
        return "%s: %s" % (self.activity.id, self.ref)

class ActivityPolicyMarker(models.Model):
    activity = models.ForeignKey(Activity)
    code = models.ForeignKey(PolicyMarker)
    vocabulary = models.ForeignKey(PolicyMarkerVocabulary)
    significance = models.ForeignKey(
        PolicySignificance,
        null=True,
        default=None)
    narratives = GenericRelation(Narrative)

    def __unicode__(self,):
        return "%s - %s - %s" % (self.activity.id, self.code, self.significance.code)

class ActivitySector(models.Model):
    activity = models.ForeignKey(Activity)
    sector = models.ForeignKey(Sector, null=True, default=None)
    vocabulary = models.ForeignKey(SectorVocabulary, null=True, default=None)
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        default=None)

    def __unicode__(self,):
        return "%s - %s" % (self.activity.id, self.sector)

class ActivityRecipientCountry(models.Model):
    activity = models.ForeignKey(Activity)
    country = models.ForeignKey(Country)
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        default=None)

    def __unicode__(self,):
        return "%s - %s" % (self.activity.id, self.country)

class CountryBudgetItem(models.Model):
    activity = models.ForeignKey(Activity)
    vocabulary = models.ForeignKey(BudgetIdentifierVocabulary)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, default=None)

class BudgetItem(models.Model):
    country_budget_item = models.ForeignKey(CountryBudgetItem)
    code = models.ForeignKey(BudgetIdentifier)
    # code = models.CharField(max_length=50)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, default=None)

class BudgetItemDescription(models.Model):
    budget_item = models.ForeignKey(BudgetItem)
    narratives = GenericRelation(Narrative)

class ActivityRecipientRegion(models.Model):
    activity = models.ForeignKey(Activity)
    region = models.ForeignKey(Region)
    vocabulary = models.ForeignKey(RegionVocabulary, default=1)
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        default=None)

    def __unicode__(self,):
        return "%s - %s" % (self.activity.id, self.region)

class OtherIdentifier(models.Model):
    activity = models.ForeignKey(Activity)
    identifier = models.CharField(max_length=100)
    owner_ref = models.CharField(max_length=100, default="")
    # owner_name = models.CharField(max_length=100, default="")
    narratives = GenericRelation(Narrative)
    type = models.ForeignKey(OtherIdentifierType,null=True)

    def __unicode__(self,):
        return "%s - %s" % (self.activity.id, self.identifier)

class ActivityWebsite(models.Model):
    activity = models.ForeignKey(Activity)
    url = models.URLField()

    def __unicode__(self,):
        return "%s - %s" % (self.activity.id, self.url)


#   Class not truly correct, attributes fully open
class ContactInfo(models.Model):
    activity = models.ForeignKey(Activity)
    type = models.ForeignKey(ContactType, null=True)
    # person_name = GenericRelation(Narrative, related_query_name="person_name")
    # organisation = GenericRelation(ContactInfoOrganisationNarrative)
    # person_name = models.CharField(max_length=100, default="", null=True, blank=True)
    # organisation = models.CharField(max_length=100, default="", null=True, blank=True)
    telephone = models.CharField(max_length=100, default="", null=True, blank=True)
    email = models.TextField(default="", null=True, blank=True)
    mailing_address = models.TextField(default="", null=True, blank=True)
    website = models.CharField(max_length=255, default="", null=True, blank=True)
    job_title = models.CharField(max_length=150, default="", null=True, blank=True)

    def __unicode__(self,):
        return "ContactInfo: %s" % (self.activity.id)

# class ContactInfoOrganisationNarrative(Narrative):
#     pass
# TODO: inherit narratives and link from contactinfo? (API inconsistency?)

class ContactInfoOrganisation(models.Model):
    contact_info = models.ForeignKey(ContactInfo)
    narratives = GenericRelation(Narrative)

class ContactInfoDepartment(models.Model):
    contact_info = models.ForeignKey(ContactInfo)
    narratives = GenericRelation(Narrative)

class ContactInfoPersonName(models.Model):
    contact_info = models.ForeignKey(ContactInfo)
    narratives = GenericRelation(Narrative)

class ContactInfoJobTitle(models.Model):
    contact_info = models.ForeignKey(ContactInfo)
    narratives = GenericRelation(Narrative)

class ContactInfoMailingAddress(models.Model):
    contact_info = models.ForeignKey(ContactInfo)
    narratives = GenericRelation(Narrative)

class ContactInfoTelephone(models.Model):
    contact_info = models.ForeignKey(ContactInfo)
    narratives = GenericRelation(Narrative)

# class transaction_description(models.Model):
#     transaction = models.ForeignKey(transaction)
#     type = models.ForeignKey(description_type, null=True, default=None)
#     language = models.ForeignKey(language, null=True, default=None)
#     description = models.TextField(default="")
#
#     def __unicode__(self,):
#         return "%s - %s" % (self.code, self.name)

class PlannedDisbursement(models.Model):
    budget_type = models.ForeignKey(BudgetType, null=True, default=None)
    activity = models.ForeignKey(Activity)
    period_start = models.CharField(max_length=100, default="")
    period_end = models.CharField(max_length=100, default="")
    value_date = models.DateField(null=True)
    value = models.DecimalField(max_digits=15, decimal_places=2)
    value_string = models.CharField(max_length=50)
    currency = models.ForeignKey(Currency, null=True, default=None)
    # updated = models.DateField(null=True, default=None) deprecated

    def __unicode__(self,):
        return "%s - %s" % (self.activity.id, self.period_start)

class RelatedActivity(models.Model):
    current_activity = models.ForeignKey(
        Activity,
        related_name="current_activity",
        on_delete=models.CASCADE)
    related_activity = models.ForeignKey(
        Activity,
        related_name="related_activity", 
        null=True,
        on_delete=models.SET_NULL)
    type = models.ForeignKey(
        RelatedActivityType,
        max_length=200,
        null=True,
        default=None)
    ref = models.CharField(max_length=200, default="")

    def __unicode__(self,):
        return "%s" % (self.ref)

class DocumentLink(models.Model):
    activity = models.ForeignKey(Activity)
    url = models.TextField(max_length=500)
    file_format = models.ForeignKey(FileFormat, null=True, default=None)
    categories = models.ManyToManyField(
        DocumentCategory,
        through="DocumentLinkCategory")

    def __unicode__(self,):
        return "%s - %s" % (self.activity.id, self.url)

# enables saving before parent object is saved (workaround)
# TODO: eliminate the need for this
class DocumentLinkCategory(models.Model):
    document_link = models.ForeignKey(DocumentLink)
    category = models.ForeignKey(DocumentCategory)

class DocumentLinkLanguage(models.Model):
    document_link = models.ForeignKey(DocumentLink)
    language = models.ForeignKey(Language, null=True, default=None)

# TODO: enforce one-to-one
class DocumentLinkTitle(models.Model):
    document_link = models.ForeignKey(DocumentLink)
    narratives = GenericRelation(Narrative)

class Result(models.Model):
    activity = models.ForeignKey(Activity)
    type = models.ForeignKey(ResultType, null=True, default=None)
    aggregation_status = models.BooleanField(default=False)

    def __unicode__(self,):
        return "%s - %s" % (self.activity.id, self.title)

class ResultTitle(models.Model):
    result = models.ForeignKey(Result)
    narratives = GenericRelation(Narrative)

class ResultDescription(models.Model):
    result = models.ForeignKey(Result)
    narratives = GenericRelation(Narrative)

class ResultIndicator(models.Model):
    result = models.ForeignKey(Result)
    title = models.CharField(max_length=200, default="")
    description = models.TextField(default="")
    baseline_year = models.IntegerField()
    baseline_value = models.CharField(max_length=100)
    comment = models.TextField(default="")
    measure = models.ForeignKey(
        IndicatorMeasure,
        null=True,
        default=None)

    def __unicode__(self,):
        return "%s - %s" % (self.result, self.year)

class ResultIndicatorMeasure(models.Model):
    result_indicator = models.ForeignKey(ResultIndicator)

class ResultIndicatorTitle(models.Model):
    result_indicator = models.ForeignKey(ResultIndicator)

class ResultIndicatorDescription(models.Model):
    result_indicator = models.ForeignKey(ResultIndicator)

class ResultIndicatorBaseLineComment(models.Model):
    result_indicator = models.ForeignKey(ResultIndicator)

class ResultIndicatorPeriod(models.Model):
    result_indicator = models.ForeignKey(ResultIndicator)
    period_start = models.CharField(max_length=50, default="")
    period_end = models.CharField(max_length=50, default="")
    planned_disbursement_period_start = models.CharField(
        max_length=50, default="")
    planned_disbursement_period_end = models.CharField(
        max_length=50, default="")
    target = models.CharField(max_length=50, default="")
    actual = models.CharField(max_length=50, default="")

    def __unicode__(self,):
        return "%s" % self.result_indicator

class ResultIndicatorPeriodTargetComment(models.Model):
    result_indicator_period = models.ForeignKey(ResultIndicatorPeriod)

class ResultIndicatorPeriodActualComment(models.Model):
    result_indicator_period = models.ForeignKey(ResultIndicatorPeriod)

class Description(models.Model):
    activity = models.ForeignKey(Activity)
    narratives = GenericRelation(Narrative)

    type = models.ForeignKey( # TODO: set a default or require
        DescriptionType,
        related_name="description_type",
        null=True,
        default=None)

    def __unicode__(self,):
        return "Description: %s - %s" % (self.activity.id, self.type)

class Budget(models.Model):
    activity = models.ForeignKey(Activity)
    type = models.ForeignKey(BudgetType, null=True, default=None)
    period_start = models.CharField(max_length=50, default="")
    period_end = models.CharField(max_length=50, default="")
    value = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    value_string = models.CharField(max_length=50)
    value_date = models.DateField(null=True, default=None)
    currency = models.ForeignKey(Currency, null=True, default=None)

    def __unicode__(self,):
        return "%s - %s" % (self.activity.id, self.period_start)

class Condition(models.Model):
    activity = models.ForeignKey(Activity)
    text = models.TextField(default="")
    type = models.ForeignKey(ConditionType, null=True, default=None)

    def __unicode__(self,):
        return "%s - %s" % (self.activity.id, self.type)

class Location(models.Model):
    activity = models.ForeignKey(Activity)

    ref = models.CharField(max_length=200, default="")
    location_reach = models.ForeignKey(
        GeographicLocationReach,
        null=True,
        default=None,
        related_name="location_reach")

    # TODO: make location_id a one-to-one field?
    location_id_vocabulary = models.ForeignKey(
        GeographicVocabulary,
        null=True,
        default=None,
        related_name="location_id_vocabulary")
    location_id_code = models.CharField(max_length=255, default="")

    location_class = models.ForeignKey(
        GeographicLocationClass,
        null=True,
        default=None)
    feature_designation = models.ForeignKey(
        LocationType,
        null=True,
        default=None,
        related_name="feature_designation")

    point_srs_name = models.CharField(max_length=255, default="")
    point_pos = PointField(null=True, blank=True)
    exactness = models.ForeignKey(GeographicExactness, null=True, default=None)

    def __unicode__(self,):
        return "Location: %s" % (self.activity.id,)

# TODO: move to codelist
class LocationAdministrative(models.Model):
    location = models.ForeignKey(Location)
    code = models.CharField(max_length=255)
    vocabulary = models.ForeignKey(
        GeographicVocabulary,
        related_name="administrative_vocabulary")
    level = models.IntegerField(null=True, default=None)

class LocationName(models.Model):
    location = models.ForeignKey(Location)
    narratives = GenericRelation(Narrative)

class LocationDescription(models.Model):
    location = models.ForeignKey(Location)
    narratives = GenericRelation(Narrative)

class LocationActivityDescription(models.Model):
    location = models.ForeignKey(Location)
    narratives = GenericRelation(Narrative)

class Fss(models.Model):
    activity = models.ForeignKey(Activity)
    extraction_date = models.DateField(null=True, default=None)
    priority = models.BooleanField(default=False)
    phaseout_year = models.IntegerField(null=True)

    def __unicode__(self,):
        return "%s" % (self.extraction_date)

class FssForecast(models.Model):
    fss = models.ForeignKey(Fss)
    year = models.IntegerField(null=True)
    currency = models.ForeignKey(Currency)
    value_date = models.DateField(null=True, default=None)
    value = models.DecimalField(max_digits=15, decimal_places=2)

    def __unicode__(self,):
        return "%s" % self.year

class CrsAdd(models.Model):
    activity = models.ForeignKey(Activity)

    def __unicode__(self,):
        return "%s" % (self.id)

class CrsAddOtherFlags(models.Model):
    crs_add = models.ForeignKey(CrsAdd)
    other_flags = models.ForeignKey(OtherFlags)
    other_flags_significance = models.IntegerField(null=True, default=None)

    def __unicode__(self,):
        return "%s" % self.id

class CrsAddLoanTerms(models.Model):
    crs_add = models.ForeignKey(CrsAdd)
    rate_1 = models.IntegerField(null=True, default=None)
    rate_2 = models.IntegerField(null=True, default=None)
    repayment_type = models.ForeignKey(
        LoanRepaymentType,
        null=True,
        default=None)
    repayment_plan = models.ForeignKey(
        LoanRepaymentPeriod,
        null=True,
        default=None)
    repayment_plan_text = models.TextField(null=True, default="")
    commitment_date = models.DateField(null=True, default=None)
    repayment_first_date = models.DateField(null=True, default=None)
    repayment_final_date = models.DateField(null=True, default=None)

    def __unicode__(self,):
        return "%s" % (self.crs_add_id)

class CrsAddLoanStatus(models.Model):
    crs_add = models.ForeignKey(CrsAdd)
    year = models.IntegerField(null=True, default=None)
    value_date = models.DateField(null=True, default=None)
    currency = models.ForeignKey(Currency, null=True, default=None)
    interest_received = models.DecimalField(
        null=True,
        default=None,
        max_digits=15,
        decimal_places=2)
    principal_outstanding = models.DecimalField(
        null=True,
        default=None,
        max_digits=15,
        decimal_places=2)
    principal_arrears = models.DecimalField(
        null=True,
        default=None,
        max_digits=15,
        decimal_places=2)
    interest_arrears = models.DecimalField(
        null=True,
        default=None,
        max_digits=15,
        decimal_places=2)

    def __unicode__(self):
        return "%s" % (self.year)

class ActivityDate(models.Model):
    activity = models.ForeignKey(Activity)
    iso_date = models.DateTimeField()
    type = models.ForeignKey(ActivityDateType)

    def __unicode__(self):
        return "%s - %s - %s" % (self.activity.id, self.type.name, self.iso_date.strftime('%Y-%m-%d'))

class LegacyData(models.Model):
    activity = models.ForeignKey(Activity)
    name = models.CharField(max_length=150, null=True)
    value = models.CharField(max_length=200, null=True)
    iati_equivalent = models.CharField(max_length=150, null=True)

    def __unicode__(self):
        return "%s" % self.name
