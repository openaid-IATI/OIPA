import logging

from django.conf import settings
from pymongo import MongoClient
from pymongo.errors import PyMongoError

MONGO_UNWIND = '$unwind'
MONGO_GROUP = '$group'
MONGO_IID = '$iati-identifier'

TVU_DASHES = 'transaction-value-usd'
TVU_CLEAN = 'transaction.value-usd'
TVU_DASHES_TYPE = 'transaction-value-usd-type'
TVU_CLEAN_TYPE = 'transaction.value-usd-type'
TVU_DASHES_GBP = 'transaction-value-gbp'
TVU_CLEAN_GBP = 'transaction.value-gbp'
TVU_DASHES_TYPE_GBP = 'transaction-value-gbp-type'
TVU_CLEAN_TYPE_GBP = 'transaction.value-gbp-type'

BV_USD_CURR = 'budget.value-usd.conversion-currency'
BV_GBP_CURR = 'budget.value-gbp.conversion-currency'
PDV_USD_CURR = 'planned-disbursement.value-usd.conversion-currency'
PDV_GBP_CURR = 'planned-disbursement.value-gbp.conversion-currency'
TV_USD_CURR = 'transaction.value-usd.conversion-currency'
TV_GBP_CURR = 'transaction.value-gbp.conversion-currency'
T_TYPES = [None, "incoming-funds", "outgoing-commitment", "disbursement",
           "expenditure", "interest-payment", "loan-repayment",
           "reimbursement", "purchase-of-equity", "sale-of-equity",
           "credit-guarantee", "incoming-commitment", "outgoing-pledge",
           "incoming-pledge"]
TT_U = [t.replace("-", "_") if t else None for t in T_TYPES]


def currency_aggregation(data):
    """
    Aggregate currency data.
    We use a mongodb approach where the data is temporarily stored in a mongo database,
    to do the aggregations as efficiently as possible.
    This was tested to be much faster than a python approach.
    We could still test with postgres, as we already have an integration for the use of celery.

    The aggregations are split into two levels, activity level and child level.
    First, each activity is aggregated, then the updated dataset is stored in mongo, to be able
    to aggregate on the child data as well.

    :param data: List of activities.
    :return: the dataset updated with aggregations.
    """

    try:
        # Prepare data and connection
        if type(data) is dict:
            data = [data]  # Needs to be list for aggregation
        data = prepare_data(data)
        dba, client = connect_to_mongo(data)
        # Aggregate currencies on activity level.
        activity_aggregations = get_aggregations(dba, data)
        aggregation_fields, formatted_aggregation_fields, child_aggregation_fields, \
            parent_plus_child_aggregation_fields = get_aggregation_fields()
        activity_indexes = index_activity_data(data)
        data = process_activity_aggregations(data, activity_aggregations, activity_indexes, aggregation_fields)
        # Aggregate child currencies
        dba = refresh_mongo_data(dba, data)
        child_aggregations = get_child_aggregations(dba, aggregation_fields)
        data = process_child_aggregations(data, child_aggregations, activity_indexes, aggregation_fields,
                                          child_aggregation_fields, parent_plus_child_aggregation_fields)
        # Close mongo connection
        client.close()

        # Clean up data names
        data = clean_aggregation_result(data, aggregation_fields, formatted_aggregation_fields)
    except PyMongoError:
        pass  # Return the data as is, if there is an error.
    return data


def prepare_data(data):
    """
    Mongo cannot query on strings with periods, as they are used as object separators.
    Note: This needs to be reversed in clean_aggregation_result.

    :param data: List of activities.
    :return: List of activities with aggregation field periods replaced by dashes.
    """
    for activity in data:
        if TVU_CLEAN in activity:
            activity[TVU_DASHES] = activity.pop(TVU_CLEAN)
        if TVU_CLEAN_TYPE in activity:
            activity[TVU_DASHES_TYPE] = activity.pop(TVU_CLEAN_TYPE)
        if TVU_CLEAN_GBP in activity:
            activity[TVU_DASHES_GBP] = activity.pop(TVU_CLEAN_GBP)
        if TVU_CLEAN_TYPE_GBP in activity:
            activity[TVU_DASHES_TYPE_GBP] = activity.pop(TVU_CLEAN_TYPE_GBP)
    return data


