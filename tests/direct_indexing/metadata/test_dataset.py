import pytest
import requests

from direct_indexing.metadata.dataset import (
    DatasetException, _get_existing_datasets, index_datasets_and_dataset_metadata, load_codelists, prepare_update,
    subtask_process_dataset
)


def test_dataset_exception():
    # UNIT
    message = "Test message"
    with pytest.raises(DatasetException) as excinfo:
        raise DatasetException(message)
    assert str(excinfo.value) == message


def test_subtask_process_dataset(mocker, fixture_dataset):
    # INTEGRATION
    # Test successful indexing
    res_str = 'Successfully indexed'
    fun_path = "direct_indexing.metadata.dataset.dataset_processing.fun"
    mocker.patch(fun_path, return_value=(res_str, res_str, False))
    res = subtask_process_dataset(None, False)
    assert res == res_str

    # Test Dataset invalid
    res_str_dataset = 'Dataset invalid'
    mocker.patch(fun_path, return_value=(res_str_dataset, res_str, False))
    res = subtask_process_dataset(None, False)
    assert res == res_str_dataset

    # Test DatasetException
    res_str_err = 'Error processing dataset'
    mocker.patch(fun_path, return_value=(res_str_err, res_str, False))
    assert subtask_process_dataset(fixture_dataset, False) == "Dataset was not indexed"
    # with pytest.raises(DatasetException) as excinfo:
        # subtask_process_dataset(fixture_dataset, False)
    # assert str(excinfo.value) == f'Error indexing dataset {fixture_dataset["id"]}\nDataset metadata:\n{res_str}\nDataset indexing:\n{str(res_str_err)}'  # NOQA

    # Test retry
    mocker.patch(fun_path, return_value=(res_str_err, res_str, True))
    retry_mock = mocker.patch("direct_indexing.metadata.dataset.subtask_process_dataset.retry", side_effect=DatasetException("Test"))  # NOQA: E501
    with pytest.raises(DatasetException):
        subtask_process_dataset(fixture_dataset, False)
    retry_mock.assert_called_once()


def test_index_datasets_and_dataset_metadata(mocker, fixture_datasets):
    # Integration
    # Test with update = False
    # patch subfunctions
    subtask_path = 'direct_indexing.metadata.dataset.subtask_process_dataset.delay'
    mock_download = mocker.patch('direct_indexing.metadata.dataset.download_dataset')
    mock_retrieve = mocker.patch('direct_indexing.metadata.dataset.retrieve', return_value=fixture_datasets)
    mock_load_cl = mocker.patch('direct_indexing.metadata.dataset.load_codelists')
    mock_subtask = mocker.patch(subtask_path)
    mock_prep = mocker.patch('direct_indexing.metadata.dataset.prepare_update', return_value=(fixture_datasets, [True, False, True]))  # NOQA

    # run index_datasets_and_dataset_metadata
    res = index_datasets_and_dataset_metadata(False, False)
    # Assert the result is correct and all subfunctions are called except for prepare_update
    assert res == '- All Indexing substasks started'
    mock_download.assert_called_once()
    mock_retrieve.assert_called_once()
    mock_load_cl.assert_called_once()
    assert mock_subtask.call_count == len(fixture_datasets)
    mock_prep.assert_not_called()

    # Test with update = True, and only the first dataset is to be updated
    # Reset subtask mock
    mock_subtask = mocker.patch(subtask_path)
    index_datasets_and_dataset_metadata(True, False)
    mock_prep.assert_called_once()
    # Assert the subtask was triggered once with update True and once with update False
    mock_subtask.assert_any_call(dataset=fixture_datasets[0], update=True)
    mock_subtask.assert_any_call(dataset=fixture_datasets[1], update=False)

    # Test throttle dataset
    # Mock settings.THROTTLE_DATASET to True
    mocker.patch('direct_indexing.metadata.dataset.settings.THROTTLE_DATASET', True)
    # Reset subtask mock
    mock_subtask = mocker.patch(subtask_path)
    index_datasets_and_dataset_metadata(False, False)
    # Assert the subtask was called once times
    mock_subtask.assert_called_once()


def test_load_codelists(mocker):
    # Integration
    cl_path = 'direct_indexing.metadata.dataset.codelists.Codelists'
    mock_cl = mocker.patch(cl_path)
    load_codelists()
    mock_cl.assert_called_once()

    # Test exception being raised
    mocker.patch(cl_path, side_effect=requests.exceptions.RequestException)
    with pytest.raises(requests.exceptions.RequestException):
        load_codelists()


def test__get_existing_datasets(mocker, requests_mock, fixture_solr_dataset, fixture_existing_datasets):
    mocker.patch('direct_indexing.metadata.dataset.settings.SOLR_DATASET', "https://test.com")
    requests_mock.get("https://test.com" + (
        '/select?q=*:*'
        ' AND id:*&rows=100000&wt=json&fl=resources.hash,id,extras.filetype'
    ), json=fixture_solr_dataset)
    res = _get_existing_datasets()
    # Expected res is a dict with the id as key and a dict with hash and filetype as value
    assert res == fixture_existing_datasets


def test_prepare_update(mocker, fixture_existing_datasets, fixture_datasets):
    # add a changed dataset to fixture_existing_datasets
    fixture_existing_datasets["id_test_2"] = {
        "hash": "changed",
        "filetype": "activity"
    }
    mocker.patch('direct_indexing.metadata.dataset._get_existing_datasets', return_value=fixture_existing_datasets)
    # run prepare_update
    ds, bools = prepare_update(fixture_datasets)

    # we provide 3 datasets, one new, one existing with a matching hash, and one existing with a changed hash
    # therefore, we expect 2 datasets to be returned, one with update=False and a second with update=True
    assert len(ds) == 2
    assert bools == [False, True]
    # We expect id id_test_1 and id_test_2 to be in the returned datasets, in order as found in fixture_datasets
    assert ds[0]["id"] == "id_test_1"
    assert ds[1]["id"] == "id_test_2"


@pytest.fixture
def fixture_dataset():
    return {
        "id": "id_test",
    }


@pytest.fixture
def fixture_datasets():
    return [
        {
            "id": "id_test_1",
            "resources": [
                {"hash": "cc612755d0b822bb9af82f43e121428634be255a"},
            ]
        },
        {
            "id": "f783cb92-7039-44a8-b0ad-f6438566a6fa",
            "resources": [
                {"hash": "cc612755d0b822bb9af82f43e121428634be255a"},
            ]
        },
        {
            "id": "id_test_2",
            "resources": [
                {"hash": "cc612755d0b822bb9af82f43e121428634be255q"},
            ]
        },
    ]


@pytest.fixture
def fixture_solr_dataset():
    return {
        "responseHeader": {
            "status": 0,
            "QTime": 1,
            "params": {
                "q": "*:*",
                "rows": "1"
            }
        },
        "response": {
            "numFound": 10740,
            "start": 0,
            "numFoundExact": True,
            "docs": [
                {
                    "id": "f783cb92-7039-44a8-b0ad-f6438566a6fa",
                    "resources.hash": [
                        "cc612755d0b822bb9af82f43e121428634be255a"
                    ],
                    "extras.filetype": "activity",
                }
            ]
        }
    }


@pytest.fixture
def fixture_existing_datasets():
    return {
        "f783cb92-7039-44a8-b0ad-f6438566a6fa": {
            "hash": "cc612755d0b822bb9af82f43e121428634be255a",
            "filetype": "activity"
        },
    }
