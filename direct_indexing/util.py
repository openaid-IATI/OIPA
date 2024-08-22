import datetime
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import urllib.request
import xml.etree.ElementTree as ET

import pysolr
from django.conf import settings


def clear_core(core_url):
    """
    Clear out the old data from a core

    :param core_url: The url of the core to clear
    :return: None
    """
    try:
        core = pysolr.Solr(core_url, always_commit=True)
        _solr_out = core.delete(q='*:*')
        logging.info(f'clear_core:: solr_out delete: {_solr_out}')
    except pysolr.SolrError:
        logging.error(f"clear_core:: Unable to clear core {core_url}")
        raise


def index_to_core(url, json_path, remove=False):
    """
    Call the Solr post tool to index the json file into the Solr core.

    :param url: The url of the core to index into
    :param json_path: The path to the json file to index
    :param remove: bool to indicate if the created json file should be removed, defaults to False
    """
    try:
        logging.info("--index to core:: check output")
        solr_out = subprocess.check_output([settings.SOLR_POST_TOOL, '-url', url, json_path],
                                           stderr=subprocess.STDOUT).decode('utf-8')
        result = 'Successfully indexed'
        if 'SolrException' in solr_out or 'Failed to index' in solr_out:
            logging.info("--index to core:: solr_out: " + solr_out)
            message_index = re.search(r'\b(msg)\b', solr_out).start()+5  # +5 to get past the 'msg:'
            solr_out = solr_out[message_index:]
            result = solr_out[:re.search(r'\n', solr_out).start()-1]  # stop at newline excluding the ,
            if remove:
                logging.info("--index to core:: issues in solr parse, remove json dump")
                os.remove(json_path)
        else:
            if remove:
                logging.info("--index to core:: no issues, remove json dump")
                os.remove(json_path)  # On success, remove the json file
        return result
    except subprocess.CalledProcessError as e:
        result = f'Failed to index due to:\n {e}'
        logging.error(f'index_to_core:: error: {result}')
        return result
    except Exception as e:
        logging.info("--index to core:: Uncaught other exception!!" + str(e))
        raise


def datadump_success():
    """
    Check if the most recent IATI Data dump by CodeForIATI was a success.
    Returns true or false based on the above.
    """
    logging.info("datadump_success:: Checking if the most recent CodeForIATI Data Dump was a success.")
    svg_url = 'https://github.com/codeforIATI/iati-data-dump/actions/workflows/refresh_data.yml/badge.svg'
    data_dump_data = urllib.request.urlopen(svg_url)
    data = data_dump_data.read()
    data_dump_data.close()
    # data is a bytestring containing the svg, passing is not in the svg if the action failed
    return b"passing" in data


def create_dataset_metadata(url, title, name, org):
    try:
        _hash, activity_count, meta_dir = _download_and_hash_file(url, org, name)
    except Exception:
        return "Something went wrong in the downloading and hashing of the file."

    meta = META_BASE.copy()
    meta["id"] = f"zimmerman-custom-{_hash}"
    # metadata created is a datetime.now in this format: 2014-01-15T07:49:08.717792
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    meta["metadata_created"] = now
    meta["metadata_modified"] = now
    meta["resources"][0]["hash"] = _hash
    meta["resources"][0]["metadata_modified"] = now
    meta["resources"][0]["url"] = url
    meta["resources"][0]["created"] = now
    meta["resources"][0]["package_id"] = f"zimmerman-custom-resource-package-id-{_hash}"
    meta["resources"][0]["id"] = f"zimmerman-custom-resource-id-{_hash}"
    meta["title"] = title
    meta["name"] = name

    for i in range(len(meta["extras"])):
        ex = meta['extras'][i]
        if ex["key"] == "activity_count":
            ex["value"] = activity_count
        if ex["key"] == "data_updated":
            ex["value"] = now

    meta["organization"]["title"] = org
    meta["organization"]["created"] = now
    meta["organization"]["id"] = f"zimmerman-custom-{org}"
    meta["organization"]["name"] = org
    meta["iati_cloud_custom"] = True

    # Json dump meta to meta_dir
    try:
        with open(meta_dir + f"/{name}.json", "w") as file:
            json.dump(meta, file, indent=4)
    except Exception:
        return "Something went wrong in storing the metadata of the file."

    return meta