def connect_to_mongo(data):
    """
    Create a connection to the mongo database.

    :param data: List of activities.
    :return: Mongo database and connection.
    """
    try:
        # Connect to mongo
        client = MongoClient(settings.MONGO_CONNECTION_STRING)
        db = client.activities
        dba = db.activity
        dba.drop()  # Drop previous dataset
        dba.insert_many(data)  # This introduces '_id' key to each data point

        return dba, client
    except PyMongoError as e:  # NOQA
        logging.error(f"connect_to_mongo:: Error in connecting to mongo: {e}")
        raise


def get_aggregations(dba, data):
    """
    Do the mongo aggregations for every activity.
    Retrieve the aggregations for budgets, transactions (split into sum and per-transaction-type)
    and planned disbursements.

    :param dba: Mongo database with the activities.
    :return: A dict with the aggregations.
    """
    # Retrieve activity budget aggregation
    budget_agg = list(dba.aggregate([
        {MONGO_UNWIND: "$budget"},
        {MONGO_GROUP: {
            "_id": MONGO_IID,
            "budget-value-sum": {"$sum": "$budget.value"},
        }}
    ]))

    # transactions
    transaction_agg = list(dba.aggregate([
        {MONGO_UNWIND: "$transaction"},
        {MONGO_GROUP: {
            "_id": [MONGO_IID, "$transaction.transaction-type.code"],
            "transaction-value-sum": {"$sum": "$transaction.value"},
        }}
    ]))

    # target is for the type_values, {type_n: [list of values]}, to be in form
    # [
    #   {'_id': [data[iati-identifier], type_n], 'transaction-value-usd-sum': sum(type_values[type_n])},
    # ]
    transaction_usd_agg = aggregate_converted_types(data, 'usd')
    transaction_gbp_agg = aggregate_converted_types(data, 'gbp')

    # Planned disbursement
    planned_disbursement_agg = list(dba.aggregate([
        {MONGO_UNWIND: "$planned-disbursement"},
        {MONGO_GROUP: {
            "_id": MONGO_IID,
            "planned-disbursement-value-sum": {"$sum": "$planned-disbursement.value"},
        }}
    ]))

    return {
        'budget': budget_agg,
        'transaction': transaction_agg,
        'transaction-usd': transaction_usd_agg,
        'transaction-gbp': transaction_gbp_agg,
        'planned-disbursement': planned_disbursement_agg,
    }


def aggregate_converted_types(data, curr):
    transaction_agg = []
    for activity in data:
        type_values = {}
        if f'transaction-value-{curr}' in activity:
            values = activity[f'transaction-value-{curr}']
            types = activity[f'transaction-value-{curr}-type']
            for t in list(set(types)):
                type_values[t] = []

            for index, value in enumerate(types):
                if values[index] is None:
                    continue
                type_values[value].append(values[index])
        for key in type_values:
            transaction_agg.append({
                '_id': [activity['iati-identifier'], key],
                f'transaction-value-{curr}-sum': sum(type_values[key])
            })
    return transaction_agg


