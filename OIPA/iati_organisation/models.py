from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from iati.models import OrganisationType
from iati.models import Language
from iati.models import Currency
from iati.models import FileFormat
from iati.models import DocumentCategory
from iati.models import Version
from iati.models import BudgetStatus
from geodata.models import Country
from geodata.models import Region
from iati_vocabulary.models import RegionVocabulary

from organisation_manager import OrganisationManager

#function for making url
def make_abs_url(org_identifier):
    return '/api/organisation/'+org_identifier

#narrative for adding free text to elements
class OrganisationNarrative(models.Model):

    content_type = models.ForeignKey(ContentType)
    object_id = models.IntegerField(
        verbose_name='related object',
        db_index=True,
    )
    related_object = GenericForeignKey()

    organisation = models.ForeignKey('Organisation')

    language = models.ForeignKey(Language)
    content = models.TextField()

    def __unicode__(self,):
        return "%s" % self.content[:30]

    class Meta:
        index_together = [('content_type', 'object_id')]

# organisation base class
class Organisation(models.Model):

    organisation_identifier = models.CharField(max_length=150, unique=True, db_index=True)

    iati_standard_version = models.ForeignKey(Version)
    last_updated_datetime = models.DateTimeField(blank=True, null=True)

    default_currency = models.ForeignKey(Currency, null=True)
    default_lang = models.ForeignKey(Language, null=True)

    reported_in_iati = models.BooleanField(default=True)

    # first narrative
    primary_name = models.CharField(max_length=150, db_index=True)

    objects = OrganisationManager()

    def __unicode__(self):
        return self.organisation_identifier


#class for narrative
class OrganisationName(models.Model):
    organisation = models.OneToOneField(Organisation, related_name="name")
    narratives = GenericRelation(OrganisationNarrative)


class OrganisationReportingOrganisation(models.Model):
    organisation = models.OneToOneField(Organisation, related_name='reporting_org')
    org_type = models.ForeignKey(OrganisationType, null=True, default=None)
    reporting_org = models.ForeignKey(Organisation,related_name='reported_by_orgs',null=True, db_constraint=False)
    reporting_org_identifier = models.CharField(max_length=250,null=True)
    secondary_reporter = models.BooleanField(default=False)

    narratives = GenericRelation(OrganisationNarrative)


# TODO: below this must be changed - 2016-04-20
class BudgetLine(models.Model):
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
    organisation_identifier = models.CharField(max_length=150,verbose_name='organisation_identifier',null=True)
    language = models.ForeignKey(Language, null=True, default=None)
    ref = models.CharField(max_length=150,primary_key=True)
    currency = models.ForeignKey(Currency,null=True)
    value = models.DecimalField(max_digits=14, decimal_places=2, null=True, default=None)
    value_date = models.DateField(null=True)
    narratives = GenericRelation(OrganisationNarrative)

    def get_absolute_url(self):
        return make_abs_url(self.organisation_identifier)


class TotalBudget(models.Model):
    organisation = models.ForeignKey(Organisation,related_name="total_budget")
    status = models.ForeignKey(BudgetStatus, default=1)
    period_start = models.DateField(null=True)
    period_end = models.DateField(null=True)
    value_date = models.DateField(null=True)
    currency = models.ForeignKey(Currency,null=True)
    value = models.DecimalField(max_digits=14, decimal_places=2, null=True, default=None)
    narratives = GenericRelation(OrganisationNarrative)
    budget_lines = GenericRelation(
        BudgetLine,
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name="budget_lines")


class RecipientOrgBudget(models.Model):
    organisation = models.ForeignKey(Organisation, related_name='donor_org')
    status = models.ForeignKey(BudgetStatus, default=1)
    recipient_org_identifier = models.CharField(max_length=150, verbose_name='recipient_org_identifier', null=True)
    recipient_org = models.ForeignKey(Organisation, related_name='recieving_org', db_constraint=False, null=True)
    period_start = models.DateField(null=True)
    period_end = models.DateField(null=True)
    currency = models.ForeignKey(Currency,null=True)
    narratives = GenericRelation(OrganisationNarrative)
    value = models.DecimalField(max_digits=14, decimal_places=2, null=True, default=None)
    budget_lines = GenericRelation(
        BudgetLine,
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name="budget_lines")


class RecipientCountryBudget(models.Model):
    organisation = models.ForeignKey(Organisation,related_name='recipient_country_budget')
    status = models.ForeignKey(BudgetStatus, default=1)
    country = models.ForeignKey(Country, null=True)
    period_start = models.DateField(null=True)
    period_end = models.DateField(null=True)
    currency = models.ForeignKey(Currency, null=True)
    value = models.DecimalField(max_digits=14, decimal_places=2, null=True, default=None)
    narratives = GenericRelation(OrganisationNarrative)
    budget_lines = GenericRelation(
        BudgetLine,
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name="budget_lines")


class RecipientRegionBudget(models.Model):
    organisation = models.ForeignKey(Organisation, related_name='recipient_region_budget')
    status = models.ForeignKey(BudgetStatus, default=1)
    region = models.ForeignKey(Region, null=True)
    vocabulary = models.ForeignKey(RegionVocabulary, default=1)
    vocabulary_uri = models.URLField(null=True, blank=True)
    period_start = models.DateField(null=True)
    period_end = models.DateField(null=True)
    currency = models.ForeignKey(Currency,null=True)
    value = models.DecimalField(max_digits=14, decimal_places=2, null=True, default=None)
    narratives = GenericRelation(OrganisationNarrative)
    budget_lines = GenericRelation(
        BudgetLine,
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name="budget_lines")


class TotalExpenditure(models.Model):
    organisation = models.ForeignKey(Organisation,related_name="total_expenditure")
    period_start = models.DateField(null=True)
    period_end = models.DateField(null=True)
    value_date = models.DateField(null=True)
    currency = models.ForeignKey(Currency,null=True)
    value = models.DecimalField(max_digits=14, decimal_places=2, null=True, default=None)
    narratives = GenericRelation(OrganisationNarrative)
    # using BudgetLine model for this since it has the same data
    expense_lines = GenericRelation(
        BudgetLine,
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name="expense_lines")


class DocumentLink(models.Model):
    organisation = models.ForeignKey(Organisation, related_name='documentlinks')
    url = models.TextField(max_length=500)
    file_format = models.ForeignKey(FileFormat, null=True, default=None, related_name='file_formats')
    categories = models.ManyToManyField(
        DocumentCategory,
        related_name='doc_categories')
    # title = models.CharField(max_length=255, default="")
    language = models.ForeignKey(Language, null=True, default=None, related_name='languages')
    recipient_countries = models.ManyToManyField(
        Country, blank=True,
        related_name='recipient_countries')
    iso_date = models.DateField(null=True, blank=True)

    def __unicode__(self,):
        return "%s - %s" % (self.organisation.organisation_identifier, self.url)

    def get_absolute_url(self):
        return make_abs_url(self.organisation.organisation_identifier)


# TODO: enforce one-to-one
class DocumentLinkTitle(models.Model):
    document_link = models.ForeignKey(DocumentLink, related_name='documentlinktitles')
    narratives = GenericRelation(OrganisationNarrative)

