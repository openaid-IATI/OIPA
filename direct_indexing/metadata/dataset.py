import logging

import requests
from celery import shared_task
from django.conf import settings

from direct_indexing.custom_fields.models import codelists
from direct_indexing.metadata.util import download_dataset, retrieve
from direct_indexing.processing import dataset as dataset_processing


class DatasetException(Exception):
    def __init__(self, message):
        super().__init__(message)


@shared_task
def subtask_process_dataset(dataset, update):
    dataset_indexing_result, result, should_retry = dataset_processing.fun(dataset, update)
    if result == 'Successfully indexed' and dataset_indexing_result == 'Successfully indexed':
        return result
    elif dataset_indexing_result == 'Dataset invalid':
        return dataset_indexing_result
    elif should_retry:
        raise subtask_process_dataset.retry(countdown=60, max_retries=2, exc=DatasetException(message=f'Error indexing dataset {dataset["id"]}\nDataset metadata:\n{result}\nDataset indexing:\n{str(dataset_indexing_result)}'))  # NOQA
    else:
        return "Dataset was not indexed"
        # commented to prevent false positive exceptions. raise DatasetException(message=f'Error indexing dataset {dataset["id"]}\nDataset metadata:\n{result}\nDataset indexing:\n{str(dataset_indexing_result)}')  # NOQA


def index_datasets_and_dataset_metadata(update, force_update):
    """
    Steps:
    . Download all the datasets
    . Download dataset metadata
    . Download codelists and make data available.
    . For every dataset:
        Index that dataset
    . Index all dataset metadata

    :return: None
    """
    logging.info('index_datasets_and_dataset_metadata:: - Dataset metadata and indexing')
    download_dataset()

    logging.info('index_datasets_and_dataset_metadata:: -- Retrieve metadata')
    dataset_metadata = retrieve(settings.METADATA_DATASET_URL, 'dataset_metadata', force_update)

    # If we are updating instead of refreshing, retrieve dataset ids
    if update:
        dataset_metadata, update_bools = prepare_update(dataset_metadata)
    load_codelists()
    logging.info('index_datasets_and_dataset_metadata:: -- Walk the metadata')
    number_of_datasets = len(dataset_metadata)
    for i, dataset in enumerate(dataset_metadata):
        if settings.THROTTLE_DATASET and i % 10 != 0:
            continue
        logging.info(f'index_datasets_and_dataset_metadata:: --- Submitting dataset {i+1} of {number_of_datasets}')
        update_flag = update_bools[i] if update else False
        subtask_process_dataset.delay(dataset=dataset, update=update_flag)
    res = '- All Indexing substasks started'
    logging.info(f'index_datasets_and_dataset_metadata:: result: {res}')
    return res


def load_codelists():
    """
    Safe loads codelists.
    """
    logging.info('load_codelists:: -- Load currencies and codelists')
    try:
        codelists.Codelists(download=True)
    except requests.exceptions.RequestException:
        logging.error('load_codelists:: Codelists not available')
        raise


def _get_existing_datasets():
    url = settings.SOLR_DATASET + (
        '/select?q=*:*'
        ' AND id:*&rows=100000&wt=json&fl=resources.hash,id,extras.filetype'
    )
    data = requests.get(url).json()['response']['docs']
    datasets = {}
    for doc in data:
        _hash = ""
        if 'resources.hash' in doc:
            _hash = doc['resources.hash'][0]
        _filetype = ""
        if 'extras.filetype' in doc:
            _filetype = doc['extras.filetype']
        datasets[doc['id']] = {'hash': _hash, 'filetype': _filetype}
    return datasets


def prepare_update(dataset_metadata):
    # create a list of new and updated datasets.
    existing_datasets = _get_existing_datasets()
    new_datasets = [d for d in dataset_metadata if d['id'] not in existing_datasets]
    old_datasets = [d for d in dataset_metadata if d['id'] in existing_datasets]
    changed_datasets = [
        d for d in old_datasets if
        ('' if 'hash' not in d['resources'][0] else d['resources'][0]['hash']) != existing_datasets[d['id']]['hash']
    ]
    updated_datasets = new_datasets + changed_datasets
    updated_datasets_bools = [False for _ in new_datasets] + [True for _ in changed_datasets]
    return updated_datasets, updated_datasets_bools