def get_aggregation_fields():
    """
    Get the aggregation fields.

    :return: flattened aggregation fields, formatted aggregation fields,
                and the latter for child and activity-plus-child.
    """
    aggregation_fields = {
        "budget": "activity-aggregation-budget-value",
        "budget_usd": "activity-aggregation-budget-value-usd",
        "budget_gbp": "activity-aggregation-budget-value-gbp",
        "budget_currency": "activity-aggregation-budget-currency",
        "planned_disbursement": "activity-aggregation-planned-disbursement-value",
        "planned_disbursement_usd": "activity-aggregation-planned-disbursement-value-usd",
        "planned_disbursement_gbp": "activity-aggregation-planned-disbursement-value-gbp",
        "planned_disbursement_currency": "activity-aggregation-planned-disbursement-currency",
        "incoming_funds": "activity-aggregation-incoming-funds-value",
        "incoming_funds_usd": "activity-aggregation-incoming-funds-value-usd",
        "incoming_funds_gbp": "activity-aggregation-incoming-funds-value-gbp",
        "incoming_funds_currency": "activity-aggregation-incoming-funds-currency",
        "outgoing_commitment": "activity-aggregation-outgoing-commitment-value",
        "outgoing_commitment_usd": "activity-aggregation-outgoing-commitment-value-usd",
        "outgoing_commitment_gbp": "activity-aggregation-outgoing-commitment-value-gbp",
        "outgoing_commitment_currency": "activity-aggregation-outgoing-commitment-currency",
        "disbursement": "activity-aggregation-disbursement-value",
        "disbursement_usd": "activity-aggregation-disbursement-value-usd",
        "disbursement_gbp": "activity-aggregation-disbursement-value-gbp",
        "disbursement_currency": "activity-aggregation-disbursement-currency",
        "expenditure": "activity-aggregation-expenditure-value",
        "expenditure_usd": "activity-aggregation-expenditure-value-usd",
        "expenditure_gbp": "activity-aggregation-expenditure-value-gbp",
        "expenditure_currency": "activity-aggregation-expenditure-currency",
        "interest_payment": "activity-aggregation-interest-payment-value",
        "interest_payment_usd": "activity-aggregation-interest-payment-value-usd",
        "interest_payment_gbp": "activity-aggregation-interest-payment-value-gbp",
        "interest_payment_currency": "activity-aggregation-interest-payment-currency",
        "loan_repayment": "activity-aggregation-loan-repayment-value",
        "loan_repayment_usd": "activity-aggregation-loan-repayment-value-usd",
        "loan_repayment_gbp": "activity-aggregation-loan-repayment-value-gbp",
        "loan_repayment_currency": "activity-aggregation-loan-repayment-currency",
        "reimbursement": "activity-aggregation-reimbursement-value",
        "reimbursement_usd": "activity-aggregation-reimbursement-value-usd",
        "reimbursement_gbp": "activity-aggregation-reimbursement-value-gbp",
        "reimbursement_currency": "activity-aggregation-reimbursement-currency",
        "purchase_of_equity": "activity-aggregation-purchase-of-equity-value",
        "purchase_of_equity_usd": "activity-aggregation-purchase-of-equity-value-usd",
        "purchase_of_equity_gbp": "activity-aggregation-purchase-of-equity-value-gbp",
        "purchase_of_equity_currency": "activity-aggregation-purchase-of-equity-currency",
        "sale_of_equity": "activity-aggregation-sale-of-equity-value",
        "sale_of_equity_usd": "activity-aggregation-sale-of-equity-value-usd",
        "sale_of_equity_gbp": "activity-aggregation-sale-of-equity-value-gbp",
        "sale_of_equity_currency": "activity-aggregation-sale-of-equity-currency",
        "credit_guarantee": "activity-aggregation-credit-guarantee-value",
        "credit_guarantee_usd": "activity-aggregation-credit-guarantee-value-usd",
        "credit_guarantee_gbp": "activity-aggregation-credit-guarantee-value-gbp",
        "credit_guarantee_currency": "activity-aggregation-credit-guarantee-currency",
        "incoming_commitment": "activity-aggregation-incoming-commitment-value",
        "incoming_commitment_usd": "activity-aggregation-incoming-commitment-value-usd",
        "incoming_commitment_gbp": "activity-aggregation-incoming-commitment-value-gbp",
        "incoming_commitment_currency": "activity-aggregation-incoming-commitment-currency",
        "outgoing_pledge": "activity-aggregation-outgoing-pledge-value",
        "outgoing_pledge_usd": "activity-aggregation-outgoing-pledge-value-usd",
        "outgoing_pledge_gbp": "activity-aggregation-outgoing-pledge-value-gbp",
        "outgoing_pledge_currency": "activity-aggregation-outgoing-pledge-currency",
        "incoming_pledge": "activity-aggregation-incoming-pledge-value",
        "incoming_pledge_usd": "activity-aggregation-incoming-pledge-value-usd",
        "incoming_pledge_gbp": "activity-aggregation-incoming-pledge-value-gbp",
        "incoming_pledge_currency": "activity-aggregation-incoming-pledge-currency",
    }

    # prepare formatted and alternative names for aggregation fields
    formatted_aggregation_fields = {}
    for key in aggregation_fields:
        formatted_aggregation_fields[key] = aggregation_fields[key].replace("aggregation-", "aggregation.").replace(
            "-value", ".value").replace("-currency", ".currency")

    child_aggregation_fields = {}
    for key in formatted_aggregation_fields:
        child_aggregation_fields[key] = formatted_aggregation_fields[key].replace("activity-aggregation",
                                                                                  "child-aggregation")

    parent_plus_child_aggregation_fields = {}
    for key in formatted_aggregation_fields:
        parent_plus_child_aggregation_fields[key] = \
            formatted_aggregation_fields[key].replace("activity-aggregation", "activity-plus-child-aggregation")

    return aggregation_fields, formatted_aggregation_fields, \
        child_aggregation_fields, parent_plus_child_aggregation_fields


