from datetime import date

from factory import SubFactory

from iati.factory.iati_factory import (
    ActivityFactory, CountryFactory, NoDatabaseFactory, RegionFactory, RegionVocabularyFactory, SectorFactory,
    SectorVocabularyFactory
)
from iati.transaction.models import (
    Transaction, TransactionDescription, TransactionProvider, TransactionReceiver, TransactionRecipientCountry,
    TransactionRecipientRegion, TransactionSector, TransactionType
)
from iati_codelists.factory.codelist_factory import (
    CurrencyFactory, DisbursementChannelFactory, FinanceTypeFactory, FlowTypeFactory, OrganisationTypeFactory,
    TiedStatusFactory
)


class TransactionTypeFactory(NoDatabaseFactory):
    code = "1"
    name = "Incoming Funds"
    description = ""

    class Meta:
        model = TransactionType
        django_get_or_create = ('code',)


class TransactionFactory(NoDatabaseFactory):

    activity = SubFactory(ActivityFactory)

    ref = "some-ref"
    humanitarian = True

    transaction_type = SubFactory(TransactionTypeFactory)
    transaction_date = date.today()

    value = 200
    value_string = "200"
    value_date = date.today()
    currency = SubFactory(CurrencyFactory)

    disbursement_channel = SubFactory(DisbursementChannelFactory)
    flow_type = SubFactory(FlowTypeFactory)
    finance_type = SubFactory(FinanceTypeFactory)
    tied_status = SubFactory(TiedStatusFactory)

    class Meta:
        model = Transaction


class TransactionProviderFactory(NoDatabaseFactory):
    transaction = SubFactory(TransactionFactory)
    ref = "some-ref"
    normalized_ref = "some_ref"
    provider_activity = SubFactory(ActivityFactory)
    provider_activity_ref = "IATI-0001"
    type = SubFactory(OrganisationTypeFactory)

    class Meta:
        model = TransactionProvider


class TransactionReceiverFactory(NoDatabaseFactory):
    transaction = SubFactory(TransactionFactory)
    ref = "some-ref"
    normalized_ref = "some_ref"
    receiver_activity = SubFactory(ActivityFactory)
    receiver_activity_ref = "IATI-0001"
    type = SubFactory(OrganisationTypeFactory)

    class Meta:
        model = TransactionReceiver


class TransactionDescriptionFactory(NoDatabaseFactory):
    transaction = SubFactory(TransactionFactory)

    class Meta:
        model = TransactionDescription


class TransactionSectorFactory(NoDatabaseFactory):

    transaction = SubFactory(TransactionFactory)
    sector = SubFactory(SectorFactory)
    vocabulary = SubFactory(SectorVocabularyFactory)
    vocabulary_uri = "https://twitter.com"
    percentage = 100

    reported_on_transaction = False

    class Meta:
        model = TransactionSector


class TransactionRecipientCountryFactory(NoDatabaseFactory):

    transaction = SubFactory(TransactionFactory)
    reported_transaction = SubFactory(TransactionFactory)
    country = SubFactory(CountryFactory)
    percentage = 100

    reported_on_transaction = False

    class Meta:
        model = TransactionRecipientCountry


class TransactionRecipientRegionFactory(NoDatabaseFactory):

    transaction = SubFactory(TransactionFactory)
    region = SubFactory(RegionFactory)
    vocabulary = SubFactory(RegionVocabularyFactory)
    vocabulary_uri = "https://twitter.com"
    percentage = 100

    reported_on_transaction = False

    class Meta:
        model = TransactionRecipientRegion
