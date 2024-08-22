import os
import subprocess
import urllib.request

import pysolr
import pytest

from direct_indexing import util
from iaticloud import settings


# Test clear_core function
def test_clear_core(mocker):
    # Define the core URL
    core_url = "https://example.com/solr/core"

    # Mock the pysolr.Solr instance
    mock_solr = mocker.patch('pysolr.Solr')
    mock_solr_instance = mock_solr.return_value

    # Mock the delete method
    mock_delete = mocker.patch.object(mock_solr_instance, 'delete')

    # Test the clear_core function
    util.clear_core(core_url)

    # Assert that pysolr.Solr was called with the correct core URL and always_commit
    mock_solr.assert_called_with(core_url, always_commit=True)

    # Assert that the delete method was called with '*:*'
    mock_delete.assert_called_with(q='*:*')

    # Assert that clear_core raises its error when encountering a pysolr.SolrError
    mock_delete.side_effect = pysolr.SolrError
    with pytest.raises(pysolr.SolrError):
        util.clear_core(core_url)


# Test index_to_core function
def test_index_to_core(tmp_path, mocker):
    """
    Index to core:
    - Runs solr post tool with the correct arguments URL and JSON path (which file to submit to solr)
        - if the solr post tool fails, returns the error message
        - if the solr post tool succeeds, returns 'Successfully indexed'
    - Removes the JSON file if remove is True
    - If subprocess errors, return that error.
    """
    # SETUP
    test_dir = tmp_path / "test_data"
    test_dir.mkdir()
    json_path = test_dir / "test_data.json"
    with open(json_path, 'w') as file:
        file.write('{"key": "value"}')

    url = "https://example.com/solr/core"
    OP = "subprocess.check_output"
    # SUCCESSFUL INDEX:
    # Mock subprocess.check_output to simulate success
    mocker.patch(OP, return_value=b"Successfully indexed")
    # Test a successful indexing
    result = util.index_to_core(url, str(json_path), remove=True)
    # Assert that subprocess.check_output was called with the correct arguments
    subprocess.check_output.assert_called_with([
        settings.SOLR_POST_TOOL,
        '-url',
        url,
        str(json_path)
    ], stderr=subprocess.STDOUT)
    # Assert that the function returns 'Successfully indexed' for a successful operation
    assert result == "Successfully indexed"
    # Assert that the file at json_path was not removed, as the remove argument was False
    assert os.path.exists(json_path) is False

    # FAILED INDEX:
    # re-add the file
    with open(json_path, 'w') as file:
        file.write('{"key": "value"}')

    # Mock subprocess.check_output to simulate failure
    mocker.patch(OP, return_value=b"msg: Failed to index\nERROR...")
    # Test a successful indexing
    result = util.index_to_core(url, str(json_path), remove=True)
    # Assert that subprocess.check_output was called with the correct arguments
    subprocess.check_output.assert_called_with([settings.SOLR_POST_TOOL, '-url', url, str(json_path)],
                                               stderr=subprocess.STDOUT)
    # Assert that the function does not return 'Successfully indexed
    assert result != "Successfully indexed"
    # Assert that the file at json_path was removed, as the remove argument was True
    assert os.path.exists(json_path) is False

    # SUBPROCESS ERROR INDEX:
    # Mock subprocess.check_output to simulate failure
    mocker.patch(OP, side_effect=subprocess.CalledProcessError(returncode=1, cmd="solr_post_tool"))
    # Test a failed indexing
    result = util.index_to_core(url, str(json_path), remove=True)
    # Assert that subprocess.check_output was called with the correct arguments
    subprocess.check_output.assert_called_with([settings.SOLR_POST_TOOL, '-url', url, str(json_path)],
                                               stderr=subprocess.STDOUT)
    # Assert that the function returns an error message for a failed operation
    assert "Failed to index due to:" in result

    # Assert that the function raises an exception when other uncaught exceptions are raised
    mocker.patch(OP, side_effect=Exception)
    with pytest.raises(Exception):
        util.index_to_core(url, str(json_path), remove=True)


# Test datadump_success function
def test_datadump_success(mocker):
    # Mock urllib.request.urlopen to return data with "passing" (success)
    mocker.patch('urllib.request.urlopen')
    urllib.request.urlopen.return_value.read.return_value = b'<svg ... passing ...'
    assert util.datadump_success() is True

    # Mock urllib.request.urlopen to return data without "passing" (failure)
    mocker.patch('urllib.request.urlopen')
    urllib.request.urlopen.return_value.read.return_value = b'<svg ... failing ...'
    assert util.datadump_success() is False