def index_activity_data(data):
    """
    Indexes the activity data list by activity ID.

    :param data: the activity data list
    :return: a dictionary with the activity iati id as the key, and the location in the data array as the value.
    """
    activity_indexes = {}
    for i, activity in enumerate(data):
        if 'iati-identifier' in activity:
            activity_indexes[activity['iati-identifier']] = i
    return activity_indexes


def process_activity_aggregations(data, activity_aggregations, activity_indexes, aggregation_fields):
    """
    Processes the activity aggregations.
    This means that the values of the aggregations are retrieved and stored into the relevant activities.

    :param data: the activity data list
    :param activity_aggregations: the activity aggregations
    :param activity_indexes: the activity indexes
    :param aggregation_fields: the aggregation fields
    """
    budget_agg = activity_aggregations.get('budget', [])
    transaction_agg = activity_aggregations.get('transaction', [])
    transaction_usd_agg = activity_aggregations.get('transaction-usd', [])
    transaction_gbp_agg = activity_aggregations.get('transaction-gbp', [])
    planned_disbursement_agg = activity_aggregations.get('planned-disbursement', [])
    # Process the aggregated data
    process_budget_agg(budget_agg, activity_indexes, aggregation_fields, data)
    process_planned_disbursement_agg(planned_disbursement_agg, activity_indexes, aggregation_fields, data)
    # Transaction types, starting with none to make array index match the transaction type code from the codelist
    process_transaction_agg(transaction_agg, activity_indexes, aggregation_fields, data)
    process_transaction_currency_agg(transaction_usd_agg, activity_indexes, aggregation_fields, data, 'usd')
    process_transaction_currency_agg(transaction_gbp_agg, activity_indexes, aggregation_fields, data, 'gbp')
    return data


def refresh_mongo_data(dba, data):
    """
    Refresh mongo data so we can access the new activity aggregation,
    as the child aggregations are the sums of their children

    :param dba: the mongo activities database.
    :param data: the data to refresh
    :return: the refreshed data
    """
    dba.drop()  # Drop previous dataset
    dba.insert_many(data)  # Re-submit updated dataset
    return dba


def get_child_aggregations(dba, aggregation_fields):
    """
    Retrieves the child aggregations from the database.

    :param dba: the mongo activities database.
    :param aggregation_fields: the aggregation fields
    :return: the child aggregations
    """
    # Prepare group object which sums up each aggregation field.
    group_object = {"_id": "$related-activity.ref"}
    for key in aggregation_fields:
        if "currency" not in aggregation_fields[key]:
            group_object[key] = {"$sum": f'${aggregation_fields[key]}'}
    # Get aggregations for all fields
    children_agg = list(dba.aggregate([
        # {MONGO_UNWIND: "$related-activity"},
        {"$unwind": "$related-activity"},
        {"$match": {"related-activity.type": 1}},
        {'$group': {
            '_id': '$_id',
            'uniqueActivity': {
                '$first': '$$ROOT'
            }
        }},
        {'$replaceRoot': {'newRoot': '$uniqueActivity'}},
        {"$group": group_object}
        # {MONGO_GROUP: group_object}
    ]))
    return children_agg


