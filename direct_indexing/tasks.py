import json
import logging
import os
import time
import urllib.request

import pysolr
from celery import shared_task
from django.conf import settings

from direct_indexing import direct_indexing, util
from direct_indexing.metadata.dataset import subtask_process_dataset
from direct_indexing.metadata.util import retrieve
# Currently disabled import for datadump check
# from direct_indexing.util import datadump_success
from iaticloud.celery import app


@shared_task
def clear_all_cores():
    """
    Simply trigger process clearing all solr cores.
    """
    logging.info("clear_all_cores:: Starting direct indexing clear all cores.")
    return direct_indexing.clear_indices()


@shared_task
def clear_cores_with_name(core="publisher"):
    """
    Simply trigger process clearing all solr cores.
    """
    logging.info("clear_all_cores:: Starting direct indexing clear all cores.")
    return direct_indexing.clear_indices_for_core(core)


@shared_task
def start(update=False, drop=False):
    # Only if the most recent data dump was a success
    # if not datadump_success():
    #     logging.info("start:: The CodeForIATI Data Dump failed, aborting the process!")
    #     raise ValueError("The CodeForIATI Data Dump failed, aborting the process!")
    # Clear the cores, do not use a task as this needs to finish before continuing
    try:
        if not update:
            direct_indexing.clear_indices()
    except pysolr.SolrError:
        # Stop the process and send a message to Celery Flower
        logging.info("start:: Error clearing the direct indexing cores, check your Solr instance.")
        return "Error clearing the direct indexing cores, check your Solr instance."
    if drop:
        direct_indexing.drop_removed_data()
    # Run the publisher metadata indexing subtask
    subtask_publisher_metadata.delay()
    # Run the dataset metadata indexing subtask
    subtask_dataset_metadata.delay(update)
    # Send clear message to Celery Flower
    logging.info("start:: Both the publisher and dataset metadata indexing have begun.")
    return "Both the publisher and dataset metadata indexing have begun."


@shared_task
def subtask_publisher_metadata():
    logging.info("subtask_publisher_metadata:: Starting publisher metadata indexing.")
    result = direct_indexing.run_publisher_metadata()
    logging.info(f"subtask_publisher_metadata:: result: {result}")
    return result


@shared_task
def subtask_dataset_metadata(update=False):
    logging.info("subtask_dataset_metadata:: Starting dataset metadata indexing.")
    result = direct_indexing.run_dataset_metadata(update)
    logging.info(f"subtask_dataset_metadata:: result: {result}")
    return result


@shared_task
def fcdo_replace_partial_url(find_url, replace_url):
    """
    This function is used to update a dataset based on the provided URL.
    For example, if an existing dataset has the url 'example.com/a.xml',
    and a staging dataset is prepared at 'staging-example.com/a.xml',
    the file is downloaded and the iati datastore is refreshed with the new content for this file.

    Note: if the setting "FRESH" is active, and the datastore is incrementally updating,
    the custom dataset will be overwritten by the incremental update. If this feature is used,
    either disable the incremental updates (admin panel), or set the Fresh setting to false (source code).
    """
    logging.info("fcdo_replace_partial_url:: Starting partial url match and replace")
    dataset_metadata = retrieve(settings.METADATA_DATASET_URL, 'dataset_metadata')
    num_updated_datasets = 0
    for dataset in dataset_metadata:
        # find datasets that need to be replaced
        if 'resources' not in dataset or 'name' not in dataset or 'organization' not in dataset:
            continue
        if 'url' not in dataset['resources'][0] or 'hash' not in dataset['resources'][0]:
            continue
        url = dataset['resources'][0]['url']  # always 1 url
        if find_url not in url:
            continue

        # replace the url
        new_url = url.replace(find_url, replace_url)
        dataset['resources'][0]['url'] = new_url

        # download the new file and overwrite the old file.
        ds_name = dataset['name']
        ds_org = dataset['organization']['name']
        ds_file = f'{settings.DATASET_PARENT_PATH}/iati-data-main/data/{ds_org}/{ds_name}.xml'
        if os.path.exists(ds_file):
            os.remove(ds_file)
        else:
            return f"this file does not exist {ds_file}"
        downloader = urllib.request.URLopener()
        downloader.retrieve(new_url, ds_file)

        # Update the dataset hash to force an update, using current epoch as a timestamp ensure difference.
        dataset['resources'][0]['hash'] = f'updateme-{time.time()}'
        num_updated_datasets += 1
    # update the local dataset metadata file.
    logging.info("fcdo_replace_partial_url:: update dataset_metadata file")
    path = f'{settings.DATASET_PARENT_PATH}/dataset_metadata.json'
    with open(path, 'w') as file:
        json.dump(dataset_metadata, file, indent=4)

    # run the dataset metadata with update = True and force_update = True
    # this will automatically all the files that have a new URL and a new HASH
    logging.info("fcdo_replace_partial_url:: run the dataset metadata to process the files which have been updated.")
    direct_indexing.run_dataset_metadata(True, force_update=True)
    logging.info(f"fcdo_replace_partial_url:: Finished partial url match and replace, updated {num_updated_datasets} datasets.")  # NOQA
    return f"We've updated {num_updated_datasets} dataset(s) for the provided URLs."


@shared_task
def revoke_all_tasks():
    app.control.purge()


"""
CUSTOM DATASETS
"""


@shared_task
def index_custom_dataset(url, title, name, org):
    logging.info("index_custom_dataset:: create the dataset metadata")
    metadata = util.create_dataset_metadata(url, title, name, org)
    if type(metadata) is str:
        raise ValueError(metadata)

    cp_res = util.copy_custom()
    if type(cp_res) is str:
        raise ValueError(cp_res)

    subtask_process_dataset.delay(dataset=metadata, update=False)
    return "Success"


@shared_task
def remove_custom_dataset(name, org, dataset_id):
    logging.info("remove_custom_dataset:: remove the custom dataset")
    return util.remove_custom(name, org, dataset_id)
