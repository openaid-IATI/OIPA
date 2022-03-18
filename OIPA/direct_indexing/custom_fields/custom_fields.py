from direct_indexing.custom_fields.activity_dates import activity_dates
from direct_indexing.custom_fields.codelists import add_codelist_fields
from direct_indexing.custom_fields.currency_aggregation import currency_aggregation
from direct_indexing.custom_fields.currency_conversion import currency_conversion
from direct_indexing.custom_fields.dataset_metadata import dataset_metadata
from direct_indexing.custom_fields.policy_marker_combined import policy_marker_combined
from direct_indexing.custom_fields.title_narrative import title_narrative_first


def add_all(data, codelists, currencies, metadata):
    """
    Start activity processing.

    :param data: the cleaned dataset.
    :param codelists: an initialized codelist object.
    :param currencies: an initialized currencies object.
    :return: the updated dataset.
    """
    if type(data) is list:
        for activity in data:
            process_activity(activity, codelists, currencies)
            activity = {**activity, **metadata}
    else:
        process_activity(data, codelists, currencies)
        data = {**data, **metadata}

    # Currency aggregation is done on the whole dataset, rather than on the activity level
    data = currency_aggregation(data)
    return data


def process_activity(activity, codelists, currencies):
    """
    Add all custom fields as described above.

    :param activity: the cleaned dataset.
    :param codelists: an initialized codelist object.
    :param currencies: an initialized currencies object.
    :return: the updated dataset.
    """
    add_codelist_fields(activity, codelists)
    title_narrative_first(activity)
    activity_dates(activity)
    policy_marker_combined(activity)
    currency_conversion(activity, currencies)


def get_custom_metadata(metadata):
    """
    Pretty wrapper function

    :param metadata: the metadata to be processed
    :return: a subselection of the metadata
    """
    return dataset_metadata(metadata)