def process_child_aggregations(data, children_agg, activity_indexes, aggregation_fields, child_aggregation_fields,
                               parent_plus_child_aggregation_fields):
    """
    Process the child aggregations and add them to the data.

    :param data: the activities dataset
    :param children_agg: the child aggregations
    :param activity_indexes: the activity indexes
    :param aggregation_fields: the aggregation fields
    :param child_aggregation_fields: the child aggregation fields
    :param parent_plus_child_aggregation_fields: the parent plus child aggregation fields
    """
    for agg in children_agg:
        if agg['_id'] not in activity_indexes:
            # skip activities that are not in the parent dataset
            continue
            # Find the index of the relevant activity
        index_of_activity = activity_indexes[agg.pop('_id')]

        for key in agg:
            if agg[key] == 0:
                continue
            # Add the child aggregations to the data
            data[index_of_activity][child_aggregation_fields[key]] = agg[key]
            # Add the parent plus child aggregations to the data
            parent_value = 0  # Only retrieve value if the value exists in parent
            if aggregation_fields[key] in data[index_of_activity]:
                parent_value = data[index_of_activity][aggregation_fields[key]]
            data[index_of_activity][parent_plus_child_aggregation_fields[key]] = agg[key] + parent_value

            # Make sure we add the currency as well:
            process_child_agg_currencies(data, key, index_of_activity,
                                         child_aggregation_fields, parent_plus_child_aggregation_fields)

    return data


def process_child_agg_currencies(data, key, index_of_activity,
                                 child_aggregation_fields, parent_plus_child_aggregation_fields):
    """
    Make sure we have the currencies for each of the child aggregations.
    """
    if key + "_currency" in child_aggregation_fields:  # Check once as both have the same keys
        currency = get_currency(key, data, index_of_activity)
        data[index_of_activity][child_aggregation_fields[key + "_currency"]] = currency
        data[index_of_activity][parent_plus_child_aggregation_fields[key + "_currency"]] = currency


def get_currency(key, data, index_of_activity):
    currency = "USD"  # Default to USD
    if key == 'budget':
        if BV_USD_CURR in data[index_of_activity]:
            currency = data[index_of_activity][BV_USD_CURR]
        if BV_GBP_CURR in data[index_of_activity]:
            currency = data[index_of_activity][BV_GBP_CURR]
    if key == 'planned-disbursement':
        if PDV_USD_CURR in data[index_of_activity]:
            currency = data[index_of_activity][PDV_USD_CURR]
        if PDV_GBP_CURR in data[index_of_activity]:
            currency = data[index_of_activity][PDV_GBP_CURR]
    if key == 'transaction':
        if TV_USD_CURR in data[index_of_activity]:
            currency = data[index_of_activity][TV_USD_CURR]
        if TV_GBP_CURR in data[index_of_activity]:
            currency = data[index_of_activity][TV_GBP_CURR]
    return currency


def clean_aggregation_result(data, aggregation_fields, formatted_aggregation_fields):
    """
    Rename any fields in the aggregation_fields dict to the corresponding formatted_aggregation_fields dict.
    As well as the initially renamed transaction value fields.

    :param data: the activities dataset
    :param aggregation_fields: the aggregation fields
    :param formatted_aggregation_fields: the formatted aggregation fields
    :return: the cleaned data
    """
    for activity in data:
        if '_id' in activity:
            activity.pop('_id')  # Remove mongo introduced '_id'.
        activity = revert_activity_tvu(activity)
        # Go through the - appended aggregation_fields and rename to formatted_aggregation_fields
        for key, value in aggregation_fields.items():
            if value not in activity:
                continue
            activity[formatted_aggregation_fields[key]] = activity.pop(value)
    return data


