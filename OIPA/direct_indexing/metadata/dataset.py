import logging
import requests
from celery import shared_task
from django.conf import settings
from pysolr import Solr

from direct_indexing.custom_fields.models import codelists
from direct_indexing.metadata.util import download_dataset, retrieve
from direct_indexing.processing import dataset as dataset_processing


@shared_task
def direct_indexing_subtask_process_dataset(dataset, update):
    dataset_indexing_result, result = dataset_processing.fun(dataset, update)
    if result == 'Successfully indexed' and dataset_indexing_result == 'Successfully indexed':
        return result
    elif dataset_indexing_result == 'Dataset invalid':
        return dataset_indexing_result
    else:
        raise DatasetException(message=f'Error indexing dataset {dataset["id"]}\nDataset metadata:\n{result}\nDataset indexing:\n{str(dataset_indexing_result)}')  # NOQA


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
    logging.info('- Dataset metadata and indexing')
    download_dataset()

    logging.info('-- Retrieve metadata')
    dataset_metadata = retrieve(settings.METADATA_DATASET_URL, 'dataset_metadata', force_update)

    # If we are updating instead of refreshing, retrieve dataset ids
    if update:
        dataset_metadata, update_bools = prepare_update(dataset_metadata)
    load_codelists()
    logging.info('-- Walk the metadata')
    number_of_datasets = len(dataset_metadata)
    for i, dataset in enumerate(dataset_metadata):
        if dataset['name'] != 'fcdo-998_1':
            continue
        logging.info(f'--- Submitting dataset {i+1} of {number_of_datasets}')
        direct_indexing_subtask_process_dataset.delay(dataset=dataset, update=update_bools[i])
    res = '- All Indexing substasks started'
    logging.info(res)
    return res


def load_codelists():
    """
    Safe loads codelists.
    """
    logging.info('-- Load currencies and codelists')
    try:
        codelists.Codelists(download=True)
    except requests.exceptions.RequestException:
        logging.error('Codelists not available')
        raise


class DatasetException(Exception):
    def __init__(self, message):
        super().__init__(message)


def _get_existing_datasets():
    url = settings.SOLR_DATASET + '/select?q=resources.hash:* AND extras.filetype:* AND id:*&rows=100000&wt=json&fl=resources.hash,id,extras.filetype'
    data = requests.get(url).json()['response']['docs']
    datasets = {}
    for doc in data:
        datasets[doc['id']] = { 'hash': doc['resources.hash'][0], 'filetype': doc['extras.filetype'] }
    return datasets


def prepare_update(dataset_metadata):
    # create a list of new and updated datasets.
    existing_datasets = _get_existing_datasets()
    new_datasets = [d for d in dataset_metadata if d['id'] not in existing_datasets]
    old_datasets = [d for d in dataset_metadata if d['id'] in existing_datasets]
    changed_datasets = [d for d in old_datasets if d['resources'][0]['hash'] != existing_datasets[d['id']]['hash']
        and existing_datasets[d['id']]['filetype'] == 'activity'] # Skip organisation files for incremental updates
    updated_datasets = new_datasets + changed_datasets
    updated_datasets_bools = [False for _ in new_datasets] + [True for _ in changed_datasets]
    return updated_datasets, updated_datasets_bools