def test_create_dataset_metadata(mocker):
    mock_dl = mocker.patch("direct_indexing.util._download_and_hash_file", return_value=("123", 1, "example"))
    mock_json = mocker.patch("direct_indexing.util.json.dump")
    mocker.patch("builtins.open")
    meta_res = util.create_dataset_metadata("url", "title", "name", "org")
    mock_dl.assert_called_once()
    mock_json.assert_called_once()
    assert meta_res["id"] == "zimmerman-custom-123"
    assert meta_res["metadata_created"] != ""
    assert meta_res["metadata_modified"] != ""
    assert meta_res["resources"][0]["hash"] == "123"
    assert meta_res["resources"][0]["metadata_modified"] != ""
    assert meta_res["resources"][0]["url"] == "url"
    assert meta_res["resources"][0]["created"] != ""
    assert meta_res["resources"][0]["package_id"] == "zimmerman-custom-resource-package-id-123"
    assert meta_res["resources"][0]["id"] == "zimmerman-custom-resource-id-123"
    assert meta_res["title"] == "title"
    assert meta_res["name"] == "name"
    assert meta_res["extras"][0]['value'] == 1
    assert meta_res['extras'][1]['value'] != ""
    assert meta_res["organization"]["title"] == "org"
    assert meta_res["organization"]["created"] != ""
    assert meta_res["organization"]["id"] == "zimmerman-custom-org"
    assert meta_res["organization"]["name"] == "org"

    # mock json.dump to raise Exception("error")
    mocker.patch("direct_indexing.util.json.dump", side_effect=Exception)
    res = util.create_dataset_metadata("url", "title", "name", "org")
    assert res == "Something went wrong in storing the metadata of the file."

    # mock _download_and_hash_file has error
    mock_dl.side_effect = Exception
    res = util.create_dataset_metadata("url", "title", "name", "org")
    assert res == "Something went wrong in the downloading and hashing of the file."


def test__download_and_hash_file(tmp_path, mocker):
    # mock the dataset directory creation
    mocker.patch("django.conf.settings.DATASET_PARENT_PATH", tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)

    # mock urllib.request.URLopener() to have a function .retrieve(a,b) which returns ok
    mock_urlretrieve = mocker.patch("urllib.request.URLopener.retrieve")
    xml_content = "<iati-activities><iati-activity></iati-activity><iati-activity></iati-activity></iati-activities>"
    file_path = tmp_path / "iati-data-main-custom" / "data" / "example_org" / "example_name.xml"
    mock_urlretrieve.side_effect = lambda url, filename: open(file_path, 'wb').write(xml_content.encode('utf-8'))

    # run
    res = util._download_and_hash_file("url", "example_org", "example_name")

    # test the dataset directory creation
    idmc = tmp_path/'iati-data-main-custom'
    idmcd = idmc/'data'
    idmcm = idmc/'metadata'
    assert idmc in list(tmp_path.iterdir())
    assert idmcd in list(idmc.iterdir())
    assert idmcm in list(idmc.iterdir())
    # test the download
    mock_urlretrieve.assert_called_once()
    # Test the resulting hash and count. Hashing xml_content is the result, and there are 2 empty activities.
    assert res == ("5594f08ce7fc7f01bb9cdea9801196a0", 2, str(idmcm/'example_org'))


def test_copy_custom(mocker):
    cpt = mocker.patch("shutil.copytree")
    # assert shutil.copytree called once
    util.copy_custom()
    cpt.assert_called_once()

    cpt.side_effect = Exception
    assert util.copy_custom() == "The provided file could not be used."


def test_remove_custom(tmp_path, mocker):
    mocker.patch("django.conf.settings.DATASET_PARENT_PATH", tmp_path)
    mock_rm = mocker.patch("direct_indexing.util._rm")
    mock_solr = mocker.patch('pysolr.Solr')
    mock_solr_instance = mock_solr.return_value

    # Mock the delete method
    mock_delete = mocker.patch.object(mock_solr_instance, 'delete')
    mocker.patch.object(mock_solr_instance, 'search', return_value=[1, 2])

    res = util.remove_custom("", "", "")
    assert res == "The dataset has been removed."
    # assert mock_rm was called 4 times
    assert mock_rm.call_count == 4
    assert mock_delete.call_count == 5
    mock_rm.side_effect = Exception
    assert util.remove_custom("", "", "") == "The provided org and file name could not be removed."


def test__rm(mocker):
    # mock os.path.exists return true
    mocker.patch("direct_indexing.util.os.path.exists", return_value=True)
    mock_rm = mocker.patch("direct_indexing.util.os.remove", return_value=True)
    util._rm("", "", "")
    mock_rm.assert_called_once()