def _download_and_hash_file(url, org, name):
    logging.info("_download_and_hash_file:: start")
    custom_dir = f"{settings.DATASET_PARENT_PATH}/iati-data-main-custom"
    os.makedirs(custom_dir, exist_ok=True)
    # Creating directories
    data_dir = os.path.join(custom_dir, "data")
    metadata_dir = os.path.join(custom_dir, "metadata")
    data_org_dir = os.path.join(data_dir, org)
    metadata_org_dir = os.path.join(metadata_dir, org)

    # Creating directories if they don't exist
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(metadata_dir, exist_ok=True)
    os.makedirs(data_org_dir, exist_ok=True)
    os.makedirs(metadata_org_dir, exist_ok=True)

    # download the file @ url to data_org_dir
    logging.info("_download_and_hash_file:: download " + url)
    file_path = f"{data_org_dir}/{name}.xml"
    downloader = urllib.request.URLopener()
    downloader.retrieve(url, file_path)

    # Get the hash of the file @ file_path
    logging.info("_download_and_hash_file:: hash")
    _hash = hashlib.md5(open(file_path, 'rb').read()).hexdigest()
    # Count the activities in file_path
    logging.info("_download_and_hash_file:: count activities")
    activity_count = 0
    parser = ET.XMLParser(encoding='utf-8')
    etree = ET.parse(file_path, parser=parser)
    tree = etree.getroot()
    # Count nodes in tree
    activity_count = len(tree.findall('iati-activity'))
    return _hash, activity_count, metadata_org_dir


def copy_custom():
    try:
        source_dir = f"{settings.DATASET_PARENT_PATH}/iati-data-main-custom"
        destination_dir = f"{settings.DATASET_PARENT_PATH}/iati-data-main"
        shutil.copytree(source_dir, destination_dir, dirs_exist_ok=True)
    except Exception:
        return "The provided file could not be used."
    return None


def remove_custom(name, org, dataset_id):
    try:
        custom_dir = f"{settings.DATASET_PARENT_PATH}/iati-data-main-custom"
        data_dir = os.path.join(custom_dir, "data")
        metadata_dir = os.path.join(custom_dir, "metadata")
        data_org_dir = os.path.join(data_dir, org)
        metadata_org_dir = os.path.join(metadata_dir, org)

        _rm(data_org_dir, name, '.xml')
        _rm(metadata_org_dir, name, '.json')

        # base_data = data_org_dir str replace iati-data-main-custom with iati-data-main
        base_data = data_org_dir.replace("iati-data-main-custom", "iati-data-main")
        base_metadata = metadata_org_dir.replace("iati-data-main-custom", "iati-data-main")

        _rm(base_data, name, '.xml')
        _rm(base_metadata, name, '.json')

        d_id = dataset_id
        for core in ['activity', 'transaction', 'result', 'budget']:
            solr = pysolr.Solr(f'{settings.SOLR_URL}/{core}', always_commit=True)
            if len(solr.search(f'dataset.id:"{d_id}"')) > 0:
                solr.delete(q=f'dataset.id:"{d_id}"')
        solr = pysolr.Solr(settings.SOLR_DATASET, always_commit=True)
        if len(solr.search(f'id:"{d_id}"')) > 0:
            solr.delete(q=f'id:"{d_id}"')
    except Exception:
        return "The provided org and file name could not be removed."
    return "The dataset has been removed."


def _rm(dir, name, ext=""):
    file_to_remove = os.path.join(dir, f"{name}{ext}")
    if os.path.exists(file_to_remove):
        os.remove(file_to_remove)


META_BASE = {
    "owner_org": "zimmerman-custom",
    "maintainer": None,
    "relationships_as_object": [],
    "private": False,
    "maintainer_email": None,
    "num_tags": 0,
    "id": "",
    "metadata_created": "",
    "metadata_modified": "",
    "author": None,
    "author_email": "info@zimmerman.team",
    "state": "active",
    "version": None,
    "license_id": "other-at",
    "type": "dataset",
    "resources": [
        {
            "cache_url": None,
            "hash": "",
            "description": None,
            "metadata_modified": "",
            "cache_last_updated": None,
            "url": "",
            "format": "iati-xml",
            "state": "active",
            "created": "",
            "package_id": "",
            "mimetype_inner": None,
            "last_modified": None,
            "position": 0,
            "size": 0,
            "url_type": None,
            "id": "",
            "resource_type": None,
            "name": None
        }
    ],
    "num_resources": 1,
    "tags": [],
    "title": "",
    "groups": [],
    "creator_user_id": "zimmerman-custom",
    "relationships_as_subject": [],
    "name": "",
    "isopen": True,
    "url": None,
    "notes": "",
    "license_title": "Other (Attribution)",
    "extras": [
        {
            "value": "",
            "key": "activity_count"
        },
        {
            "value": "",
            "key": "data_updated"
        },
        {
            "value": "activity",
            "key": "filetype"
        },
        {
            "value": "2.03",
            "key": "iati_version"
        },
        {
            "value": "en",
            "key": "language"
        },
        {
            "key": "validation_status",
            "value": "Success"
        }
    ],
    "organization": {
        "description": "",
        "title": "",
        "created": "",
        "approval_status": "approved",
        "is_organization": True,
        "state": "active",
        "image_url": "",
        "type": "organization",
        "id": "",
        "name": ""
    }
}