def revert_activity_tvu(activity):
    if TVU_DASHES in activity:
        activity[TVU_CLEAN] = activity.pop(TVU_DASHES)
    if TVU_DASHES_TYPE in activity:
        activity[TVU_CLEAN_TYPE] = activity.pop(TVU_DASHES_TYPE)
    if TVU_DASHES_GBP in activity:
        activity[TVU_CLEAN_GBP] = activity.pop(TVU_DASHES_GBP)
    if TVU_DASHES_TYPE_GBP in activity:
        activity[TVU_CLEAN_TYPE_GBP] = activity.pop(TVU_DASHES_TYPE_GBP)
    return activity


def process_budget_agg(budget_agg, activity_indexes, aggregation_fields, data):
    for agg in budget_agg:
        # Find the index of the relevant activity
        if agg['_id'] not in activity_indexes:
            continue
        index_of_activity = activity_indexes[agg['_id']]
        data[index_of_activity][aggregation_fields['budget']] = agg['budget-value-sum']
        if 'budget.value-usd.sum' in data[index_of_activity]:
            data[index_of_activity][aggregation_fields['budget_usd']] = data[index_of_activity]['budget.value-usd.sum']
        if 'budget.value-gbp.sum' in data[index_of_activity]:
            data[index_of_activity][aggregation_fields['budget_gbp']] = data[index_of_activity]['budget.value-gbp.sum']
        # Get the original currency from which has been converted
        if BV_USD_CURR in data[index_of_activity]:
            data[index_of_activity][aggregation_fields['budget_currency']] = data[index_of_activity][BV_USD_CURR]


def process_planned_disbursement_agg(planned_disbursement_agg, activity_indexes, aggregation_fields, data):
    for agg in planned_disbursement_agg:
        # Find the index of the relevant activity
        if agg['_id'] not in activity_indexes:
            continue
        index_of_activity = activity_indexes[agg['_id']]
        data[index_of_activity][aggregation_fields['planned_disbursement']] = agg['planned-disbursement-value-sum']
        if 'planned-disbursement.value-usd.sum' in data[index_of_activity]:
            data[index_of_activity][aggregation_fields['planned_disbursement_usd']] = data[index_of_activity][
                'planned-disbursement.value-usd.sum']
        if 'planned-disbursement.value-gbp.sum' in data[index_of_activity]:
            data[index_of_activity][aggregation_fields['planned_disbursement_gbp']] = data[index_of_activity][
                'planned-disbursement.value-gbp.sum']
        if PDV_USD_CURR in data[index_of_activity]:
            data[index_of_activity][aggregation_fields['planned_disbursement_currency']] = data[index_of_activity][
                PDV_USD_CURR]
        if PDV_GBP_CURR in data[index_of_activity]:
            data[index_of_activity][aggregation_fields['planned_disbursement_currency']] = data[index_of_activity][
                PDV_GBP_CURR]


def process_transaction_agg(transaction_agg, activity_indexes, aggregation_fields, data):
    for agg in transaction_agg:
        # Find the index of the relevant activity
        if agg['_id'][0] not in activity_indexes:
            continue
        index_of_activity = activity_indexes[agg['_id'][0]]
        transaction_type = agg['_id'][1]
        if type(transaction_type) is int:
            data[index_of_activity][f'{aggregation_fields[TT_U[transaction_type]]}'] = \
                agg['transaction-value-sum']


def process_transaction_currency_agg(transaction_curr_agg, activity_indexes, aggregation_fields, data, currency):
    for agg in transaction_curr_agg:
        if agg['_id'][0] not in activity_indexes:
            continue
        # Find the index of the relevant activity
        index_of_activity = activity_indexes[agg['_id'][0]]
        transaction_type = agg['_id'][1]
        if not transaction_type or type(transaction_type) is not int:
            continue
        data[index_of_activity][f'{aggregation_fields[TT_U[transaction_type]]}-{currency}'] = agg[
            f'transaction-value-{currency}-sum']
        if f'transaction-value-{currency}-conversion-currency' in data[index_of_activity]:
            if currency == 'gbp':
                selector = TV_GBP_CURR
            else:
                selector = TV_USD_CURR
            data[index_of_activity][f'{aggregation_fields[TT_U[transaction_type]]}-currency'] = \
                data[index_of_activity][selector]
