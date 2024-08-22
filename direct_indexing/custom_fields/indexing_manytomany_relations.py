def index_many_to_many_relations(activity):
    """
    Index many-to-many relations is used to support the use of relational data,
    Currently we use it for the result indicators, which have 0 to N periods and baselines.
    By providing an index for each indicator in for these children, a frontend can access these files as relational
    """
    # Index result indicator, starting with baseline:
    # An indicator has 0 to N baselines, if 0, represent with index -1, else represent with index n.
    if 'result' in activity:
        if not isinstance(activity['result'], list):
            activity['result'] = [activity['result']]
        for result in activity['result']:
            add_result_child_indexes(result, 'indicator')
    # Index participating organisations.
    if 'participating-org' in activity:
        if not isinstance(activity['participating-org'], list):
            activity['participating-org'] = [activity['participating-org']]
        add_participating_org_child_indexes(activity, 'participating-org')


def add_participating_org_child_indexes(field, child):
    """
    Go through the activity participating orgs and index the given child.
    Because this is currently used for results, we directly pass the required children.

    :param field: a dataset containing the initial child of the activity
    :param child: the second level child of the aforementioned field
    """
    # Check if the child exists and make the child a list if it is a dict.
    add_field_child_field_indexes(field, child, 'ref')
    add_field_child_field_indexes(field, child, 'type')
    add_field_child_field_indexes(field, child, 'role')
    add_field_child_field_indexes(field, child, 'activity-id')
    add_field_child_field_indexes(field, child, 'crs-channel-code')
    add_field_child_field_indexes(field, child, 'narrative')
    add_field_child_field_children_indexes(field, child, 'narrative', children=['lang'])


def add_result_child_indexes(field, child):
    """
    Go through the activity results and index the given child.
    Because this is currently used for results, we directly pass the required children.

    :param field: a dataset containing the initial child of the activity
    :param child: the second level child of the aforementioned field
    """
    # Check if the child exists and make the child a list if it is a dict.
    if child not in field:
        return
    if not isinstance(field[child], list):
        field[child] = [field[child]]

    add_field_child_field_indexes(field, child, 'baseline')
    add_field_child_field_indexes(field, child, 'period')
    add_field_child_field_children_indexes(field, child, 'period', children=['actual', 'target'])


def add_field_child_field_indexes(data, target_field, field):
    """
    Index and save the specified field and parent.

    :param data: the data object
    :param target_field: the first level child of data, like an indicator
    :param field: the second level child of data, like indicator.period
    """
    total_field = 0
    data[f'{target_field}.{field}-index'] = []

    for target in data[target_field]:
        # for each first-level child in the data:
        # - if there is no field, set the index to -1
        # - if there is a field, set the index to the number of occurrences

        if field not in target:
            # if there is no field, we notate it with -1
            data[f'{target_field}.{field}-index'].append(-1)
            continue

        # make sure the baseline is a list of baselines.
        if not isinstance(target[field], list):
            target[field] = [target[field]]

        field_index = total_field
        total_field += len(target[field])
        data[f'{target_field}.{field}-index'].append(field_index)


def add_field_child_field_children_indexes(data, target_field, field, children):
    """
    We need to have a separate function for this, it cannot be recursive, because
    we need to store this information at the base level of the budget, rather than
    in the "second level" child of data, to maintain a complete index.

    :param data: the data object
    :param target_field: the first level child of data, like an indicator
    :param field: the second level child of data, like indicator.period
    :param children: a list of third level children, such as indicator.period.actual
    """
    # Loop over the desired children
    for child in children:
        total_field = 0
        data[f'{target_field}.{field}.{child}-index'] = []
        # For every first level child we need to check for second level children.
        for target in data[target_field]:
            if field in target:
                # If the second level child is found, loop over this and check if the third level children are found.
                if not isinstance(target[field], list):
                    target[field] = [target[field]]
                iterate_third_level_children(child, data, field, target, target_field, total_field)
    return data


def iterate_third_level_children(child, data, field, target, target_field, total_field):
    """
    target[field] is now a list of the second level children,
    for every second level child, check if the third level children are found.
    Use enumerate to only save the index of for the first occurrence.
    """
    for item in target[field]:
        if not isinstance(item, dict):
            field_index = -1
        elif child in item:
            field_index = total_field
            if not isinstance(item[child], list):
                total_field += 1
            else:
                total_field += len(item[child])
        else:
            field_index = -1
        data[f'{target_field}.{field}.{child}-index'].append(field_index)
