def activity_dates(data):
    """
    Requested by FCDO. Single valued fields.
    Activity dates is one of four types: planned or actual, start or end.
    start planned (type 1), start actual (type 2),
    end planned (type 3), end actual (type 4)

    Relevant fields:
    'activity-date.type' and 'activity-date.iso-date'

    :param data: reference to the activity in the data
    """
    if 'activity-date' in data.keys():
        if type(data['activity-date']) is dict:
            data['activity-date'] = [data['activity-date']]
        for date in data['activity-date']:
            data = extract_activity_dates(date, data)
    return data


def extract_activity_dates(date, data):
    # This approach was tested to be the fastest with 10.000 runs
    i = 1
    for s in ['start', 'end']:
        for ss in ['planned', 'actual']:
            if 'type' in date.keys() and 'iso-date' in data.keys():
                if date['type'] == i:
                    data[f'activity-date.{s}-{ss}'] = date['iso-date']
            i += 1
    return data
